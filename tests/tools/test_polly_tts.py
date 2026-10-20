"""Focused tests for the Amazon Polly TTS tool. No live AWS calls."""

import io
import sys
import wave
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import BaseTool, ToolStatus
from tools.audio.polly_tts import PollyTTS
from tools.tool_registry import ToolRegistry

FAKE_MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 32


class _FakeClient:
    def __init__(self):
        self.calls = []

    def synthesize_speech(self, **kwargs):
        self.calls.append(kwargs)
        data = b"\x00\x00" * 160 if kwargs["OutputFormat"] == "pcm" else FAKE_MP3
        return {"AudioStream": io.BytesIO(data)}


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "fake")


def test_contract():
    t = PollyTTS()
    assert issubclass(PollyTTS, BaseTool)
    assert (t.name, t.capability, t.provider) == ("polly_tts", "tts", "polly")
    assert t.DEFAULT_VOICE == "Raul" and t.DEFAULT_ENGINE == "long-form"


def test_registry_discovers_it():
    reg = ToolRegistry()
    reg.discover("tools")
    assert reg.get("polly_tts") is not None
    assert "polly_tts" in [t.name for t in reg.get_by_capability("tts")]


def test_status_unavailable_without_credentials(monkeypatch):
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    assert PollyTTS().get_status() == ToolStatus.UNAVAILABLE
    assert PollyTTS().execute({"text": "hola"}).success is False


def test_split_respects_limit():
    text = " ".join(["Esta es una frase de prueba."] * 300)
    chunks = PollyTTS._split(text)
    assert len(chunks) > 1
    assert all(len(c) <= 3000 for c in chunks)
    assert " ".join(chunks) == text


def test_billable_chars_ignore_ssml():
    assert PollyTTS._billable_chars("<speak>hola</speak>") == 4


def test_mp3_synthesis(aws_env, monkeypatch, tmp_path):
    fake = _FakeClient()
    monkeypatch.setattr(PollyTTS, "_client", lambda self: fake)
    monkeypatch.setattr(PollyTTS, "get_status", lambda self: ToolStatus.AVAILABLE)
    out = tmp_path / "v.mp3"
    r = PollyTTS().execute({"text": "Hola mundo.", "output_path": str(out)})
    assert r.success, r.error
    assert out.read_bytes() == FAKE_MP3
    call = fake.calls[0]
    assert (call["VoiceId"], call["Engine"], call["LanguageCode"]) == ("Raul", "long-form", "es-ES")


def test_wav_synthesis(aws_env, monkeypatch, tmp_path):
    fake = _FakeClient()
    monkeypatch.setattr(PollyTTS, "_client", lambda self: fake)
    monkeypatch.setattr(PollyTTS, "get_status", lambda self: ToolStatus.AVAILABLE)
    out = tmp_path / "v.wav"
    r = PollyTTS().execute({"text": "Hola.", "output_path": str(out), "output_format": "wav", "voice_id": "Lucia"})
    assert r.success, r.error
    with wave.open(str(out)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
    assert fake.calls[0]["VoiceId"] == "Lucia"
