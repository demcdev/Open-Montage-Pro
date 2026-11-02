"""Kokoro local text-to-speech provider tool (kokoro-onnx, CPU, offline)."""

from __future__ import annotations

import os
import time
import wave
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    DependencyError,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
_RELEASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

# Voice-name prefix -> espeak language code used by kokoro-onnx.
_LANG_BY_PREFIX = {
    "a": "en-us",
    "b": "en-gb",
    "e": "es",
    "f": "fr-fr",
    "h": "hi",
    "i": "it",
    "j": "ja",
    "p": "pt-br",
    "z": "cmn",
}
# Default voice by language prefix when the caller gives no voice.
_DEFAULT_VOICES = {
    "es": "ef_dora",
    "en": "af_heart",
    "fr": "ff_siwis",
    "it": "if_sara",
    "pt": "pf_dora",
    "hi": "hf_alpha",
    "ja": "jf_alpha",
    "zh": "zf_xiaobei",
}
_FALLBACK_VOICE = "ef_dora"


def model_dir() -> Path:
    """Directory holding the Kokoro model files (KOKORO_MODEL_DIR overrides)."""
    override = os.environ.get("KOKORO_MODEL_DIR")
    return Path(override).expanduser() if override else Path.home() / ".cache" / "kokoro"


class KokoroTTS(BaseTool):
    name = "kokoro_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "kokoro"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    fallback = "piper_tts"

    dependencies = ["python:kokoro_onnx", "python:onnxruntime"]
    install_instructions = (
        "Install Kokoro (CPU, offline, Apache 2.0):\n"
        "  pip install kokoro-onnx\n"
        f"Then download the model files (~325 MB + ~28 MB) into {model_dir()}\n"
        "(or set KOKORO_MODEL_DIR):\n"
        f"  {_RELEASE_URL}/{MODEL_FILE}\n"
        f"  {_RELEASE_URL}/{VOICES_FILE}"
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": True,
        "native_audio": True,
        "word_timestamps": False,
    }
    best_for = [
        "free offline neural narration on CPU",
        "multilingual narration without API key or GPU",
        "privacy-sensitive local-only workflows",
    ]
    not_good_for = [
        "voice clone matching",
        "emotional or expressive direction",
        "word timestamps (chain transcriber afterwards)",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {
                "type": "string",
                "description": "Kokoro voice, e.g. ef_dora / em_alex (es), af_heart (en). Defaults by language_code.",
            },
            "voice_id": {
                "type": "string",
                "description": "Alias of voice (passed by tts_selector).",
            },
            "language_code": {
                "type": "string",
                "description": "Picks the default voice when no voice is given, e.g. es, en-US.",
            },
            "lang": {
                "type": "string",
                "description": "Override the espeak language code (otherwise derived from the voice prefix).",
            },
            "speed": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 2.0,
                "default": 1.0,
            },
            "speaking_rate": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 2.0,
                "description": "Alias of speed.",
            },
            "sentence_pause": {
                "type": "number",
                "default": 0.25,
                "description": "Seconds of silence between sentences.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=1024, vram_mb=0, disk_mb=360, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["text", "voice", "speed", "sentence_pause"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for pronunciation and pacing"]

    def check_dependencies(self) -> None:
        super().check_dependencies()
        missing = [
            name for name in (MODEL_FILE, VOICES_FILE) if not (model_dir() / name).is_file()
        ]
        if missing:
            raise DependencyError(
                f"Kokoro model files missing in {model_dir()}: {', '.join(missing)}. "
                + self.install_instructions
            )

    def get_status(self) -> ToolStatus:
        try:
            self.check_dependencies()
            return ToolStatus.AVAILABLE
        except DependencyError:
            return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            self.check_dependencies()
        except DependencyError as exc:
            return ToolResult(success=False, error=str(exc))

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Kokoro generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    @staticmethod
    def _resolve_voice(inputs: dict[str, Any]) -> str:
        voice = inputs.get("voice") or inputs.get("voice_id")
        if voice:
            return str(voice)
        lang = str(inputs.get("language_code") or "").split("-")[0].lower()
        return _DEFAULT_VOICES.get(lang, _FALLBACK_VOICE)

    @staticmethod
    def _resolve_lang(voice: str, inputs: dict[str, Any]) -> str:
        if inputs.get("lang"):
            return str(inputs["lang"])
        return _LANG_BY_PREFIX.get(voice[:1], "en-us")

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import numpy as np
        from kokoro_onnx import Kokoro

        text = inputs["text"]
        voice = self._resolve_voice(inputs)
        lang = self._resolve_lang(voice, inputs)
        speed = float(inputs.get("speed", inputs.get("speaking_rate", 1.0)))
        sentence_pause = float(inputs.get("sentence_pause", 0.25))

        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine = Kokoro(str(model_dir() / MODEL_FILE), str(model_dir() / VOICES_FILE))
        if voice not in engine.get_voices():
            return ToolResult(
                success=False,
                error=f"Unknown Kokoro voice {voice!r}. Available: {', '.join(sorted(engine.get_voices()))}",
            )

        samples, sample_rate = engine.create(
            text, voice=voice, speed=speed, lang=lang, sentence_pause=sentence_pause
        )
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm.tobytes())

        if not output_path.exists() or output_path.stat().st_size == 0:
            return ToolResult(success=False, error=f"Kokoro output file missing: {output_path}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "kokoro-v1.0",
                "voice": voice,
                "lang": lang,
                "speed": speed,
                "text_length": len(text),
                "audio_seconds": round(len(pcm) / sample_rate, 2),
                "output": str(output_path),
                "format": "wav",
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            model="kokoro-v1.0",
        )
