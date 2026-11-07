"""Amazon Polly text-to-speech provider tool.

Neural / Long-Form narration served by Amazon Polly through ``boto3``. The
Long-Form engine (e.g. Spanish ``Raul``, es-ES) is tuned for extended
narration and is the engine used for channel voiceovers.

Credentials follow the standard AWS chain: ``AWS_ACCESS_KEY_ID`` +
``AWS_SECRET_ACCESS_KEY`` (+ ``AWS_DEFAULT_REGION``) in the environment, or a
configured ``~/.aws`` profile.

Polly limits each request to 3000 billable characters, so longer text is split
on sentence boundaries and the audio is concatenated. Polly does not bill SSML
tags.

Docs: https://docs.aws.amazon.com/polly/latest/dg/long-form-voices.html
"""

from __future__ import annotations

import importlib.util
import io
import os
import re
import time
import wave
from pathlib import Path
from typing import Any

from lib.paths import scratch_path
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

# Max billable characters per SynthesizeSpeech request.
_CHUNK_LIMIT = 3000
# Polly PCM output is 16-bit signed little-endian mono; sample rate is configurable.
_PCM_RATE = 16000


class PollyTTS(BaseTool):
    name = "polly_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "polly"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Install boto3 and set AWS credentials for Amazon Polly:\n"
        "  pip install boto3\n"
        "  AWS_ACCESS_KEY_ID=...\n"
        "  AWS_SECRET_ACCESS_KEY=...\n"
        "  AWS_DEFAULT_REGION=us-east-1\n"
        "Create an IAM user with the AmazonPollyReadOnlyAccess policy "
        "(https://console.aws.amazon.com/iam). Long-Form voices are available "
        "in us-east-1, us-west-2 and eu-west-1."
    )
    fallback = "google_tts"
    fallback_tools = ["google_tts", "azure_tts", "elevenlabs_tts", "piper_tts"]
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "voice_selection",
        "ssml_support",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
    }
    best_for = [
        "long-form Spanish (es-ES) narration with the Raul voice",
        "extended voiceovers on AWS credentials",
    ]
    not_good_for = [
        "fully offline production (use piper_tts)",
        "voice cloning (use elevenlabs_tts)",
    ]

    DEFAULT_VOICE = "Raul"
    DEFAULT_ENGINE = "long-form"
    DEFAULT_LANGUAGE = "es-ES"

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string", "description": "Text to convert to speech"},
            "voice": {
                "type": "string",
                "description": "Polly voice id (e.g. 'Raul'). Default: Raul.",
            },
            "voice_id": {
                "type": "string",
                "description": "Alias for 'voice' so tts_selector's provider-agnostic voice_id passes through. 'voice' wins when both are set.",
            },
            "engine": {
                "type": "string",
                "enum": ["long-form", "neural", "generative", "standard"],
                "default": "long-form",
                "description": "Polly engine. Default long-form.",
            },
            "language_code": {
                "type": "string",
                "default": "es-ES",
                "description": "BCP-47 language code. Default es-ES.",
            },
            "ssml": {
                "type": "boolean",
                "default": False,
                "description": "Treat 'text' as SSML. A <speak> root is added when missing.",
            },
            "output_path": {"type": "string"},
            "output_format": {
                "type": "string",
                "enum": ["mp3", "wav"],
                "default": "mp3",
                "description": "mp3, or wav (built from Polly's 16 kHz PCM output).",
            },
        },
    }

    output_schema = {
        "type": "object",
        "properties": {
            "provider": {"type": "string"},
            "voice": {"type": "string"},
            "engine": {"type": "string"},
            "output": {"type": "string"},
            "format": {"type": "string"},
            "text_length": {"type": "integer"},
            "chunks": {"type": "integer"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        retryable_errors=["ConnectionError", "Timeout", "ThrottlingException"],
    )
    idempotency_key_fields = ["text", "voice", "engine", "language_code", "ssml", "output_format"]
    side_effects = ["writes audio file to output_path", "sends text to Amazon Polly"]
    user_visible_verification = ["Listen to generated audio for natural speech quality"]

    # Long-Form is billed at about $100 per 1M characters (first 500k chars/month
    # free for the first 12 months of an AWS account).
    COST_PER_CHAR = {
        "long-form": 100.0 / 1_000_000,
        "generative": 30.0 / 1_000_000,
        "neural": 16.0 / 1_000_000,
        "standard": 4.0 / 1_000_000,
    }

    # ---- status / estimates ----

    def get_status(self) -> ToolStatus:
        if importlib.util.find_spec("boto3") is None:
            return ToolStatus.UNAVAILABLE
        if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
            return ToolStatus.AVAILABLE
        if os.environ.get("AWS_PROFILE"):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        engine = inputs.get("engine", self.DEFAULT_ENGINE)
        rate = self.COST_PER_CHAR.get(engine, self.COST_PER_CHAR[self.DEFAULT_ENGINE])
        return round(self._billable_chars(inputs.get("text", "")) * rate, 4)

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 10.0

    # ---- helpers ----

    @staticmethod
    def _billable_chars(text: str) -> int:
        """Polly does not bill SSML tags."""
        return len(re.sub(r"<[^>]+>", "", text))

    @staticmethod
    def _split(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
        """Split on sentence boundaries so each piece stays within ``limit``."""
        text = text.strip()
        if len(text) <= limit:
            return [text]
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            while len(sentence) > limit:  # pathological: no punctuation
                cut = sentence.rfind(" ", 0, limit)
                cut = cut if cut > 0 else limit
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if current and len(current) + 1 + len(sentence) > limit:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current)
        return chunks

    def _client(self):
        import boto3

        return boto3.client(
            "polly", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )

    # ---- execution ----

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Amazon Polly is not configured. " + self.install_instructions,
            )
        start = time.time()
        try:
            result = self._synthesize(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"TTS generation failed: {exc}")
        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result

    def _synthesize(self, inputs: dict[str, Any]) -> ToolResult:
        voice = inputs.get("voice") or inputs.get("voice_id") or self.DEFAULT_VOICE
        engine = inputs.get("engine", self.DEFAULT_ENGINE)
        language = inputs.get("language_code", self.DEFAULT_LANGUAGE)
        is_ssml = bool(inputs.get("ssml", False))
        container = inputs.get("output_format", "mp3")
        wav = container == "wav"
        ext = "wav" if wav else "mp3"

        if is_ssml:
            ssml_text = inputs["text"].strip()
            if not ssml_text.startswith("<speak"):
                ssml_text = f"<speak>{ssml_text}</speak>"
            chunks = [ssml_text]
        else:
            chunks = self._split(inputs["text"])
        for chunk in chunks:
            if self._billable_chars(chunk) > _CHUNK_LIMIT:
                return ToolResult(
                    success=False,
                    error=f"Polly accepts at most {_CHUNK_LIMIT} billable characters per request; split SSML input into smaller parts.",
                )

        client = self._client()
        audio = bytearray()
        for chunk in chunks:
            response = client.synthesize_speech(
                Text=chunk,
                TextType="ssml" if is_ssml else "text",
                VoiceId=voice,
                Engine=engine,
                LanguageCode=language,
                OutputFormat="pcm" if wav else "mp3",
                **({"SampleRate": str(_PCM_RATE)} if wav else {}),
            )
            audio += response["AudioStream"].read()

        output_path = Path(inputs.get("output_path") or scratch_path(f"tts_output.{ext}"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if wav:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(_PCM_RATE)
                w.writeframes(bytes(audio))
            output_path.write_bytes(buffer.getvalue())
        else:
            output_path.write_bytes(bytes(audio))

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "voice": voice,
                "engine": engine,
                "text_length": len(inputs["text"]),
                "chunks": len(chunks),
                "output": str(output_path),
                "format": ext,
            },
            artifacts=[str(output_path)],
            model=f"polly-{engine}:{voice}",
        )
