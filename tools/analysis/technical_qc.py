"""Technical QC gate for finished renders.

One ffmpeg decode pass runs blackdetect, freezedetect, silencedetect and
ebur128 together; ffprobe checks container conformity. Every finding gets a
severity and the run ends in a single verdict:

- ``pass``  (exit_code 0)  nothing to fix,
- ``warn``  (exit_code 10) ship only after a human looks at the flagged spots,
- ``block`` (exit_code 1)  do not publish.

This is the *technical* half of review. Creative review (does the cut work,
is the joke funny) stays with ``skills/meta/reviewer.md``. The policy that
decides when to run this and how to act on the verdict lives in
``skills/meta/technical-qc-gate.md``.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

# Thresholds per delivery profile. Loudness tolerances are in LU around the
# target; true peak is a ceiling in dBTP.
PROFILES: dict[str, dict[str, float]] = {
    "youtube": {"lufs": -14.0, "lufs_warn": 1.0, "lufs_block": 3.0, "true_peak": -1.0},
    "social": {"lufs": -14.0, "lufs_warn": 1.0, "lufs_block": 3.0, "true_peak": -1.0},
    "podcast": {"lufs": -16.0, "lufs_warn": 1.0, "lufs_block": 3.0, "true_peak": -1.0},
    "broadcast_ebu": {"lufs": -23.0, "lufs_warn": 0.5, "lufs_block": 1.0, "true_peak": -1.0},
    "broadcast_atsc": {"lufs": -24.0, "lufs_warn": 1.0, "lufs_block": 2.0, "true_peak": -2.0},
}

SEVERITY_RANK = {"info": 0, "warn": 1, "block": 2}
VERDICT_EXIT = {"pass": 0, "warn": 10, "block": 1}


def file_sha256(path: str | Path) -> str:
    """Fingerprint of a file, so a report can be tied to the exact bytes it checked."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TechnicalQC(BaseTool):
    name = "technical_qc"
    version = "0.2.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]

    capabilities = [
        "detect_black_frames",
        "detect_frozen_frames",
        "detect_silence",
        "measure_loudness",
        "check_delivery_conformity",
        "check_asset_licenses",
    ]

    input_schema = {
        "type": "object",
        "required": ["input_path"],
        "properties": {
            "input_path": {"type": "string", "description": "Finished render to check."},
            "profile": {
                "type": "string",
                "enum": list(PROFILES.keys()),
                "default": "youtube",
                "description": "Loudness and true-peak targets to check against.",
            },
            "expected": {
                "type": "object",
                "description": "Delivery spec to enforce. Any key left out is not checked.",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "fps": {"type": "number"},
                    "video_codec": {"type": "string"},
                    "pixel_format": {"type": "string"},
                    "audio_codec": {"type": "string"},
                    "sample_rate": {"type": "integer"},
                    "min_duration": {"type": "number"},
                    "max_duration": {"type": "number"},
                },
            },
            "black_min_seconds": {
                "type": "number", "default": 0.5,
                "description": "Shortest black run reported.",
            },
            "freeze_min_seconds": {
                "type": "number", "default": 2.0,
                "description": (
                    "Shortest frozen run reported. Raise it for animation with "
                    "long intentional holds."
                ),
            },
            "silence_min_seconds": {
                "type": "number", "default": 2.0,
                "description": "Shortest full-mix silence reported.",
            },
            "silence_threshold_db": {"type": "number", "default": -50},
            "edge_grace_seconds": {
                "type": "number", "default": 1.5,
                "description": (
                    "Black or silence that touches the start or end within this "
                    "window is treated as an intentional fade (info, not warn)."
                ),
            },
            "intentional_ranges": {
                "type": "array",
                "description": (
                    "Planned holds, blackouts or silences from edit_decisions. "
                    "Findings fully inside one of these ranges are downgraded to info."
                ),
                "items": {
                    "type": "object",
                    "required": ["start", "end"],
                    "properties": {
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                        "reason": {"type": "string"},
                    },
                },
            },
            "asset_manifest_path": {
                "type": "string",
                "description": (
                    "Optional asset_manifest JSON. Any asset without a license "
                    "blocks publishing (youtube-policy-gate)."
                ),
            },
            "report_path": {
                "type": "string",
                "description": "Where to write the JSON report. Defaults next to the input.",
            },
        },
    }

    resource_profile = ResourceProfile(cpu_cores=2, ram_mb=512, vram_mb=0, disk_mb=10)
    idempotency_key_fields = ["input_path", "profile", "expected"]
    side_effects = ["writes a JSON QC report next to the input (or report_path)"]
    user_visible_verification = [
        "Open the flagged timestamps and confirm each warning is real or intentional",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        input_path = inputs["input_path"]
        if not Path(input_path).exists():
            return ToolResult(success=False, error=f"Input not found: {input_path}")

        start = time.time()
        try:
            probe = self._probe(input_path)
            stderr = self._analyze(input_path, probe, inputs)
            findings = self.evaluate(probe, parse_analysis(stderr), inputs)
            findings.extend(self._license_findings(inputs.get("asset_manifest_path")))
        except Exception as exc:  # noqa: BLE001 - surface any ffmpeg/parse failure
            return ToolResult(success=False, error=str(exc))

        verdict = verdict_for(findings)
        report = {
            "input": input_path,
            "input_sha256": file_sha256(input_path),
            "profile": inputs.get("profile", "youtube"),
            "verdict": verdict,
            "exit_code": VERDICT_EXIT[verdict],
            "probe": probe,
            "loudness": parse_analysis(stderr)["loudness"],
            "findings": findings,
            "counts": {
                sev: sum(1 for f in findings if f["severity"] == sev)
                for sev in ("block", "warn", "info")
            },
        }
        report_path = Path(
            inputs.get("report_path") or Path(input_path).with_suffix(".qc.json")
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        return ToolResult(
            success=True,
            data={**report, "report_path": str(report_path)},
            artifacts=[str(report_path)],
            duration_seconds=round(time.time() - start, 2),
        )

    # ------------------------------------------------------------------ ffmpeg

    def _probe(self, path: str) -> dict[str, Any]:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,"
            "pix_fmt,r_frame_rate,sample_rate,channels",
            "-of", "json", path,
        ]
        raw = json.loads(self.run_command(cmd).stdout or "{}")
        info: dict[str, Any] = {
            "duration": float(raw.get("format", {}).get("duration", 0) or 0),
            "has_video": False,
            "has_audio": False,
        }
        for s in raw.get("streams", []):
            if s.get("codec_type") == "video" and not info["has_video"]:
                info.update({
                    "has_video": True,
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "video_codec": s.get("codec_name"),
                    "pixel_format": s.get("pix_fmt"),
                    "fps": _fps(s.get("r_frame_rate")),
                })
            elif s.get("codec_type") == "audio" and not info["has_audio"]:
                info.update({
                    "has_audio": True,
                    "audio_codec": s.get("codec_name"),
                    "sample_rate": int(s.get("sample_rate") or 0),
                    "channels": s.get("channels"),
                })
        return info

    def _analyze(self, path: str, probe: dict[str, Any], inputs: dict[str, Any]) -> str:
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path]
        if probe["has_video"]:
            black = float(inputs.get("black_min_seconds", 0.5))
            freeze = float(inputs.get("freeze_min_seconds", 2.0))
            cmd += ["-vf", f"blackdetect=d={black}:pix_th=0.10,freezedetect=n=-60dB:d={freeze}"]
        if probe["has_audio"]:
            sil = float(inputs.get("silence_min_seconds", 2.0))
            thr = float(inputs.get("silence_threshold_db", -50))
            cmd += ["-af", f"silencedetect=n={thr}dB:d={sil},ebur128=peak=true"]
        cmd += ["-f", "null", "-"]
        return self.run_command(cmd, timeout=3600).stderr

    # -------------------------------------------------------------- evaluation

    @staticmethod
    def evaluate(
        probe: dict[str, Any], analysis: dict[str, Any], inputs: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Turn probe + parsed detector output into graded findings."""
        findings: list[dict[str, Any]] = []
        duration = probe.get("duration", 0.0)
        grace = float(inputs.get("edge_grace_seconds", 1.5))
        ranges = inputs.get("intentional_ranges") or []
        profile = PROFILES.get(inputs.get("profile", "youtube"), PROFILES["youtube"])

        def add(check, severity, message, start=None, end=None):
            findings.append({
                "check": check, "severity": severity, "message": message,
                "start": start, "end": end,
            })

        def graded(check, start, end, label):
            at_edge = start <= grace or (duration and end >= duration - grace)
            planned = next(
                (r for r in ranges if r["start"] - 0.05 <= start and end <= r["end"] + 0.05),
                None,
            )
            if planned:
                add(check, "info", f"{label} (planned: {planned.get('reason', 'intentional')})", start, end)
            elif at_edge:
                add(check, "info", f"{label} at the edge (fade?)", start, end)
            else:
                add(check, "warn", label, start, end)

        if not probe.get("has_video"):
            add("streams", "block", "No video stream")
        if not probe.get("has_audio"):
            add("streams", "warn", "No audio stream")

        for b in analysis["black"]:
            covers_all = duration and b["duration"] >= duration * 0.9
            if covers_all:
                add("black", "block", f"Video is black for {b['duration']:.1f}s", b["start"], b["end"])
            else:
                graded("black", b["start"], b["end"], f"Black run {b['duration']:.2f}s")
        for f in analysis["freeze"]:
            # A black run is also a static picture; report it once, as black.
            if any(b["start"] - 0.1 <= f["start"] and f["end"] <= b["end"] + 0.1 for b in analysis["black"]):
                continue
            graded("freeze", f["start"], f["end"], f"Frozen picture {f['duration']:.2f}s")
        for s in analysis["silence"]:
            end = s["end"] if s["end"] is not None else duration
            graded("silence", s["start"], end, f"Silence {end - s['start']:.2f}s")

        loud = analysis["loudness"]
        if probe.get("has_audio") and loud.get("integrated") is not None:
            delta = loud["integrated"] - profile["lufs"]
            msg = f"Integrated {loud['integrated']:.1f} LUFS vs target {profile['lufs']:.0f} ({delta:+.1f} LU)"
            if abs(delta) > profile["lufs_block"]:
                add("loudness", "block", msg)
            elif abs(delta) > profile["lufs_warn"]:
                add("loudness", "warn", msg)
            else:
                add("loudness", "info", msg)
            tp = loud.get("true_peak")
            if tp is not None:
                tp_msg = f"True peak {tp:.1f} dBTP vs ceiling {profile['true_peak']:.1f}"
                if tp > -0.1:
                    add("true_peak", "block", tp_msg + " (clipping)")
                elif tp > profile["true_peak"]:
                    add("true_peak", "warn", tp_msg)

        expected = inputs.get("expected") or {}
        for key in ("width", "height", "video_codec", "pixel_format", "audio_codec", "sample_rate"):
            if key in expected and probe.get(key) != expected[key]:
                add("conformity", "block", f"{key}: expected {expected[key]}, got {probe.get(key)}")
        if "fps" in expected and probe.get("fps") is not None:
            if abs(probe["fps"] - float(expected["fps"])) > 0.01:
                add("conformity", "block", f"fps: expected {expected['fps']}, got {probe['fps']:.3f}")
        if "min_duration" in expected and duration < expected["min_duration"]:
            add("conformity", "block", f"Too short: {duration:.1f}s < {expected['min_duration']}s")
        if "max_duration" in expected and duration > expected["max_duration"]:
            add("conformity", "block", f"Too long: {duration:.1f}s > {expected['max_duration']}s")
        return findings

    @staticmethod
    def _license_findings(manifest_path: str | None) -> list[dict[str, Any]]:
        if not manifest_path:
            return []
        path = Path(manifest_path)
        if not path.exists():
            return [{"check": "licenses", "severity": "block",
                     "message": f"asset_manifest not found: {manifest_path}",
                     "start": None, "end": None}]
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [
            a.get("id") or a.get("path")
            for a in data.get("assets", [])
            if not str(a.get("license") or "").strip()
        ]
        if not missing:
            return [{"check": "licenses", "severity": "info",
                     "message": "Every asset has a license", "start": None, "end": None}]
        return [{"check": "licenses", "severity": "block",
                 "message": f"{len(missing)} asset(s) without license: {', '.join(map(str, missing[:10]))}",
                 "start": None, "end": None}]


# ---------------------------------------------------------------- parsing

_BLACK = re.compile(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)\s+black_duration:\s*([\d.]+)")
_FREEZE_START = re.compile(r"freeze_start:\s*([\d.]+)")
_FREEZE_END = re.compile(r"freeze_end:\s*([\d.]+)")
_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*([\d.]+)")


def parse_analysis(stderr: str) -> dict[str, Any]:
    """Parse blackdetect / freezedetect / silencedetect / ebur128 stderr."""
    black = [
        {"start": float(a), "end": float(b), "duration": float(c)}
        for a, b, c in _BLACK.findall(stderr)
    ]

    freeze: list[dict[str, Any]] = []
    pending: float | None = None
    for line in stderr.splitlines():
        m = _FREEZE_START.search(line)
        if m:
            pending = float(m.group(1))
            continue
        m = _FREEZE_END.search(line)
        if m and pending is not None:
            end = float(m.group(1))
            freeze.append({"start": pending, "end": end, "duration": end - pending})
            pending = None

    silence: list[dict[str, Any]] = []
    for line in stderr.splitlines():
        m = _SIL_START.search(line)
        if m:
            silence.append({"start": max(0.0, float(m.group(1))), "end": None})
            continue
        m = _SIL_END.search(line)
        if m and silence and silence[-1]["end"] is None:
            silence[-1]["end"] = float(m.group(1))

    loudness: dict[str, Any] = {}
    summary = stderr.rsplit("Summary:", 1)[-1] if "Summary:" in stderr else ""
    for key, pattern in (
        ("integrated", r"I:\s*(-?[\d.]+)\s*LUFS"),
        ("lra", r"LRA:\s*(-?[\d.]+)\s*LU"),
        ("true_peak", r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS"),
    ):
        m = re.search(pattern, summary)
        if m and m.group(1) != "-inf":
            loudness[key] = float(m.group(1))

    return {"black": black, "freeze": freeze, "silence": silence, "loudness": loudness}


def verdict_for(findings: list[dict[str, Any]]) -> str:
    worst = max((SEVERITY_RANK[f["severity"]] for f in findings), default=0)
    return {0: "pass", 1: "warn", 2: "block"}[worst]


def _fps(rate: str | None) -> float | None:
    if not rate or rate in ("0/0",):
        return None
    if "/" in rate:
        num, den = rate.split("/", 1)
        return float(num) / float(den) if float(den) else None
    return float(rate)
