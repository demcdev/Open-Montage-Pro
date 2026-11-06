"""Edge TTS provider tool — free Microsoft neural voices, no API key."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

from lib.voice_language import mismatch_error
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)

# Default voice by language prefix when the caller gives no voice.
_DEFAULT_VOICES = {
    "es": "es-MX-JorgeNeural",
    "en": "en-US-AndrewNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "pt": "pt-BR-AntonioNeural",
    "it": "it-IT-DiegoNeural",
}
_FALLBACK_VOICE = "es-MX-JorgeNeural"
_TICKS_PER_SECOND = 10_000_000  # edge-tts offsets are in 100 ns units


class EdgeTTS(BaseTool):
    name = "edge_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "edge_tts"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API
    fallback = "kokoro_tts"

    dependencies = ["python:edge_tts"]
    install_instructions = (
        "Install Edge TTS (no API key needed):\n"
        "  pip install edge-tts\n"
        "Uses Microsoft Edge's online read-aloud endpoint. It is unofficial and "
        "may change or break without notice; list voices with `edge-tts --list-voices`."
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "word_timestamps",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "word_timestamps": True,
    }
    best_for = [
        "free multilingual neural narration without API key",
        "drafts and zero-budget productions with word timestamps",
    ]
    not_good_for = [
        "offline production",
        "voice clone matching",
        "SSML control or emotional direction",
        "commercial services that need a supported API",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {
                "type": "string",
                "description": "Edge voice name, e.g. es-MX-JorgeNeural. Defaults by language_code.",
            },
            "voice_id": {
                "type": "string",
                "description": "Alias of voice (passed by tts_selector).",
            },
            "language_code": {
                "type": "string",
                "description": (
                    "Language of the script, e.g. es, en-US. Picks the default voice when no voice "
                    "is given; a voice named for another language is refused."
                ),
            },
            "allow_voice_language_mismatch": {
                "type": "boolean",
                "default": False,
                "description": "True only with a voice_language decision the user approved in decision_log.",
            },
            "rate": {
                "type": "string",
                "description": "Edge rate string such as +10% or -20%. Overrides speed.",
            },
            "speed": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 4.0,
                "description": "Speaking speed multiplier; 1.0 is normal.",
            },
            "speaking_rate": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 2.0,
                "description": "Alias of speed.",
            },
            "pitch": {
                "type": ["number", "string"],
                "description": "Hz offset as a number or an Edge string such as +5Hz.",
            },
            "volume": {
                "type": "string",
                "description": "Edge volume string such as +0% or -10%.",
                "default": "+0%",
            },
            "timestamps": {
                "type": "boolean",
                "default": False,
                "description": "Return word timestamps in data.word_timestamps.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=5, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["timeout", "connection"])
    idempotency_key_fields = ["text", "voice", "rate", "pitch", "volume"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for pronunciation and pacing"]

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            self.check_dependencies()
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

        language_error = mismatch_error(inputs, self._resolve_voice(inputs))
        if language_error:
            return ToolResult(success=False, error=language_error)

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Edge TTS generation failed: {exc}")

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
    def _resolve_rate(inputs: dict[str, Any]) -> str:
        if inputs.get("rate"):
            return str(inputs["rate"])
        speed = inputs.get("speed", inputs.get("speaking_rate"))
        if speed is None:
            return "+0%"
        percent = round((float(speed) - 1.0) * 100)
        return f"{percent:+d}%"

    @staticmethod
    def _resolve_pitch(inputs: dict[str, Any]) -> str:
        pitch = inputs.get("pitch")
        if pitch is None:
            return "+0Hz"
        if isinstance(pitch, (int, float)):
            return f"{round(pitch):+d}Hz"
        return str(pitch)

    @staticmethod
    def _run(coro):
        """Run a coroutine even when the caller already has an event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        box: dict[str, Any] = {}

        def runner() -> None:
            try:
                box["value"] = asyncio.run(coro)
            except BaseException as exc:  # re-raised in the caller's thread
                box["error"] = exc

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()
        if "error" in box:
            raise box["error"]
        return box["value"]

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import edge_tts

        text = inputs["text"]
        voice = self._resolve_voice(inputs)
        rate = self._resolve_rate(inputs)
        pitch = self._resolve_pitch(inputs)
        volume = inputs.get("volume", "+0%")
        with_timestamps = bool(inputs.get("timestamps"))

        output_path = Path(inputs.get("output_path", "tts_output.mp3"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def synthesize() -> list[dict[str, Any]]:
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
                boundary="WordBoundary",
            )
            words: list[dict[str, Any]] = []
            got_audio = False
            with open(output_path, "wb") as handle:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        handle.write(chunk["data"])
                        got_audio = True
                    elif chunk["type"] == "WordBoundary":
                        begin = chunk["offset"] / _TICKS_PER_SECOND
                        words.append(
                            {
                                "word": chunk["text"],
                                "start": round(begin, 3),
                                "end": round(begin + chunk["duration"] / _TICKS_PER_SECOND, 3),
                            }
                        )
            if not got_audio:
                raise RuntimeError("Edge TTS returned no audio (check the voice name and network)")
            return words

        words = self._run(synthesize())

        if not output_path.exists() or output_path.stat().st_size == 0:
            return ToolResult(success=False, error=f"Edge TTS output file missing: {output_path}")

        data: dict[str, Any] = {
            "provider": self.provider,
            "model": voice,
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
            "text_length": len(text),
            "output": str(output_path),
            "format": "mp3",
        }
        if with_timestamps:
            data["word_timestamps"] = words

        return ToolResult(
            success=True,
            data=data,
            artifacts=[str(output_path)],
            cost_usd=0.0,
            model=voice,
        )
