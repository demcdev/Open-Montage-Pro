"""The beat grid must find a known pulse and refuse to invent one.

Click tracks have an exact answer, so they pin tempo, beat position and bars. Noise
and a held tone pin the other half: music with no pulse must stay unusable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from lib.pipeline_loader import load_pipeline
from tools.analysis import beat_grid
from tools.analysis.beat_grid import SAMPLE_RATE, BeatGrid, analyze, playing_stretch, snap_cuts, to_timeline
from tools.analysis.cold_review import NARRATIVE_PIPELINES

ROOT = Path(__file__).resolve().parent.parent.parent
FIRST_BEAT = 0.5
MAX_ERROR_SECONDS = 0.02  # One frame at 60 fps is 16 ms; the mean error must stay near it.


def clicks(bpm: float, seconds: float = 30, accent: bool = True) -> np.ndarray:
    samples = np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)
    length = int(0.03 * SAMPLE_RATE)
    time = np.arange(length) / SAMPLE_RATE
    for index, moment in enumerate(np.arange(FIRST_BEAT, seconds - 0.1, 60 / bpm)):
        frequency, level = (80, 1.0) if accent and index % 4 == 0 else (1200, 0.5)
        start = int(moment * SAMPLE_RATE)
        samples[start : start + length] += level * np.sin(2 * np.pi * frequency * time) * np.exp(-time * 80)
    return samples


@pytest.mark.parametrize("bpm", [70, 90, 120, 128, 150])
def test_a_click_track_is_read_exactly(bpm):
    result = analyze(clicks(bpm))
    truth = np.arange(FIRST_BEAT, 29.9, 60 / bpm)
    beats = np.array(result["beats"])
    assert result["usable"]
    assert result["bpm"] == pytest.approx(bpm, rel=0.01)
    assert abs(len(beats) - len(truth)) <= 1
    assert np.abs(beats[:, None] - truth[None, :]).min(axis=1).mean() < MAX_ERROR_SECONDS


def test_bars_start_on_the_accent():
    result = analyze(clicks(120))
    assert result["downbeats_reliable"]
    assert result["downbeats"][0] == pytest.approx(FIRST_BEAT, abs=0.03)
    assert result["downbeats"][1] == pytest.approx(FIRST_BEAT + 2.0, abs=0.03)


def test_bars_are_not_guessed_without_accents():
    assert not analyze(clicks(120, accent=False))["downbeats_reliable"]


def test_a_fast_track_can_read_at_half_tempo_and_the_range_corrects_it():
    assert analyze(clicks(174))["bpm"] == pytest.approx(87, rel=0.02)
    assert analyze(clicks(174), min_bpm=120)["bpm"] == pytest.approx(174, rel=0.02)


def test_noise_has_no_grid():
    noise = np.random.default_rng(0).normal(0, 0.1, SAMPLE_RATE * 30).astype(np.float32)
    result = analyze(noise)
    assert not result["usable"] and result["beats"] == []


def test_a_held_tone_has_no_grid():
    time = np.arange(SAMPLE_RATE * 30) / SAMPLE_RATE
    tone = np.sin(2 * np.pi * 220 * time) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * time))
    assert not analyze(tone.astype(np.float32))["usable"]


@pytest.mark.parametrize("length", [0, 100, SAMPLE_RATE])
def test_very_short_audio_has_no_grid(length):
    assert not analyze(np.zeros(length, dtype=np.float32))["usable"]


def test_silence_has_no_grid():
    assert not analyze(np.zeros(SAMPLE_RATE * 10, dtype=np.float32))["usable"]


def test_timeline_applies_offset_and_entry():
    grid = {"beats": [1.0, 2.0, 3.0], "downbeats": [1.0, 3.0]}
    assert to_timeline(grid, 2.0, 10.0) == {"beats": [10.0, 11.0], "downbeats": [11.0]}


def test_cuts_move_to_the_nearest_beat():
    results = snap_cuts([1.1, 2.9], [1.0, 2.0, 3.0])
    assert [item["to"] for item in results] == [1.0, 3.0]
    assert results[0]["moved"] == pytest.approx(-0.1)
    assert all(item["snapped"] for item in results)


def test_a_cut_far_from_any_beat_stays():
    result = snap_cuts([1.5], [1.0, 2.0], tolerance=0.25)[0]
    assert result == {"from": 1.5, "to": 1.5, "moved": 0.0, "snapped": False}


def test_two_cuts_never_land_on_the_same_beat():
    results = snap_cuts([1.0, 1.1], [1.0, 2.0])
    assert [item["to"] for item in results] == [1.0, 1.1]
    assert not results[1]["snapped"]


def test_min_gap_protects_short_shots():
    results = snap_cuts([1.0, 1.45], [1.0, 1.5], min_gap=0.6)
    assert [item["to"] for item in results] == [1.0, 1.45]


def test_no_beats_means_no_movement():
    assert snap_cuts([1.0], [])[0]["snapped"] is False


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


@pytest.fixture
def wav(tmp_path) -> Path:
    path = tmp_path / "music.wav"
    raw = tmp_path / "music.raw"
    raw.write_bytes(clicks(120).tobytes())
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-i", str(raw), str(path)],
        check=True,
    )
    return path


@needs_ffmpeg
def test_the_tool_snaps_and_writes_its_report(wav):
    result = BeatGrid().execute({"audio_path": str(wav), "cut_times": [2.6]})
    assert result.success, result.error
    assert result.data["snapped_cuts"][0]["to"] == pytest.approx(2.5, abs=0.03)
    report = json.loads(wav.with_suffix(".beats.json").read_text(encoding="utf-8"))
    assert report["bpm"] == pytest.approx(120, rel=0.01)


def test_only_the_stretch_that_plays_is_analyzed():
    samples = np.arange(SAMPLE_RATE * 10, dtype=np.float32)
    stretch = playing_stretch(samples, 2.0, 3.0)
    assert len(stretch) == SAMPLE_RATE * 3 and stretch[0] == SAMPLE_RATE * 2
    assert len(playing_stretch(samples, 2.0, None)) == SAMPLE_RATE * 8


@needs_ffmpeg
def test_beats_land_in_video_time(wav):
    result = BeatGrid().execute({"audio_path": str(wav), "offset_seconds": 10.0, "music_start_seconds": 3.0})
    first = result.data["timeline"]["beats"][0]
    # The track has a click every 0.5 s from 0.5, so one lands exactly on second 10.
    assert first == pytest.approx(3.0, abs=0.03) or first == pytest.approx(3.5, abs=0.03)


@needs_ffmpeg
def test_unreliable_bars_fall_back_to_beats(wav, monkeypatch):
    original = beat_grid.analyze

    def unreliable(*args):
        return {**original(*args), "downbeats_reliable": False}

    monkeypatch.setattr(beat_grid, "analyze", unreliable)
    result = BeatGrid().execute({"audio_path": str(wav), "cut_times": [1.0], "snap_to": "downbeats"})
    assert result.data["snap_target"] == "beats"
    assert result.data["snapped_cuts"][0]["snapped"]


@needs_ffmpeg
def test_music_without_pulse_snaps_nothing(wav, monkeypatch):
    monkeypatch.setattr(beat_grid, "analyze", lambda *args: {**analyze(*args), "usable": False})
    result = BeatGrid().execute({"audio_path": str(wav), "cut_times": [1.0]})
    assert "snapped_cuts" not in result.data


def test_missing_audio_fails(tmp_path):
    assert not BeatGrid().execute({"audio_path": str(tmp_path / "no.mp3")}).success


@pytest.mark.parametrize("pipeline", sorted(NARRATIVE_PIPELINES))
def test_narrative_edit_stages_can_use_it(pipeline):
    edit = next(stage for stage in load_pipeline(pipeline)["stages"] if stage["name"] == "edit")
    assert "beat_grid" in edit["tools_available"]


def test_the_catalog_routes_beat_cuts_to_the_tool():
    catalog = (ROOT / "skills" / "creative" / "technique-catalog.md").read_text(encoding="utf-8")
    row = next(line for line in catalog.splitlines() if line.startswith("| `cut_beat`"))
    assert "`tool:beat_grid`" in row and "Fase 5" not in row
