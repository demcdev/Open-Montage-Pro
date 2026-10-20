"""Regression: mixing 24 kHz mono TTS with full-band stereo music must not
downmix / band-limit the music (it sounded like a radio).

The mixer must deliver 48 kHz stereo and keep the music's high frequencies.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.audio.audio_mixer import AudioMixer

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


def _gen(path: Path, lavfi: str, rate: int, channels: int, dur: float = 2.0):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"{lavfi}:d={dur}", "-ar", str(rate), "-ac", str(channels), str(path)],
        check=True,
    )


def _probe(path: Path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    rate, ch = out.split(",")
    return int(rate), int(ch)


def _hf_level(path: Path) -> float:
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "highpass=f=14000,volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    for line in err.splitlines():
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    return -90.0


@pytest.fixture
def sources(tmp_path):
    voice = tmp_path / "voice.wav"
    music = tmp_path / "music.wav"
    _gen(voice, "sine=f=300", 24000, 1)
    # music with 16 kHz content: only survives if the mix runs at >= 44.1 kHz
    _gen(music, "sine=f=16000", 44100, 2)
    return voice, music


def test_mix_outputs_48k_stereo_and_keeps_high_frequencies(tmp_path, sources):
    voice, music = sources
    out = tmp_path / "mix.wav"
    result = AudioMixer().execute({
        "operation": "mix",
        "tracks": [{"path": str(voice), "role": "speech"}, {"path": str(music), "role": "music", "volume": 0.5}],
        "normalize": False,
        "output_path": str(out),
    })
    assert result.success, result.error
    assert _probe(out) == (48000, 2)
    assert _hf_level(out) > -40, "high frequencies of the music were lost"


def test_duck_outputs_48k_stereo_and_keeps_high_frequencies(tmp_path, sources):
    voice, music = sources
    out = tmp_path / "duck.wav"
    result = AudioMixer().execute({
        "operation": "duck",
        "primary_audio": str(voice),
        "secondary_audio": str(music),
        "ducking": {"music_volume_during_speech": 0.5},
        "output_path": str(out),
    })
    assert result.success, result.error
    assert _probe(out) == (48000, 2)
    assert _hf_level(out) > -40, "high frequencies of the music were lost"
