"""technical_qc grades detector output; audio_master masters in two passes.

Parser and grading tests run without ffmpeg. The end-to-end test builds a
synthetic clip with a planted black run, a frozen hold and a silence, then
checks that each one is found and that the two-pass master lands on target.
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

from tools.analysis.technical_qc import (  # noqa: E402
    TechnicalQC,
    file_sha256,
    parse_analysis,
    verdict_for,
)
from tools.audio.audio_master import (  # noqa: E402
    AudioMaster,
    build_second_pass,
    parse_loudnorm_json,
    resolve_target,
)

STDERR = """
[blackdetect @ 0x1] black_start:4 black_end:6 black_duration:2
[freezedetect @ 0x2] lavfi.freezedetect.freeze_start: 4.04
[freezedetect @ 0x2] lavfi.freezedetect.freeze_duration: 1.9
[freezedetect @ 0x2] lavfi.freezedetect.freeze_end: 5.96
[freezedetect @ 0x2] lavfi.freezedetect.freeze_start: 7
[freezedetect @ 0x2] lavfi.freezedetect.freeze_duration: 3
[freezedetect @ 0x2] lavfi.freezedetect.freeze_end: 10
[silencedetect @ 0x3] silence_start: 5.02
[silencedetect @ 0x3] silence_end: 8 | silence_duration: 2.98
[silencedetect @ 0x3] silence_start: 11.5
[Parsed_ebur128_1 @ 0x4] Summary:

  Integrated loudness:
    I:         -18.5 LUFS
    Threshold: -28.9 LUFS

  Loudness range:
    LRA:         6.1 LU

  True peak:
    Peak:       -0.4 dBFS
"""

PROBE = {"duration": 12.0, "has_video": True, "has_audio": True, "width": 1920,
         "height": 1080, "fps": 24.0, "video_codec": "h264", "pixel_format": "yuv420p"}


def test_report_records_the_fingerprint_of_the_checked_file(tmp_path, monkeypatch):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"master bytes")
    tool = TechnicalQC()
    monkeypatch.setattr(tool, "_probe", lambda path: dict(PROBE))
    monkeypatch.setattr(tool, "_analyze", lambda path, probe, inputs: STDERR)

    result = tool.execute({"input_path": str(video)})

    assert result.success is True
    assert result.data["input_sha256"] == file_sha256(video)
    report = json.loads(video.with_suffix(".qc.json").read_text(encoding="utf-8"))
    assert report["input_sha256"] == file_sha256(video)
    video.write_bytes(b"remastered bytes")
    assert report["input_sha256"] != file_sha256(video)


def test_parse_analysis_reads_every_detector():
    a = parse_analysis(STDERR)
    assert a["black"] == [{"start": 4.0, "end": 6.0, "duration": 2.0}]
    assert [f["start"] for f in a["freeze"]] == [4.04, 7.0]
    assert a["silence"][0] == {"start": 5.02, "end": 8.0}
    assert a["silence"][1]["end"] is None  # runs to the end of the file
    assert a["loudness"] == {"integrated": -18.5, "lra": 6.1, "true_peak": -0.4}


def test_evaluate_grades_and_dedupes_black_freeze():
    findings = TechnicalQC.evaluate(PROBE, parse_analysis(STDERR), {"profile": "youtube"})
    checks = [(f["check"], f["severity"]) for f in findings]
    assert ("black", "warn") in checks
    # The freeze inside the black run is not reported twice.
    assert sum(1 for c, _ in checks if c == "freeze") == 1
    # Trailing silence that reaches the end is treated as a fade.
    assert ("silence", "info") in checks
    # -18.5 vs -14 is 4.5 LU off: block. TP -0.4 above the -1 ceiling: warn.
    assert ("loudness", "block") in checks
    assert ("true_peak", "warn") in checks
    assert verdict_for(findings) == "block"


def test_intentional_ranges_downgrade_to_info():
    findings = TechnicalQC.evaluate(
        PROBE, parse_analysis(STDERR),
        {"intentional_ranges": [{"start": 6.9, "end": 10.1, "reason": "hold"}]},
    )
    freeze = [f for f in findings if f["check"] == "freeze"]
    assert freeze[0]["severity"] == "info" and "hold" in freeze[0]["message"]


def test_conformity_and_licenses_block(tmp_path):
    findings = TechnicalQC.evaluate(PROBE, parse_analysis(""), {"expected": {"fps": 30, "width": 1920}})
    assert [f["message"] for f in findings if f["check"] == "conformity"] == [
        "fps: expected 30, got 24.000"
    ]
    manifest = tmp_path / "asset_manifest.json"
    manifest.write_text(json.dumps({"version": "1", "assets": [
        {"id": "music_1", "path": "a.mp3", "license": ""},
        {"id": "img_1", "path": "b.png", "license": "CC0"},
    ]}), encoding="utf-8")
    lic = TechnicalQC._license_findings(str(manifest))
    assert lic[0]["severity"] == "block" and "music_1" in lic[0]["message"]


def test_audio_master_target_and_second_pass():
    assert resolve_target({"preset": "podcast"})["I"] == -16.0
    assert resolve_target({"target_lufs": -99})["I"] == -40.0
    measured = parse_loudnorm_json(
        'x\n{\n "input_i" : "-20.10",\n "input_tp" : "-3.00",\n "input_lra" : "5.0",\n'
        ' "input_thresh" : "-30.5",\n "target_offset" : "0.2",\n "normalization_type" : "dynamic"\n}\n'
    )
    chain = build_second_pass(measured, resolve_target({}), "deesser")
    assert chain.startswith("deesser,loudnorm=I=-14.0")
    assert "measured_I=-20.1" in chain and "linear=true" in chain


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_end_to_end_qc_and_master(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=320x240:r=24:d=4",
        "-f", "lavfi", "-i", "color=black:s=320x240:r=24:d=2",
        "-f", "lavfi", "-i", "testsrc2=s=320x240:r=24:d=4",
        "-f", "lavfi", "-i", "sine=f=440:d=5:sample_rate=48000",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=3",
        "-f", "lavfi", "-i", "sine=f=330:d=2:sample_rate=48000",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p[v];"
        "[3:a][4:a][5:a]concat=n=3:v=0:a=1,volume=0.2[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", str(clip),
    ], check=True)

    qc = TechnicalQC().execute({"input_path": str(clip)})
    assert qc.success, qc.error
    found = {f["check"] for f in qc.data["findings"] if f["severity"] != "info"}
    assert {"black", "silence"} <= found
    assert Path(qc.data["report_path"]).exists()

    master = AudioMaster().execute({"operation": "master", "input_path": str(clip)})
    assert master.success, master.error
    assert master.data["verification_passed"]
    assert abs(master.data["after"]["input_i"] - (-14.0)) <= 1.0
