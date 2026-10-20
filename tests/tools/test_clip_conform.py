"""clip_conform picks the right fps method and conforms clips in one pass.

Method choice, probe parsing, flicker math and filter building run without
ffmpeg. The end-to-end tests conform a 16 fps clip to 24, retime 25 to 24,
keep animation on twos un-interpolated, stabilize, and build a slow-mo.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.video.clip_conform import (  # noqa: E402
    ClipConform,
    choose_fps_method,
    compute_flicker_index,
    fps_arg,
    fps_filters,
    parse_rate,
    recommend,
    resize_filters,
    summarize_probe,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.parametrize("src,target,content,expected", [
    (24, 24, "generated", "none"),
    (16, 24, "generated", "interpolate"),   # fill frames for a slow model
    (12, 24, "animation", "drop"),          # animation on twos: duplicate, never interpolate
    (25, 24, "generated", "retime"),        # small gap: retime instead of a stutter per second
    (25, 24, "animation", "drop"),
    (30, 24, "generated", "drop"),
    (60, 30, "live_action", "drop"),
    (29.97, 30, "generated", "none"),       # 0.1% gap: the fps filter only normalizes
])
def test_choose_fps_method(src, target, content, expected):
    assert choose_fps_method(src, target, "auto", content) == expected


def test_explicit_method_wins():
    assert choose_fps_method(30, 24, "blend") == "blend"


def test_rates_and_probe_summary():
    assert parse_rate("30000/1001") == pytest.approx(29.97, abs=0.01)
    assert parse_rate("0/0") == 0.0
    assert fps_arg(23.976) == "24000/1001" and fps_arg(24) == "24"
    info = summarize_probe({
        "format": {"duration": "5.0"},
        "streams": [{"codec_type": "video", "r_frame_rate": "30/1", "avg_frame_rate": "24/1",
                     "width": 1280, "height": 720, "codec_name": "h264", "pix_fmt": "yuv420p"}],
    })
    assert info["vfr"] is True and info["fps"] == 24 and info["has_audio"] is False
    assert info["color_space"] == "unknown"


def test_flicker_index_ignores_smooth_changes():
    ramp = [50 + i for i in range(40)]                 # fade or pan: linear luma change
    flicker = [100 + (6 if i % 2 else -6) for i in range(40)]
    assert compute_flicker_index(ramp) == 0.0
    assert compute_flicker_index(flicker) > 0.05


def test_filters():
    assert fps_filters("interpolate", 16, 24)[0].startswith("minterpolate=fps=24")
    assert fps_filters("retime", 25, 24)[0] == "setpts=PTS*25.000000/24.000000"
    assert resize_filters({"target_width": 1920, "target_height": 1080}, {"width": 1920, "height": 1080}) == []
    fit = resize_filters({"target_width": 1080, "target_height": 1920, "resize_mode": "fit"}, {"width": 1920, "height": 1080})
    assert any(f.startswith("pad=1080:1920") for f in fit)


def test_recommendations():
    info = {"has_video": True, "fps": 16.0, "vfr": True, "width": 640, "height": 360, "color_space": "unknown"}
    steps = [r["step"] for r in recommend(info, 0.03, {"target_fps": 24, "target_height": 1080})]
    assert "conform" in steps and "fps_method=interpolate" in steps and "deflicker" in steps
    assert "upscale_method=realesrgan" in steps and "film_look tagging" in steps


def _clip(path: Path, rate: str, seconds: int = 2, audio: bool = True) -> Path:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"testsrc2=s=320x180:r={rate}:d={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=f=440:d={seconds}:sample_rate=48000", "-c:a", "aac", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_end_to_end_conform_retime_animation_and_slowmo(tmp_path):
    tool = ClipConform()

    slow = _clip(tmp_path / "model16.mp4", "16")
    analysis = tool.execute({"operation": "analyze", "input_path": str(slow)})
    assert analysis.success, analysis.error
    assert analysis.data["probe"]["fps"] == 16

    done = tool.execute({"operation": "conform", "input_path": str(slow), "deflicker": True,
                         "target_width": 640, "target_height": 360})
    assert done.success, done.error
    assert done.data["fps_method"] == "interpolate"
    assert done.data["result"]["fps"] == 24 and done.data["result"]["height"] == 360
    assert done.data["result"]["duration"] == pytest.approx(2.0, abs=0.1)

    pal = _clip(tmp_path / "pal.mp4", "25", seconds=4)
    retimed = tool.execute({"operation": "conform", "input_path": str(pal)})
    assert retimed.success, retimed.error
    assert retimed.data["fps_method"] == "retime"
    assert retimed.data["result"]["duration"] == pytest.approx(4 * 25 / 24, abs=0.1)

    twos = _clip(tmp_path / "twos.mp4", "12", audio=False)
    anim = tool.execute({"operation": "conform", "input_path": str(twos), "content_type": "animation"})
    assert anim.success, anim.error
    assert anim.data["fps_method"] == "drop" and "minterpolate" not in anim.data["filter"]
    forced = tool.execute({"operation": "conform", "input_path": str(twos), "content_type": "animation",
                           "fps_method": "interpolate"})
    assert not forced.success

    stab = tool.execute({"operation": "conform", "input_path": str(slow), "stabilize": True,
                         "output_path": str(tmp_path / "stab.mp4")})
    assert stab.success, stab.error
    assert stab.data["stabilization"] in ("vidstab", "deshake")

    slowmo = tool.execute({"operation": "slow_motion", "input_path": str(_clip(tmp_path / "c24.mp4", "24")),
                           "slow_motion_factor": 2})
    assert slowmo.success, slowmo.error
    assert slowmo.data["result"]["duration"] == pytest.approx(4.0, abs=0.15)
    assert slowmo.data["result"]["fps"] == 24
