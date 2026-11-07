"""No tool may write to the working directory by default.

A relative default such as "tts_output.mp3" lands wherever the process runs, usually
the repo root, where the file looks like project work and can reach a commit.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from lib import paths
from tools.audio.audio_mixer import AudioMixer

ROOT = Path(__file__).resolve().parent.parent.parent
RELATIVE_DEFAULT = re.compile(r'inputs\.get\(\s*"output_path",\s*f?"[^/"\n]*"')


def test_no_tool_defaults_to_the_working_directory():
    offenders = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "tools").rglob("*.py")
        if RELATIVE_DEFAULT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_scratch_path_creates_its_folder(monkeypatch, tmp_path):
    folder = tmp_path / "a" / "b"
    monkeypatch.setattr(paths, "SCRATCH_DIR", folder)
    assert paths.scratch_path("x.wav") == folder / "x.wav"
    assert folder.is_dir()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_real_tool_writes_there_without_a_path(monkeypatch, tmp_path):
    tone = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", str(tone)],
        check=True,
    )
    monkeypatch.setattr(paths, "SCRATCH_DIR", tmp_path / "scratch")
    monkeypatch.chdir(tmp_path)
    result = AudioMixer().execute({"operation": "mix", "tracks": [{"path": str(tone), "role": "speech"}], "normalize": False})
    assert result.success, result.error
    assert (tmp_path / "scratch" / "mixed_audio.wav").is_file()
    assert not (tmp_path / "mixed_audio.wav").exists()
