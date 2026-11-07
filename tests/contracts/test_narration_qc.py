"""Narration QC must flag slips without crying wolf on native voices.

The cases come from a real run: fr-FR-RemyMultilingualNeural and
it-IT-GiuseppeMultilingualNeural reading the Spanish line "Paris. Londres. Tokio."
against four native voices. The Whisper model is replaced, so these tests pin the
rules and not its output.
"""

from __future__ import annotations

import json

import pytest

from tools.analysis.narration_qc import NarrationQC, align, analyze, is_flagged, normalize, split_sentences, tokens


def word(text: str, start: float, end: float, probability: float = 0.95) -> dict:
    return {"word": f" {text}", "start": start, "end": end, "probability": probability}


def spanish(_start: float, _end: float) -> float:
    return 0.98


def flagged(results: list[dict]) -> list[str]:
    return [item["text"] for item in results if item["flagged"]]


def test_sentences_keep_their_punctuation_and_skip_empty_ones():
    assert split_sentences("¿Y ahora qué? Nadie lo sabe...\n\n¡Vamos!") == ["Y ahora qué?", "Nadie lo sabe...", "Vamos!"]


def test_words_compare_without_case_or_accents():
    assert normalize("París") == "paris"
    assert tokens("Sin él, no hay.") == ["sin", "el", "no", "hay"]


def test_align_keeps_positions_across_a_replaced_word():
    assert align(["a", "londres", "b"], ["a", "london", "b"]) == [0, 1, 2, 3]


def test_a_clean_read_passes():
    words = [word("El", 0, 0.3), word("litio", 0.3, 0.8), word("mueve", 0.8, 1.2), word("todo.", 1.2, 1.6)]
    assert flagged(analyze("El litio mueve todo.", words, spanish)) == []


def test_numbers_spelled_out_are_not_wrong_words():
    words = [word("Por", 0, 0.3), word("10", 0.3, 0.7), word("años.", 0.7, 1.2)]
    assert analyze("Por diez años.", words, spanish)[0]["signals"] == []


def test_a_name_in_another_language_is_flagged():
    words = [word("Paris.", 0, 0.5), word("London.", 0.9, 1.3, 0.34), word("Tres", 2, 2.3), word("ciudades.", 2.3, 3)]
    results = analyze("Paris. Londres. Tres ciudades.", words, spanish)
    assert flagged(results) == ["Londres."]
    assert results[1]["heard"] == "London."


def test_a_short_line_flags_on_its_wrong_word_alone():
    words = [word("Londa,", 0, 0.6), word("otra", 1, 1.3), word("ciudad.", 1.3, 1.9)]
    assert flagged(analyze("Londres. Otra ciudad.", words, spanish)) == ["Londres."]


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        ([], False),
        (["low_confidence"], False),
        (["foreign_language"], False),
        (["wrong_words"], True),
        (["foreign_language", "low_confidence"], True),
    ],
)
def test_a_wrong_word_flags_alone_and_other_traces_need_company(signals, expected):
    assert is_flagged(signals) is expected


def said(text: str) -> list[dict]:
    return [word(item, index, index + 0.3) for index, item in enumerate(text.split())]


def test_one_wrong_word_flags_a_long_sentence_and_names_the_word():
    words = said("Buceas en un arrecife y ves un pech rojo sobre un coral")
    results = analyze("Buceas en un arrecife y ves un pez rojo sobre un coral.", words, spanish)
    assert results[0]["flagged"] and results[0]["wrong_words"] == ["pez"]


def test_words_run_together_are_not_wrong_words():
    assert flagged(analyze("Tu verias algo asi.", said("Tuverias algo asi"), spanish)) == []


def test_short_clips_skip_language_detection():
    words = [word("Tokio.", 0, 0.7)]
    calls = []
    analyze("Tokio.", words, lambda start, end: calls.append((start, end)) or 0.02)
    assert calls == []


def test_a_foreign_sounding_sentence_needs_a_second_trace():
    words = [word("Tampoco", 0, 0.6), word("el", 0.6, 0.7), word("mercado.", 0.7, 1.4)]
    results = analyze("Tampoco el mercado.", words, lambda *_: 0.3)
    assert results[0]["signals"] == ["foreign_language"] and not results[0]["flagged"]


def test_a_sentence_nobody_heard_is_flagged():
    words = [word("Primera", 0, 0.5), word("frase.", 0.5, 1)]
    results = analyze("Primera frase. Segunda frase perdida.", words, spanish)
    assert "Segunda frase perdida." in flagged(results)


@pytest.fixture
def run(monkeypatch, tmp_path):
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"audio")

    def check(inputs):
        return analyze(inputs["script_text"], [word("London.", 0, 0.5, 0.3)], spanish)

    monkeypatch.setattr(NarrationQC, "_check", lambda self, inputs: check(inputs))

    def execute(**extra):
        return NarrationQC().execute({"audio_path": str(audio), "script_text": "Londres.", "language": "es", **extra})

    return execute


def test_a_flag_asks_for_review_and_writes_the_report(run, tmp_path):
    result = run()
    assert result.data["verdict"] == "review"
    assert [item["text"] for item in result.data["flagged"]] == ["Londres."]
    report = json.loads((tmp_path / "voice.narration.json").read_text(encoding="utf-8"))
    assert report["verdict"] == "review" and report["transcript"] == "London."


def test_a_person_can_accept_what_they_listened_to(run):
    result = run(accepted_sentences=["Londres."])
    assert result.data["verdict"] == "pass"
    assert result.data["sentences"][0]["accepted"] is True


def test_missing_audio_fails(tmp_path):
    result = NarrationQC().execute({"audio_path": str(tmp_path / "no.mp3"), "script_text": "x", "language": "es"})
    assert not result.success
