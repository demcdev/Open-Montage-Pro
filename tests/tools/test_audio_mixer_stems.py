"""Stems must rebuild the mix, line up, and leave the mix itself untouched."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tools.analysis.technical_qc import file_sha256
from tools.audio.audio_mixer import AudioMixer
from tools.publishers.export_bundle import ExportBundle

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")

RATE = 48000
SECONDS = 6.0
MAX_MIX_LATENCY = 480


def tone(path: Path, frequency: int, seconds: float, volume: float = 1.6) -> str:
    """Peak 0.2: the sine source peaks at 1/8."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency={frequency}:sample_rate={RATE}:duration={seconds}",
         "-af", f"volume={volume},pan=stereo|c0=c0|c1=c0", str(path)],
        check=True,
    )
    return str(path)


def read(path: str | Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(samples**2)))


def window(samples: np.ndarray, start: float, end: float) -> np.ndarray:
    return samples[int(start * RATE) : int(end * RATE)]


@pytest.fixture
def tracks(tmp_path) -> list[dict]:
    return [
        {"path": tone(tmp_path / "v1.wav", 300, 1.5), "role": "speech", "start_seconds": 0},
        {"path": tone(tmp_path / "v2.wav", 350, 1.0), "role": "speech", "start_seconds": 3.0},
        {"path": tone(tmp_path / "m.wav", 500, SECONDS), "role": "music", "volume": 0.5},
        {"path": tone(tmp_path / "s.wav", 900, 0.5), "role": "sfx", "start_seconds": 2.0},
    ]


def mix(tmp_path: Path, tracks: list[dict], **extra):
    inputs = {
        "operation": "full_mix",
        "tracks": tracks,
        "output_path": str(tmp_path / "mix.wav"),
        "normalize": False,
        "target_duration": SECONDS,
        "stems_dir": str(tmp_path / "stems"),
        **extra,
    }
    result = AudioMixer().execute(inputs)
    assert result.success, result.error
    return result


def test_each_role_gets_a_stem(tmp_path, tracks):
    stems = mix(tmp_path, tracks).data["stems"]
    assert {Path(path).name for path in stems.values()} == {"dialogue.wav", "music.wav", "sfx.wav"}


def test_stems_share_one_length(tmp_path, tracks):
    stems = mix(tmp_path, tracks).data["stems"]
    assert {len(read(path)) for path in stems.values()} == {int(SECONDS * RATE)}


def test_length_comes_from_the_tracks_without_a_target(tmp_path, tracks):
    stems = mix(tmp_path, tracks, target_duration=None).data["stems"]
    lengths = {len(read(path)) for path in stems.values()}
    assert len(lengths) == 1 and lengths.pop() == pytest.approx(SECONDS * RATE, abs=RATE * 0.05)


def test_stems_rebuild_the_mix(tmp_path, tracks):
    result = mix(tmp_path, tracks)
    total = sum(read(path) for path in result.data["stems"].values())
    full = read(result.data["output"])
    # The mix's limiter adds about 5 ms of latency that stems do not have.
    length = min(len(total), len(full)) - MAX_MIX_LATENCY
    residual = min(rms(full[lag : lag + length] - total[:length]) for lag in range(MAX_MIX_LATENCY))
    assert residual < rms(full) * 0.1


def test_each_stem_holds_only_its_role(tmp_path, tracks):
    stems = mix(tmp_path, tracks, ducking={"enabled": False}).data["stems"]
    dialogue = read(stems["dialogue"])
    effects = read(stems["sfx"])
    assert rms(window(dialogue, 0.2, 1.2)) > 0.05
    assert rms(window(dialogue, 2.0, 2.5)) < 1e-6
    assert rms(window(effects, 2.1, 2.4)) > 0.05
    assert rms(window(effects, 0.2, 1.2)) < 1e-6


def test_tracks_keep_their_place_on_the_timeline(tmp_path, tracks):
    dialogue = read(mix(tmp_path, tracks).data["stems"]["dialogue"])
    assert rms(window(dialogue, 2.6, 2.9)) < 1e-6
    assert rms(window(dialogue, 3.1, 3.9)) > 0.05


def test_music_stem_carries_the_ducking(tmp_path, tracks):
    music = read(mix(tmp_path, tracks).data["stems"]["music"])
    assert rms(window(music, 0.5, 1.2)) < rms(window(music, 4.8, 5.8)) * 0.8


def test_track_volume_reaches_the_stem(tmp_path, tracks):
    music = read(mix(tmp_path, tracks, ducking={"enabled": False}).data["stems"]["music"])
    assert rms(window(music, 1, 5)) == pytest.approx(0.2 * 0.5 / np.sqrt(2), rel=0.05)


def test_mono_narration_stays_at_its_level(tmp_path, tracks):
    mono = tmp_path / "mono.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=24000:duration=1",
         "-af", "volume=1.6", "-ac", "1", str(mono)],
        check=True,
    )
    stems = mix(tmp_path, [{"path": str(mono), "role": "speech"}]).data["stems"]
    assert rms(window(read(stems["dialogue"]), 0.2, 0.8)) == pytest.approx(0.2 / np.sqrt(2), rel=0.05)


def test_mono_narration_does_not_collapse_the_mix(tmp_path, tracks):
    mono = tmp_path / "mono.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=24000:duration=1",
         "-ac", "1", str(mono)],
        check=True,
    )
    output = mix(tmp_path, [{"path": str(mono), "role": "speech"}, tracks[2]]).data["output"]
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=channels,sample_rate", "-of", "csv=p=0", output],
        capture_output=True,
        text=True,
        check=True,
    )
    assert probe.stdout.strip() == "48000,2"


def test_a_role_without_tracks_has_no_stem(tmp_path, tracks):
    stems = mix(tmp_path, [track for track in tracks if track["role"] != "sfx"]).data["stems"]
    assert set(stems) == {"dialogue", "music"}


def test_no_stems_unless_asked(tmp_path, tracks):
    result = mix(tmp_path, tracks, stems_dir=None)
    assert result.data["stems"] == {} and not (tmp_path / "stems").exists()


def test_stems_do_not_change_the_mix(tmp_path, tracks):
    with_stems = read(mix(tmp_path, tracks, output_path=str(tmp_path / "a.wav")).data["output"])
    without = read(mix(tmp_path, tracks, output_path=str(tmp_path / "b.wav"), stems_dir=None).data["output"])
    assert np.array_equal(with_stems, without)


def export(tmp_path: Path, stems_dir: Path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"master")
    report = {"input_sha256": file_sha256(video), "verdict": "pass", "profile": "youtube", "findings": []}
    video.with_suffix(".qc.json").write_text(json.dumps(report), encoding="utf-8")
    return ExportBundle().execute(
        {"pipeline": "clip-factory", "video_path": str(video), "title": "t", "export_dir": str(tmp_path / "out"), "stems_dir": str(stems_dir)}
    )


def test_stems_travel_with_the_export(tmp_path, tracks):
    result = export(tmp_path, Path(mix(tmp_path, tracks).data["stems"]["music"]).parent)
    assert result.success, result.error
    assert {path.name for path in (tmp_path / "out" / "stems").iterdir()} == {"dialogue.wav", "music.wav", "sfx.wav"}


def test_export_refuses_a_missing_stems_folder(tmp_path):
    result = export(tmp_path, tmp_path / "none")
    assert not result.success and "stems_dir" in result.error
