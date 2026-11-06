"""A ramp must put every frame where the curve says.

The test clip encodes its own clock: each frame's brightness is its source time, so
decoding the output shows which source moment landed at each output second.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from lib.pipeline_loader import load_pipeline
from tools.analysis.cold_review import NARRATIVE_PIPELINES
from tools.video.speed_ramp import (
    SpeedRamp,
    build_curve,
    output_time,
    scale_to_duration,
    setpts_expression,
)

FPS = 30
SECONDS = 6
SIZE = 32
ACCURACY_SECONDS = 0.12

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@pytest.fixture
def clock(tmp_path) -> Path:
    path = tmp_path / "clock.mp4"
    frames = FPS * SECONDS
    gray = (np.linspace(16, 235, frames)[:, None, None] * np.ones((frames, SIZE, SIZE))).astype(np.uint8)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{SIZE}x{SIZE}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv444p", str(path)],
        input=gray.tobytes(),
        check=True,
    )
    return path


def source_times(path: str) -> np.ndarray:
    """Decode a clip back to the source second of each of its frames."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True,
        check=True,
    ).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, SIZE, SIZE)
    return (frames.mean(axis=(1, 2)) - 16) / 219 * (SECONDS - 1 / FPS)


def test_constant_speed_divides_time():
    curve = build_curve([{"time": 0, "speed": 2}], 6)
    assert output_time(curve, 6) == pytest.approx(3)


def test_a_linear_ramp_matches_its_integral():
    curve = build_curve([{"time": 0, "speed": 1}, {"time": 4, "speed": 2}], 4)
    assert output_time(curve, 4) == pytest.approx(4 * np.log(2))


def test_speed_holds_outside_the_keyframes():
    curve = build_curve([{"time": 1, "speed": 2}, {"time": 2, "speed": 2}], 4)
    assert curve == [(0.0, 2.0), (1.0, 2.0), (2.0, 2.0), (4.0, 2.0)]
    assert output_time(curve, 4) == pytest.approx(2)


def test_keyframes_can_arrive_in_any_order():
    assert build_curve([{"time": 3, "speed": 1}, {"time": 1, "speed": 2}], 3)[1] == (1.0, 2.0)


def test_mapping_never_runs_backward():
    curve = build_curve([{"time": 0, "speed": 3}, {"time": 2, "speed": 0.2}, {"time": 4, "speed": 3}], 6)
    times = [output_time(curve, moment) for moment in np.linspace(0, 6, 200)]
    assert all(later >= earlier for earlier, later in zip(times, times[1:]))


@pytest.mark.parametrize(
    "keyframes",
    [
        [],
        [{"time": 9, "speed": 1}],
        [{"time": -1, "speed": 1}],
        [{"time": 1, "speed": 0}],
        [{"time": 1, "speed": 100}],
        [{"time": 1, "speed": 1}, {"time": 1, "speed": 2}],
    ],
)
def test_bad_keyframes_are_refused(keyframes):
    with pytest.raises(ValueError):
        build_curve(keyframes, 6)


def test_scaling_reaches_the_target_and_keeps_the_shape():
    curve = build_curve([{"time": 0, "speed": 1}, {"time": 3, "speed": 0.5}, {"time": 6, "speed": 1}], 6)
    scaled = scale_to_duration(curve, 4)
    assert output_time(scaled, 6) == pytest.approx(4)
    assert scaled[1][1] / scaled[0][1] == pytest.approx(0.5)


def test_an_impossible_target_is_refused():
    with pytest.raises(ValueError, match="outside"):
        scale_to_duration(build_curve([{"time": 0, "speed": 1}], 6), 0.01)


def test_the_expression_covers_every_piece():
    curve = build_curve([{"time": 1, "speed": 1}, {"time": 3, "speed": 2}], 6)
    expression = setpts_expression(curve)
    assert expression.endswith("/TB") and expression.count("if(lt(T,") == 2 and "log(" in expression


@needs_ffmpeg
def test_frames_land_where_the_curve_says(clock, tmp_path):
    keyframes = [{"time": 0, "speed": 2}, {"time": 2, "speed": 0.5}, {"time": 4, "speed": 2}]
    result = SpeedRamp().execute(
        {"input_path": str(clock), "keyframes": keyframes, "smoothing": "none", "output_path": str(tmp_path / "out.mp4")}
    )
    assert result.success, result.error
    curve = build_curve(keyframes, SECONDS)
    decoded = source_times(result.data["output"])
    expected_end = output_time(curve, SECONDS)
    assert len(decoded) / FPS == pytest.approx(expected_end, abs=0.1)

    moments = np.linspace(0.2, SECONDS - 0.2, 40)
    outputs = [output_time(curve, moment) for moment in moments]
    measured = np.interp(outputs, np.arange(len(decoded)) / FPS, decoded)
    assert np.abs(measured - moments).max() < ACCURACY_SECONDS


@needs_ffmpeg
def test_target_duration_sets_the_real_length(clock, tmp_path):
    result = SpeedRamp().execute(
        {
            "input_path": str(clock),
            "keyframes": [{"time": 0, "speed": 1}, {"time": 3, "speed": 0.4}],
            "target_duration": 4.0,
            "smoothing": "none",
            "output_path": str(tmp_path / "out.mp4"),
        }
    )
    assert result.data["output_duration"] == pytest.approx(4.0)
    assert len(source_times(result.data["output"])) / FPS == pytest.approx(4.0, abs=0.1)


@needs_ffmpeg
def test_blend_keeps_the_timing(clock, tmp_path):
    keyframes = [{"time": 0, "speed": 1}, {"time": 3, "speed": 0.3}]
    result = SpeedRamp().execute({"input_path": str(clock), "keyframes": keyframes, "output_path": str(tmp_path / "o.mp4")})
    assert result.success, result.error
    assert result.data["smoothing"] == "blend"
    assert len(source_times(result.data["output"])) / FPS == pytest.approx(result.data["output_duration"], abs=0.15)


@needs_ffmpeg
def test_the_report_warns_about_invented_frames(clock, tmp_path):
    result = SpeedRamp().execute(
        {"input_path": str(clock), "keyframes": [{"time": 0, "speed": 0.25}], "smoothing": "none", "output_path": str(tmp_path / "o.mp4")}
    )
    assert result.data["real_frames_ratio"] == pytest.approx(0.25)
    report = json.loads((tmp_path / "o.ramp.json").read_text(encoding="utf-8"))
    assert report["output_duration"] == pytest.approx(SECONDS * 4, abs=0.1)


@needs_ffmpeg
def test_the_clip_has_no_audio(clock, tmp_path):
    result = SpeedRamp().execute(
        {"input_path": str(clock), "keyframes": [{"time": 0, "speed": 1}], "smoothing": "none", "output_path": str(tmp_path / "o.mp4")}
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", result.data["output"]],
        capture_output=True,
        text=True,
    )
    assert probe.stdout.strip() == ""


@pytest.mark.parametrize("pipeline", sorted(NARRATIVE_PIPELINES))
def test_narrative_edit_stages_can_use_it(pipeline):
    edit = next(stage for stage in load_pipeline(pipeline)["stages"] if stage["name"] == "edit")
    assert "speed_ramp" in edit["tools_available"]


def test_the_catalog_routes_ramps_to_the_tool():
    catalog = Path("skills/creative/technique-catalog.md").read_text(encoding="utf-8")
    row = next(line for line in catalog.splitlines() if line.startswith("| `fin_speed_ramp`"))
    assert "`tool:speed_ramp`" in row and "Fase 5" not in row


def test_missing_input_fails(tmp_path):
    assert not SpeedRamp().execute({"input_path": str(tmp_path / "no.mp4"), "keyframes": [{"time": 0, "speed": 1}]}).success


@needs_ffmpeg
def test_bad_keyframes_fail_as_a_result(clock):
    result = SpeedRamp().execute({"input_path": str(clock), "keyframes": [{"time": 99, "speed": 1}]})
    assert not result.success and "outside" in result.error


def test_unknown_smoothing_fails(clock):
    result = SpeedRamp().execute({"input_path": str(clock), "keyframes": [{"time": 0, "speed": 1}], "smoothing": "magic"})
    assert not result.success
