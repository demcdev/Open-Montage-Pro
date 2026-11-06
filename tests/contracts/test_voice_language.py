"""A voice named for another language must be an approved choice, never a default."""

from __future__ import annotations

import pytest

from lib.voice_language import mismatch_error, voice_language
from tools.audio.edge_tts import EdgeTTS
from tools.audio.tts_selector import TTSSelector


@pytest.mark.parametrize(
    ("voice", "language"),
    [
        ("fr-FR-RemyMultilingualNeural", "fr"),
        ("es-US-Chirp3-HD-Puck", "es"),
        ("it-IT-GiuseppeMultilingualNeural", "it"),
        ("Rachel", None),
        ("21m00Tcm4TlvDq8ikWAM", None),
        ("", None),
        (None, None),
    ],
)
def test_voice_language_reads_the_locale_prefix(voice, language):
    assert voice_language(voice) == language


@pytest.mark.parametrize(
    "inputs",
    [
        {"voice": "es-MX-JorgeNeural", "language_code": "es"},
        {"voice_id": "es-US-Chirp3-HD-Puck", "language_code": "es-US"},
        {"voice": "fr-FR-RemyMultilingualNeural"},
        {"voice": "Rachel", "language_code": "es"},
        {"language_code": "es"},
        {"voice": "fr-FR-RemyMultilingualNeural", "language_code": "es", "allow_voice_language_mismatch": True},
    ],
)
def test_allowed_narration(inputs):
    assert mismatch_error(inputs) is None


@pytest.mark.parametrize("field", ["voice", "voice_id"])
def test_a_foreign_voice_is_refused(field):
    error = mismatch_error({field: "fr-FR-RemyMultilingualNeural", "language_code": "es-MX"})
    assert "fr-FR-RemyMultilingualNeural" in error and "voice_language" in error


def test_selector_refuses_before_choosing_a_provider(monkeypatch):
    selector = TTSSelector()
    monkeypatch.setattr(selector, "_select_best_tool", lambda *_: pytest.fail("provider was selected"))
    result = selector.execute({"text": "hola", "voice": "it-IT-GiuseppeMultilingualNeural", "language_code": "es"})
    assert not result.success and "it-IT-GiuseppeMultilingualNeural" in result.error


def test_edge_refuses_a_direct_call(monkeypatch):
    tool = EdgeTTS()
    monkeypatch.setattr(tool, "check_dependencies", lambda: None)
    monkeypatch.setattr(tool, "_generate", lambda _: pytest.fail("audio was generated"))
    result = tool.execute({"text": "hola", "voice": "fr-FR-RemyMultilingualNeural", "language_code": "es"})
    assert not result.success and "voice_language" in result.error


def test_the_override_is_declared_where_it_is_read():
    for tool in (TTSSelector, EdgeTTS):
        assert "allow_voice_language_mismatch" in tool.input_schema["properties"]
