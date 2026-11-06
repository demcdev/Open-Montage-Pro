"""Cold review of a finished master, by a reviewer who did not make it.

``skills/meta/reviewer.md`` is self-review: the agent that made the video judges it.
This tool keeps the second opinion honest. ``prepare`` builds the only material the
``cold-viewer`` agent receives: the brief, frames, the transcript and the measured
reports, never the conversation. ``record`` turns its scores into a verdict tied to
the exact bytes reviewed, which ``export_bundle`` checks in narrative pipelines.

The reviewer cannot hear audio or see motion between frames, so voice and layout
scores are capped by what was measured: a missing or failing report wins over any
score. The policy lives in ``skills/meta/cold-review.md``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tools.analysis.technical_qc import file_sha256
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

NARRATIVE_PIPELINES = {
    "animated-explainer",
    "animation",
    "avatar-spokesperson",
    "character-animation",
    "cinematic",
    "documentary-montage",
    "hybrid",
}
CRITERIA = ("hook", "pacing", "legibility", "continuity", "audio", "promise", "voice", "layout")
MIN_SCORE = 3
MAX_ROUNDS = 3
MAX_FRAMES = 40
FRAME_WIDTH = 960
SCENE_MOMENTS = (0.35, 0.75)
HOOK_SECONDS = 1.0


def cold_path(video_path: str | Path) -> Path:
    return Path(video_path).with_suffix(".cold.json")


def packet_dir(video_path: str | Path) -> Path:
    return Path(video_path).with_suffix(".cold")


def read_report(path: Path) -> dict[str, Any] | None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def frame_times(duration: float, scenes: list[dict[str, Any]], layout: dict[str, Any] | None) -> list[float]:
    """Pick frames: the hook, two per scene, and every moment the audit flagged."""
    times = [min(HOOK_SECONDS, duration / 2)]
    for scene in scenes:
        start, end = float(scene["start"]), float(scene["end"])
        times += [start + (end - start) * moment for moment in SCENE_MOMENTS]
    if not scenes:
        step = max(duration / (MAX_FRAMES - 1), 2.0)
        times += [step * index for index in range(1, int(duration / step) + 1)]
    flagged = [finding["start"] for finding in (layout or {}).get("findings", [])]
    if len(times) + len(flagged) > MAX_FRAMES:
        stride = (len(times) + len(flagged)) / MAX_FRAMES
        times = [times[int(index * stride)] for index in range(int(len(times) / stride))]
    moments = {round(min(moment, max(duration - 0.1, 0)), 2) for moment in times + flagged}
    return sorted(moments)


def measured_caps(packet: dict[str, Any]) -> dict[str, tuple[int, str]]:
    """Return the highest score each measured criterion may keep, and why."""
    caps: dict[str, tuple[int, str]] = {}
    layout = packet.get("layout")
    if layout is None:
        caps["layout"] = (1, "No layout audit for this render.")
    elif layout.get("verdict") == "block":
        caps["layout"] = (1, "The layout audit blocked this composition.")
    if packet.get("has_narration"):
        narration = packet.get("narration")
        if narration is None:
            caps["voice"] = (1, "No narration_qc report for this narration.")
        elif narration.get("verdict") != "pass":
            caps["voice"] = (1, "narration_qc has flagged sentences nobody resolved.")
    return caps


def evaluate(
    scores: dict[str, Any],
    packet: dict[str, Any],
    round_number: int,
) -> tuple[str, dict[str, Any], list[str]]:
    """Return (verdict, final scores, failed criteria)."""
    caps = measured_caps(packet)
    final: dict[str, Any] = {}
    for criterion in CRITERIA:
        entry = dict(scores.get(criterion) or {})
        if criterion == "voice" and not packet.get("has_narration"):
            final[criterion] = {"score": None, "evidence": "No narration in this video."}
            continue
        if not isinstance(entry.get("score"), int) or not 1 <= entry["score"] <= 5:
            raise ValueError(f"{criterion} needs a score from 1 to 5.")
        if not str(entry.get("evidence") or "").strip():
            raise ValueError(f"{criterion} needs evidence: a timestamp or a frame.")
        if criterion in caps and entry["score"] > caps[criterion][0]:
            entry["score"], entry["capped_by"] = caps[criterion]
        final[criterion] = entry

    failed = [name for name, entry in final.items() if entry["score"] is not None and entry["score"] < MIN_SCORE]
    if not failed:
        return "pass", final, failed
    return ("escalate" if round_number >= MAX_ROUNDS else "revise"), final, failed


class ColdReview(BaseTool):
    name = "cold_review"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]
    usage_skills = ["meta/cold-review"]

    capabilities = ["build_cold_review_packet", "record_cold_review"]

    input_schema = {
        "type": "object",
        "required": ["operation", "video_path"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["prepare", "record"],
                "description": "prepare: build the packet for cold-viewer. record: score it and write <video>.cold.json.",
            },
            "video_path": {"type": "string", "description": "Final master, after audio_master."},
            "brief": {"type": "object", "description": "prepare: the brief or delivery promise."},
            "scenes": {
                "type": "array",
                "description": "prepare: scene windows in seconds, from edit_decisions or scene_plan.",
                "items": {
                    "type": "object",
                    "required": ["start", "end"],
                    "properties": {
                        "id": {"type": "string"},
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                    },
                },
            },
            "has_narration": {"type": "boolean", "default": True, "description": "prepare: the video has a voice."},
            "narration_report_path": {"type": "string", "description": "prepare: narration_qc report."},
            "layout_report_path": {
                "type": "string",
                "description": "prepare: layout report. Defaults to <video>.layout.json.",
            },
            "qc_report_path": {
                "type": "string",
                "description": "prepare: technical_qc report. Defaults to <video>.qc.json.",
            },
            "scores": {
                "type": "object",
                "description": "record: {criterion: {score: 1-5, evidence: text}} from cold-viewer.",
            },
            "findings": {
                "type": "array",
                "items": {"type": "object"},
                "description": "record: cold-viewer's findings, each with a timestamp and a proposed fix.",
            },
            "round": {"type": "integer", "minimum": 1, "maximum": MAX_ROUNDS, "default": 1},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=50)
    idempotency_key_fields = ["operation", "video_path", "round"]
    side_effects = ["writes a review packet next to the video and <video>.cold.json"]
    user_visible_verification = ["Read the failed criteria and their evidence before shipping"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        video_path = Path(inputs["video_path"])
        if not video_path.is_file():
            return ToolResult(success=False, error=f"Video not found: {video_path}")
        start = time.time()
        try:
            data = self._prepare(video_path, inputs) if inputs["operation"] == "prepare" else self._record(video_path, inputs)
        except Exception as exc:  # noqa: BLE001 - surface ffmpeg and scoring failures
            return ToolResult(success=False, error=f"Cold review failed: {exc}")
        return ToolResult(success=True, data=data, duration_seconds=round(time.time() - start, 2))

    def _duration(self, video_path: Path) -> float:
        probe = self.run_command(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
            timeout=60,
        )
        return float(probe.stdout.strip())

    def _prepare(self, video_path: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        duration = self._duration(video_path)
        layout = read_report(Path(inputs.get("layout_report_path") or video_path.with_suffix(".layout.json")))
        qc = read_report(Path(inputs.get("qc_report_path") or video_path.with_suffix(".qc.json")))
        narration_path = inputs.get("narration_report_path")
        narration = read_report(Path(narration_path)) if narration_path else None

        out_dir = packet_dir(video_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("frame_*.jpg"):
            old.unlink()
        frames = []
        for moment in frame_times(duration, inputs.get("scenes") or [], layout):
            frame = out_dir / f"frame_{moment:08.2f}.jpg"
            self.run_command(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(moment), "-i", str(video_path),
                 "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2", "-q:v", "3", str(frame)],
                timeout=120,
            )
            frames.append({"time": moment, "file": frame.name})

        packet = {
            "input_sha256": file_sha256(video_path),
            "duration_seconds": round(duration, 2),
            "brief": inputs.get("brief") or {},
            "scenes": inputs.get("scenes") or [],
            "has_narration": inputs.get("has_narration", True),
            "transcript": (narration or {}).get("transcript", ""),
            "narration": None if narration is None else {k: narration.get(k) for k in ("verdict", "flagged")},
            "layout": None if layout is None else {k: layout.get(k) for k in ("verdict", "findings", "samples_checked")},
            "technical_qc": None if qc is None else {k: qc.get(k) for k in ("verdict", "loudness", "findings")},
            "frames": frames,
        }
        packet_path = out_dir / "packet.json"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"packet_path": str(packet_path), "frames": len(frames), "caps": list(measured_caps(packet))}

    def _record(self, video_path: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        packet = read_report(packet_dir(video_path) / "packet.json")
        if packet is None:
            raise ValueError("No packet for this video. Run operation prepare first.")
        sha = file_sha256(video_path)
        if packet.get("input_sha256") != sha:
            raise ValueError("The video changed after prepare. Run operation prepare again.")

        round_number = int(inputs.get("round", 1))
        if not 1 <= round_number <= MAX_ROUNDS:
            raise ValueError(f"round must be 1 to {MAX_ROUNDS}.")
        verdict, scores, failed = evaluate(inputs.get("scores") or {}, packet, round_number)
        report = {
            "input": str(video_path),
            "input_sha256": sha,
            "verdict": verdict,
            "round": round_number,
            "scores": scores,
            "failed_criteria": failed,
            "findings": inputs.get("findings") or [],
        }
        report_path = cold_path(video_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**report, "report_path": str(report_path)}
