"""Two-pass loudness mastering with measurement.

``audio_mixer`` builds the mix and can apply a single-pass ``loudnorm``.
Single-pass loudnorm works in dynamic mode, so it rides the gain through the
programme and never reports what it actually delivered. This tool is the last
audio step before delivery:

1. **measure** — ``loudnorm`` analysis pass (``print_format=json``).
2. **master** — second pass with the measured values and ``linear=true``, so
   the whole programme gets one gain change (dynamics preserved) and a
   true-peak ceiling. Optional de-esser for TTS sibilance.
3. **verify** — measures the output again and reports pass/fail against the
   target, so the number in the report is the delivered number.

Works on audio files and on videos (video stream is copied untouched).
Policy and targets: ``skills/core/loudness-mastering.md``.
"""

from __future__ import annotations

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

# Integrated LUFS, true-peak ceiling (dBTP), loudness range cap (LU).
PRESETS: dict[str, dict[str, float]] = {
    "youtube": {"I": -14.0, "TP": -1.0, "LRA": 11.0},
    "social": {"I": -14.0, "TP": -1.0, "LRA": 9.0},
    "podcast": {"I": -16.0, "TP": -1.0, "LRA": 11.0},
    "broadcast_ebu": {"I": -23.0, "TP": -1.0, "LRA": 15.0},
    "broadcast_atsc": {"I": -24.0, "TP": -2.0, "LRA": 15.0},
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


class AudioMaster(BaseTool):
    name = "audio_master"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "audio_processing"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]

    capabilities = ["measure_loudness", "two_pass_loudnorm", "deess"]

    input_schema = {
        "type": "object",
        "required": ["operation", "input_path"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["measure", "master"],
                "description": "measure: report loudness only. master: two-pass normalize + verify.",
            },
            "input_path": {"type": "string"},
            "output_path": {
                "type": "string",
                "description": "master only. Defaults to <input>_master.<ext>.",
            },
            "preset": {"type": "string", "enum": list(PRESETS.keys()), "default": "youtube"},
            "target_lufs": {"type": "number", "description": "Overrides the preset integrated target."},
            "true_peak": {"type": "number", "description": "Overrides the preset true-peak ceiling (dBTP)."},
            "deess": {
                "type": "boolean", "default": False,
                "description": "Tame 5-9 kHz sibilance before normalizing (useful on TTS).",
            },
            "tolerance_lu": {
                "type": "number", "default": 1.0,
                "description": "Allowed distance from the target in the verify step.",
            },
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500)
    idempotency_key_fields = ["operation", "input_path", "preset", "target_lufs", "true_peak", "deess"]
    side_effects = ["writes mastered file to output_path"]
    user_visible_verification = ["Listen to the start, a loud passage and the end of the master"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        src = Path(inputs["input_path"])
        if not src.exists():
            return ToolResult(success=False, error=f"Input not found: {src}")
        start = time.time()
        target = resolve_target(inputs)
        try:
            if inputs["operation"] == "measure":
                measured = self.measure(src, target)
                data = {"operation": "measure", "input": str(src), "target": target, "measured": measured}
                artifacts: list[str] = []
            else:
                data = self._master(src, inputs, target)
                artifacts = [data["output"]]
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(
            success=True, data=data, artifacts=artifacts,
            duration_seconds=round(time.time() - start, 2),
        )

    def measure(self, path: Path, target: dict[str, float], pre_filter: str = "") -> dict[str, Any]:
        chain = f"{pre_filter + ',' if pre_filter else ''}loudnorm=I={target['I']}:TP={target['TP']}:LRA={target['LRA']}:print_format=json"
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", chain, "-f", "null", "-"]
        return parse_loudnorm_json(self.run_command(cmd, timeout=3600).stderr)

    def _master(self, src: Path, inputs: dict[str, Any], target: dict[str, float]) -> dict[str, Any]:
        is_video = src.suffix.lower() in VIDEO_EXTENSIONS
        out = Path(inputs.get("output_path") or src.with_name(f"{src.stem}_master{src.suffix}"))
        out.parent.mkdir(parents=True, exist_ok=True)

        pre = deess_filter() if inputs.get("deess") else ""
        first = self.measure(src, target, pre)
        chain = build_second_pass(first, target, pre)

        cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af", chain]
        if is_video:
            cmd += ["-map", "0:v?", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k"]
        elif out.suffix.lower() == ".wav":
            cmd += ["-c:a", "pcm_s24le"]
        cmd += ["-ar", "48000", str(out)]
        second = parse_loudnorm_json(self.run_command(cmd, timeout=3600).stderr)

        after = self.measure(out, target)
        tol = float(inputs.get("tolerance_lu", 1.0))
        delta = after["input_i"] - target["I"]
        passed = abs(delta) <= tol and after["input_tp"] <= target["TP"] + 0.1
        return {
            "operation": "master",
            "input": str(src),
            "output": str(out),
            "target": target,
            "before": first,
            "after": after,
            "delta_lu": round(delta, 2),
            "verification_passed": passed,
            # loudnorm silently falls back to dynamic mode when the linear
            # gain would push the peak over the ceiling; say so.
            "linear_mode": second.get("normalization_type") == "linear",
        }


def resolve_target(inputs: dict[str, Any]) -> dict[str, float]:
    target = dict(PRESETS.get(inputs.get("preset", "youtube"), PRESETS["youtube"]))
    if inputs.get("target_lufs") is not None:
        target["I"] = max(-40.0, min(-5.0, float(inputs["target_lufs"])))
    if inputs.get("true_peak") is not None:
        target["TP"] = max(-9.0, min(0.0, float(inputs["true_peak"])))
    return target


def deess_filter() -> str:
    # Gentle de-esser on the sibilance band; leaves the rest of the voice alone.
    return "deesser=i=0.4:m=0.5:f=0.5:s=o"


def build_second_pass(measured: dict[str, Any], target: dict[str, float], pre_filter: str = "") -> str:
    ln = (
        f"loudnorm=I={target['I']}:TP={target['TP']}:LRA={target['LRA']}"
        f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
        f":offset={measured.get('target_offset', 0.0)}:linear=true:print_format=json"
    )
    return f"{pre_filter + ',' if pre_filter else ''}{ln}"


def parse_loudnorm_json(stderr: str) -> dict[str, Any]:
    """Extract the JSON block loudnorm prints at the end of stderr."""
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, flags=re.S)
    if not blocks:
        raise RuntimeError("loudnorm did not report measurements (no audio stream?)")
    raw = json.loads(blocks[-1])
    out: dict[str, Any] = {}
    for key, value in raw.items():
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            out[key] = value
    return out
