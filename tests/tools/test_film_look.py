"""film_look builds one finishing graph; intensities follow the style.

Filter-building, LUT resolution and color-match math run without ffmpeg. The
end-to-end tests finish a synthetic clip, check the BT.709 tags, render a
preview still and confirm that matching moves a dark shot toward its reference.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.enhancement.film_look import (  # noqa: E402
    LUT_DIR,
    STYLE_PRESETS,
    FilmLook,
    build_chain,
    compute_match,
    parse_signalstats,
    resolve_layers,
    resolve_lut,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_flat_vector_is_nearly_untouched():
    layers = resolve_layers({"style": "flat_vector"})
    assert layers["halation"] == layers["bloom"] == layers["vignette"] == 0
    assert 0 < layers["grain"] <= 0.05
    chain = build_chain(layers)
    assert "blend=all_mode=screen" not in chain and "vignette" not in chain
    assert "setparams=color_primaries=bt709" in chain


def test_explicit_layers_override_style_and_clamp():
    layers = resolve_layers({"style": "cinematic_ai", "grain": 2.0, "halation": 0})
    assert layers["grain"] == 1.0
    assert layers["halation"] == 0.0
    assert layers["bloom"] == STYLE_PRESETS["cinematic_ai"]["bloom"]


def test_style_intensity_grows_from_vector_to_archival():
    order = ["flat_vector", "anime", "stylized_2d", "live_action", "cinematic_ai", "archival"]
    grains = [STYLE_PRESETS[s]["grain"] for s in order]
    assert grains == sorted(grains)


def test_chain_has_halation_bloom_lut_and_luma_only_grain(tmp_path):
    lut = LUT_DIR / "warm_film.cube"
    chain = build_chain(resolve_layers({"style": "cinematic_ai"}), height=2160, lut_path=lut, lut_intensity=0.6)
    assert "lut3d=file=" in chain and "all_opacity=0.600" in chain
    assert chain.count("blend=all_mode=screen") == 2
    assert "colorchannelmixer" in chain  # halation is tinted
    assert "gblur=sigma=24.0" in chain  # halation sigma scales with height
    assert "noise=c0s=" in chain and "allf" not in chain
    # The RGB work happens after an explicit matrix choice, never the bt601 default.
    assert chain.index("scale=in_color_matrix=bt709") < chain.index("lut3d")


def test_resolve_lut_by_name_and_rejects_missing():
    assert resolve_lut("identity") == LUT_DIR / "identity.cube"
    with pytest.raises(FileNotFoundError):
        resolve_lut("does_not_exist")


def test_bundled_luts_are_valid_cube_files():
    for cube in LUT_DIR.glob("*.cube"):
        lines = cube.read_text(encoding="utf-8").splitlines()
        size = int(next(line.split()[1] for line in lines if line.startswith("LUT_3D_SIZE")))
        rows = [line for line in lines if line and line[0].isdigit()]
        assert len(rows) == size ** 3, cube.name


def test_parse_signalstats_and_match_math():
    stderr = "\n".join(
        f"[Parsed_metadata_2 @ 0x1] lavfi.signalstats.{k}={v}"
        for frame in ({"YAVG": 60, "YLOW": 20, "YHIGH": 100, "UAVG": 130, "VAVG": 120, "SATAVG": 20},
                      {"YAVG": 62, "YLOW": 22, "YHIGH": 102, "UAVG": 130, "VAVG": 120, "SATAVG": 22})
        for k, v in frame.items()
    )
    src = parse_signalstats(stderr)
    assert src["YAVG"] == 61 and src["YLOW"] == 21
    ref = {"YAVG": 120, "YLOW": 40, "YHIGH": 200, "UAVG": 126, "VAVG": 124, "SATAVG": 25}
    m = compute_match(src, ref)
    assert m["luma_gain"] == 1.6  # clamped
    assert m["u_offset"] == -4 and m["v_offset"] == 4
    assert m["saturation"] == round(25 / 21, 4)
    assert "lutyuv=" in build_chain(resolve_layers({"style": "none"}), match=m)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,pix_fmt,color_space,color_transfer,color_primaries", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)["streams"][0]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_end_to_end_apply_preview_and_match(tmp_path):
    clip = tmp_path / "clip.mp4"
    dark = tmp_path / "dark.mp4"
    for path, vf in ((clip, "null"), (dark, "eq=brightness=-0.25:contrast=0.7")):
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=2",
            "-f", "lavfi", "-i", "sine=f=440:d=2:sample_rate=48000",
            "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
        ], check=True)

    tool = FilmLook()
    done = tool.execute({"operation": "apply", "input_path": str(clip), "style": "cinematic_ai", "lut_path": "warm_film"})
    assert done.success, done.error
    info = _probe(Path(done.data["output"]))
    assert info["pix_fmt"] == "yuv420p"
    assert (info["color_space"], info["color_transfer"], info["color_primaries"]) == ("bt709",) * 3

    preview = tool.execute({"operation": "preview", "input_path": str(clip), "style": "archival"})
    assert preview.success, preview.error
    assert _probe(Path(preview.data["output"]))["width"] == 640  # before | after

    matched = tool.execute({"operation": "apply", "input_path": str(dark), "style": "none",
                            "match_reference_path": str(clip)})
    assert matched.success, matched.error
    ref = tool.measure(clip)["YAVG"]
    before = tool.measure(dark)["YAVG"]
    after = tool.measure(Path(matched.data["output"]))["YAVG"]
    assert abs(after - ref) < abs(before - ref) / 2
