"""The sound library finds effects and turns a sound plan into mixer tracks."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.audio.audio_master import AudioMaster
from tools.audio.sound_library import SoundLibrary


def library(tmp_path: Path) -> Path:
    effects = [
        {"file": "error.mp3", "name": "error", "category": "impact", "tags": ["fail"], "duration_seconds": 1},
        {"file": "agua.mp3", "name": "agua", "category": "ambience", "tags": ["water"], "duration_seconds": 5.5},
    ]
    for effect in effects:
        (tmp_path / effect["file"]).write_bytes(b"x")
    (tmp_path / "catalog.json").write_text(json.dumps({"effects": effects}), encoding="utf-8")
    return tmp_path


def resolve(tmp_path: Path, plan: dict):
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    words = [{"word": "Reprobaron.", "start": 40.9, "end": 41.4}, {"word": "reprobaron", "start": 50.0, "end": 50.5}]
    (tmp_path / "words.json").write_text(json.dumps(words), encoding="utf-8")
    return SoundLibrary().execute({"operation": "resolve", "library_dir": str(library(tmp_path)), "sound_plan_path": str(tmp_path / "plan.json"), "words_path": str(tmp_path / "words.json")})


def test_effects_are_found_by_category_and_tag(tmp_path):
    tool = SoundLibrary()
    assert tool.execute({"library_dir": str(library(tmp_path)), "category": "impact"}).data["count"] == 1
    assert tool.execute({"library_dir": str(tmp_path), "query": "water"}).data["effects"][0]["name"] == "agua"


def test_a_cue_lands_on_its_word_and_follows_the_voice(tmp_path):
    result = resolve(tmp_path, {"cues": [{"effect": "error", "word": "reprobaron", "occurrence": 2, "offset": -0.1}]})
    assert result.data["tracks"][0]["start_seconds"] == 49.9


def test_a_bed_repeats_until_its_end(tmp_path):
    result = resolve(tmp_path, {"beds": [{"effect": "agua", "from": 0, "to": 12}]})
    assert [track["start_seconds"] for track in result.data["tracks"]] == [0.0, 5.0, 10.0]


def test_unknown_effects_and_words_are_refused(tmp_path):
    assert "Unknown effect" in resolve(tmp_path, {"cues": [{"effect": "nada", "seconds": 1}]}).error
    assert "not in the narration" in resolve(tmp_path, {"cues": [{"effect": "error", "word": "pez"}]}).error


def test_a_master_that_misses_the_target_is_leveled_once(tmp_path, monkeypatch):
    calls = []

    def fake(self, src, out, inputs, target, ceiling, pre):
        calls.append(src.name)
        return {"verification_passed": len(calls) > 1}

    monkeypatch.setattr(AudioMaster, "_pass", fake)
    monkeypatch.setattr(AudioMaster, "_level", lambda self, src, out: None)
    data = AudioMaster()._master(tmp_path / "a.mp4", {"output_path": str(tmp_path / "b.mp4")}, {"I": -14.0, "TP": -1.0, "LRA": 11.0})
    assert calls == ["a.mp4", "b_leveled.mkv"] and data["leveled"]
