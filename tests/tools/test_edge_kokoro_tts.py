"""Focused tests for the free TTS providers: edge_tts (online) and kokoro_tts (local CPU).

No live calls: the edge-tts stream and the Kokoro engine are monkeypatched.
Covers the tool contract, registry discovery, status behavior, voice/rate
resolution, word timestamps, and execute() guardrails.
"""

import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import BaseTool, ToolRuntime, ToolStatus, ToolTier
from tools.tool_registry import ToolRegistry
from tools.audio import kokoro_tts
from tools.audio.edge_tts import EdgeTTS
from tools.audio.kokoro_tts import KokoroTTS


# ---- Contract ----

class TestContract:
    @pytest.mark.parametrize("cls", [EdgeTTS, KokoroTTS])
    def test_inherits_base_tool(self, cls):
        assert issubclass(cls, BaseTool)

    def test_edge_identity(self):
        t = EdgeTTS()
        assert t.name == "edge_tts"
        assert t.capability == "tts"
        assert t.provider == "edge_tts"
        assert t.runtime == ToolRuntime.API
        assert t.tier == ToolTier.VOICE
        assert t.fallback == "kokoro_tts"
        assert t.estimate_cost({"text": "x" * 10_000}) == 0.0

    def test_kokoro_identity(self):
        t = KokoroTTS()
        assert t.name == "kokoro_tts"
        assert t.capability == "tts"
        assert t.provider == "kokoro"
        assert t.runtime == ToolRuntime.LOCAL
        assert t.tier == ToolTier.VOICE
        assert t.fallback == "piper_tts"
        assert t.supports["offline"] is True
        assert t.estimate_cost({"text": "x" * 10_000}) == 0.0

    @pytest.mark.parametrize("cls", [EdgeTTS, KokoroTTS])
    def test_get_info_valid(self, cls):
        info = cls().get_info()
        assert info["capability"] == "tts"
        assert "text" in info["input_schema"]["properties"]


# ---- Registry discovery ----

class TestRegistry:
    def test_discovered_as_tts_providers(self):
        reg = ToolRegistry()
        reg.discover()
        names = {t.name for t in reg.get_by_capability("tts")}
        assert {"edge_tts", "kokoro_tts"} <= names
        assert {t.name for t in reg.get_by_provider("kokoro")} == {"kokoro_tts"}


# ---- Edge TTS ----

class TestEdgeTTS:
    def test_voice_defaults_by_language(self):
        assert EdgeTTS._resolve_voice({"language_code": "es-MX"}) == "es-MX-JorgeNeural"
        assert EdgeTTS._resolve_voice({"language_code": "en-US"}) == "en-US-AndrewNeural"
        assert EdgeTTS._resolve_voice({}) == "es-MX-JorgeNeural"
        assert EdgeTTS._resolve_voice({"voice_id": "es-ES-AlvaroNeural"}) == "es-ES-AlvaroNeural"
        assert EdgeTTS._resolve_voice({"voice": "a", "voice_id": "b"}) == "a"

    def test_rate_and_pitch_resolution(self):
        assert EdgeTTS._resolve_rate({}) == "+0%"
        assert EdgeTTS._resolve_rate({"speed": 1.25}) == "+25%"
        assert EdgeTTS._resolve_rate({"speaking_rate": 0.8}) == "-20%"
        assert EdgeTTS._resolve_rate({"rate": "+5%", "speed": 2.0}) == "+5%"
        assert EdgeTTS._resolve_pitch({}) == "+0Hz"
        assert EdgeTTS._resolve_pitch({"pitch": -4}) == "-4Hz"
        assert EdgeTTS._resolve_pitch({"pitch": "+3Hz"}) == "+3Hz"

    def _patch_edge(self, monkeypatch, chunks):
        calls = {}

        class FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                calls.update(text=text, voice=voice, **kwargs)

            async def stream(self):
                for chunk in chunks:
                    yield chunk

        fake = types.SimpleNamespace(Communicate=FakeCommunicate)
        monkeypatch.setitem(sys.modules, "edge_tts", fake)
        return calls

    def test_generates_audio_and_word_timestamps(self, monkeypatch, tmp_path):
        calls = self._patch_edge(
            monkeypatch,
            [
                {"type": "audio", "data": b"ID3fake"},
                {"type": "WordBoundary", "offset": 1_000_000, "duration": 3_000_000, "text": "Hola"},
                {"type": "audio", "data": b"more"},
                {"type": "WordBoundary", "offset": 5_000_000, "duration": 2_500_000, "text": "mundo"},
            ],
        )
        out = tmp_path / "a" / "voz.mp3"
        result = EdgeTTS().execute(
            {"text": "Hola mundo", "language_code": "es", "speed": 1.1, "timestamps": True, "output_path": str(out)}
        )
        assert result.success, result.error
        assert out.read_bytes() == b"ID3fakemore"
        assert result.data["word_timestamps"] == [
            {"word": "Hola", "start": 0.1, "end": 0.4},
            {"word": "mundo", "start": 0.5, "end": 0.75},
        ]
        assert result.artifacts == [str(out)]
        assert result.cost_usd == 0.0
        assert calls["voice"] == "es-MX-JorgeNeural"
        assert calls["rate"] == "+10%"
        assert calls["boundary"] == "WordBoundary"

    def test_timestamps_omitted_unless_requested(self, monkeypatch, tmp_path):
        self._patch_edge(monkeypatch, [{"type": "audio", "data": b"x"}])
        result = EdgeTTS().execute({"text": "hola", "output_path": str(tmp_path / "v.mp3")})
        assert result.success, result.error
        assert "word_timestamps" not in result.data

    def test_no_audio_is_an_error(self, monkeypatch, tmp_path):
        self._patch_edge(monkeypatch, [])
        result = EdgeTTS().execute({"text": "hola", "output_path": str(tmp_path / "v.mp3")})
        assert not result.success
        assert "no audio" in result.error


# ---- Kokoro TTS ----

class TestKokoroTTS:
    def test_unavailable_without_model_files(self, monkeypatch, tmp_path):
        monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
        t = KokoroTTS()
        assert t.get_status() == ToolStatus.UNAVAILABLE
        result = t.execute({"text": "hola"})
        assert not result.success
        assert "model files missing" in result.error

    def test_available_when_model_files_exist(self, monkeypatch, tmp_path):
        monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
        (tmp_path / kokoro_tts.MODEL_FILE).write_bytes(b"x")
        (tmp_path / kokoro_tts.VOICES_FILE).write_bytes(b"x")
        assert KokoroTTS().get_status() == ToolStatus.AVAILABLE

    def test_voice_and_lang_resolution(self):
        assert KokoroTTS._resolve_voice({"language_code": "es"}) == "ef_dora"
        assert KokoroTTS._resolve_voice({"language_code": "en-US"}) == "af_heart"
        assert KokoroTTS._resolve_voice({}) == "ef_dora"
        assert KokoroTTS._resolve_voice({"voice_id": "em_alex"}) == "em_alex"
        assert KokoroTTS._resolve_lang("ef_dora", {}) == "es"
        assert KokoroTTS._resolve_lang("bf_emma", {}) == "en-gb"
        assert KokoroTTS._resolve_lang("af_heart", {"lang": "en-gb"}) == "en-gb"

    def _prepare_fake_engine(self, monkeypatch, tmp_path, voices=("ef_dora",)):
        monkeypatch.setenv("KOKORO_MODEL_DIR", str(tmp_path))
        (tmp_path / kokoro_tts.MODEL_FILE).write_bytes(b"x")
        (tmp_path / kokoro_tts.VOICES_FILE).write_bytes(b"x")
        calls = {}

        class FakeKokoro:
            def __init__(self, model_path, voices_path):
                calls["paths"] = (model_path, voices_path)

            def get_voices(self):
                return list(voices)

            def create(self, text, voice, speed, lang, sentence_pause):
                import numpy as np

                calls.update(text=text, voice=voice, speed=speed, lang=lang, pause=sentence_pause)
                return np.zeros(24000, dtype=np.float32), 24000

        monkeypatch.setitem(sys.modules, "kokoro_onnx", types.SimpleNamespace(Kokoro=FakeKokoro))
        return calls

    def test_generates_wav(self, monkeypatch, tmp_path):
        import wave

        calls = self._prepare_fake_engine(monkeypatch, tmp_path)
        out = tmp_path / "out" / "voz.wav"
        result = KokoroTTS().execute(
            {"text": "Hola mundo", "language_code": "es", "speed": 1.2, "output_path": str(out)}
        )
        assert result.success, result.error
        with wave.open(str(out), "rb") as wav:
            assert wav.getframerate() == 24000
            assert wav.getnchannels() == 1
            assert wav.getnframes() == 24000
        assert result.data["voice"] == "ef_dora"
        assert result.data["lang"] == "es"
        assert result.data["audio_seconds"] == 1.0
        assert calls["speed"] == 1.2
        assert result.cost_usd == 0.0

    def test_unknown_voice_is_an_error(self, monkeypatch, tmp_path):
        self._prepare_fake_engine(monkeypatch, tmp_path)
        result = KokoroTTS().execute(
            {"text": "hola", "voice": "xx_nope", "output_path": str(tmp_path / "v.wav")}
        )
        assert not result.success
        assert "Unknown Kokoro voice" in result.error
