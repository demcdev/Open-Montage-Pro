"""Speed ramps: change a clip's speed gradually inside one shot.

``cut.speed`` and ``video_trimmer`` keep one speed for a whole clip. Here speed moves
in straight lines between keyframes on the source timeline, which gives each frame
an exact output time: with speed ``s(t)``, a frame lands at the integral of ``1/s``.
That integral has a closed form on each straight piece, so the same mapping feeds
FFmpeg's ``setpts`` and the numbers this tool reports.

The result is a new clip with no audio, since sound cannot follow a ramp, and it
replaces the source in the cut. Slowing a clip below its frame rate has to invent
frames, which is what ``smoothing`` decides.
"""

from __future__ import annotations

import json
import math
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

MIN_SPEED = 0.05
MAX_SPEED = 20.0
FLAT_SLOPE = 1e-9
END_HOLD_SECONDS = 1
SMOOTHING = {
    "none": None,
    "blend": "minterpolate=fps={fps}:mi_mode=blend",
    "motion": "minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1",
}


def build_curve(keyframes: list[dict[str, float]], duration: float) -> list[tuple[float, float]]:
    """Return sorted (source time, speed) points covering the whole clip.

    Speed holds before the first keyframe and after the last one.
    """
    if not keyframes:
        raise ValueError("keyframes needs at least one entry.")
    points = sorted((float(k["time"]), float(k["speed"])) for k in keyframes)
    for moment, speed in points:
        if not 0 <= moment <= duration:
            raise ValueError(f"Keyframe at {moment}s is outside the clip ({duration}s).")
        if not MIN_SPEED <= speed <= MAX_SPEED:
            raise ValueError(f"Speed {speed} is outside {MIN_SPEED} to {MAX_SPEED}.")
    if len({moment for moment, _ in points}) != len(points):
        raise ValueError("Two keyframes share the same time.")
    if points[0][0] > 0:
        points.insert(0, (0.0, points[0][1]))
    if points[-1][0] < duration:
        points.append((duration, points[-1][1]))
    return points


def piece_length(t0: float, s0: float, t1: float, s1: float, moment: float) -> float:
    """Output seconds from t0 to ``moment`` on one straight piece of the curve."""
    slope = (s1 - s0) / (t1 - t0)
    if abs(slope) < FLAT_SLOPE:
        return (moment - t0) / s0
    return math.log((s0 + slope * (moment - t0)) / s0) / slope


def output_time(curve: list[tuple[float, float]], moment: float) -> float:
    """Output second where a source second lands."""
    total = 0.0
    for (t0, s0), (t1, s1) in zip(curve, curve[1:]):
        if moment <= t1:
            return total + piece_length(t0, s0, t1, s1, moment)
        total += piece_length(t0, s0, t1, s1, t1)
    return total


def scale_to_duration(curve: list[tuple[float, float]], target: float) -> list[tuple[float, float]]:
    """Multiply every speed so the clip lasts ``target``, keeping the ramp's shape."""
    factor = output_time(curve, curve[-1][0]) / target
    scaled = [(moment, speed * factor) for moment, speed in curve]
    for _, speed in scaled:
        if not MIN_SPEED <= speed <= MAX_SPEED:
            raise ValueError(f"Reaching {target}s needs speed {speed:.3f}, outside {MIN_SPEED} to {MAX_SPEED}.")
    return scaled


def setpts_expression(curve: list[tuple[float, float]]) -> str:
    """Write the same mapping as ``output_time`` as an FFmpeg expression of T."""
    pieces = []
    total = 0.0
    for (t0, s0), (t1, s1) in zip(curve, curve[1:]):
        slope = (s1 - s0) / (t1 - t0)
        if abs(slope) < FLAT_SLOPE:
            piece = f"(T-{t0})/{s0}"
        else:
            piece = f"log(({s0}+{slope}*(T-{t0}))/{s0})/{slope}"
        pieces.append((t1, f"{total}+{piece}"))
        total += piece_length(t0, s0, t1, s1, t1)
    expression = pieces[-1][1]
    for limit, piece in reversed(pieces[:-1]):
        expression = f"if(lt(T,{limit}),{piece},{expression})"
    return f"({expression})/TB"


class SpeedRamp(BaseTool):
    name = "speed_ramp"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "video_post"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]
    usage_skills = ["core/speed-ramp"]

    capabilities = ["speed_ramp", "time_remap"]

    input_schema = {
        "type": "object",
        "required": ["input_path", "keyframes"],
        "properties": {
            "input_path": {"type": "string", "description": "Clip to ramp."},
            "keyframes": {
                "type": "array",
                "minItems": 1,
                "description": "Speed at moments of the source clip. Speed moves in a straight line between them.",
                "items": {
                    "type": "object",
                    "required": ["time", "speed"],
                    "properties": {
                        "time": {"type": "number", "minimum": 0, "description": "Source second."},
                        "speed": {"type": "number", "minimum": MIN_SPEED, "maximum": MAX_SPEED},
                    },
                },
            },
            "target_duration": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Output length. Scales all speeds, keeping the ramp's shape.",
            },
            "smoothing": {
                "type": "string",
                "enum": list(SMOOTHING),
                "default": "blend",
                "description": (
                    "How to fill slowed frames. none repeats frames, blend crossfades them, "
                    "motion interpolates: smoothest and slowest, with artifacts on fast action."
                ),
            },
            "fps": {"type": "number", "exclusiveMinimum": 0, "description": "Output frame rate. Defaults to the source's."},
            "crf": {"type": "integer", "default": 16},
            "output_path": {"type": "string", "description": "Defaults to <input>_ramp.mp4."},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=2048, vram_mb=0, disk_mb=500)
    idempotency_key_fields = ["input_path", "keyframes", "target_duration", "smoothing", "fps"]
    side_effects = ["writes a new video without audio to output_path", "writes <output>.ramp.json"]
    user_visible_verification = ["Watch the slow parts: too few source frames shows as stutter or smearing"]

    def _probe(self, path: Path) -> tuple[float, float]:
        probe = self.run_command(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate:format=duration",
             "-of", "json", str(path)],
            timeout=60,
        )
        info = json.loads(probe.stdout)
        numerator, denominator = info["streams"][0]["avg_frame_rate"].split("/")
        return float(info["format"]["duration"]), float(numerator) / float(denominator)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        input_path = Path(inputs["input_path"])
        if not input_path.exists():
            return ToolResult(success=False, error=f"Input not found: {input_path}")
        smoothing = inputs.get("smoothing", "blend")
        if smoothing not in SMOOTHING:
            return ToolResult(success=False, error=f"Unknown smoothing: {smoothing}")

        start = time.time()
        try:
            duration, source_fps = self._probe(input_path)
            curve = build_curve(inputs["keyframes"], duration)
            if inputs.get("target_duration"):
                curve = scale_to_duration(curve, float(inputs["target_duration"]))
            fps = float(inputs.get("fps") or source_fps)
            output_path = Path(inputs.get("output_path") or input_path.with_name(f"{input_path.stem}_ramp.mp4"))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # The last frame stands for a whole frame of slowed source, so it is held
            # and cut at the planned length: the edit relies on that exact duration.
            planned = output_time(curve, duration)
            filters = [
                "setpts=PTS-STARTPTS",
                f"setpts='{setpts_expression(curve)}'",
                f"tpad=stop_mode=clone:stop_duration={END_HOLD_SECONDS}",
            ]
            template = SMOOTHING[smoothing]
            filters.append(template.format(fps=fps) if template else f"fps={fps}")
            self.run_command(
                ["ffmpeg", "-y", "-v", "error", "-i", str(input_path), "-vf", ",".join(filters), "-an",
                 "-t", str(planned), "-c:v", "libx264", "-preset", "medium", "-crf", str(inputs.get("crf", 16)),
                 "-pix_fmt", "yuv420p", str(output_path)],
                timeout=1800,
            )
        except Exception as exc:  # noqa: BLE001 - surface bad keyframes and ffmpeg failures
            return ToolResult(success=False, error=f"Speed ramp failed: {exc}")

        slowest = min(speed for _, speed in curve)
        report = {
            "input": str(input_path),
            "output": str(output_path),
            "source_duration": round(duration, 3),
            "output_duration": round(planned, 3),
            "smoothing": smoothing,
            "fps": fps,
            "curve": [{"time": round(moment, 3), "speed": round(speed, 3)} for moment, speed in curve],
            "keyframe_output_times": [round(output_time(curve, moment), 3) for moment, _ in curve],
            # Below 1, source frames fall short of the output rate and the rest are invented.
            "real_frames_ratio": round(min(slowest * source_fps / fps, 1.0), 3),
        }
        report_path = output_path.with_suffix(".ramp.json")
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return ToolResult(
            success=True,
            data={**report, "report_path": str(report_path)},
            artifacts=[str(output_path), str(report_path)],
            duration_seconds=round(time.time() - start, 2),
        )
