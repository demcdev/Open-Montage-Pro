"""Find narration sentences that may have slipped out of the script's language.

Multilingual voices pick the language from the text, so a name or a short line can
come out in another language. Whisper cannot measure an accent, but such a slip
leaves traces. Each script sentence is aligned to the audio and checked for three:

- ``wrong_words``: Whisper heard different words than the script says.
- ``foreign_language``: the clip does not sound like the script's language. Clips
  under ``MIN_LANGUAGE_SECONDS`` are skipped, because native voices fail this too.
- ``low_confidence``: Whisper was unsure of what it heard.

A wrong word flags its sentence on its own, because one word can carry the whole line.
The other two traces are ordinary noise alone, so they flag at ``FLAG_SIGNALS``. A flag
means "listen to this", not "this is wrong": someone has to hear it, then regenerate it
or list it in ``accepted_sentences``. An accent that changes without touching the words
can pass unseen, which is why the approved sample still matters.
"""

from __future__ import annotations

import difflib
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

SAMPLE_RATE = 16000
FLAG_SIGNALS = 2
MIN_LANGUAGE_SECONDS = 1.0
MIN_LANGUAGE_PROBABILITY = 0.5
MIN_WORD_CONFIDENCE = 0.6
MIN_WORD_SIMILARITY = 0.7

_SENTENCE = re.compile(r"[^.!?…\n]+[.!?…]*")
_WORD = re.compile(r"[^\W_]+")


def normalize(word: str) -> str:
    """Compare words without case or accents, since Whisper varies both."""
    folded = unicodedata.normalize("NFKD", word.lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def tokens(text: str) -> list[str]:
    return [normalize(word) for word in _WORD.findall(text)]


def split_sentences(script: str) -> list[str]:
    found = (match.group().strip(" \t¿¡\"'") for match in _SENTENCE.finditer(script))
    return [sentence for sentence in found if tokens(sentence)]


def same_word(a: str, b: str) -> bool:
    if a == b or any(ch.isdigit() for ch in a + b):
        return True  # Whisper writes numbers as digits; the script spells them out.
    return difflib.SequenceMatcher(None, a, b).ratio() >= MIN_WORD_SIMILARITY


def align(script_words: list[str], heard_words: list[str]) -> list[int]:
    """Map each script word to its position in the transcript."""
    positions = [0] * (len(script_words) + 1)
    matcher = difflib.SequenceMatcher(None, script_words, heard_words, autojunk=False)
    for _, i1, i2, j1, j2 in matcher.get_opcodes():
        for i in range(i1, i2):
            positions[i] = j1 + (i - i1) * (j2 - j1) // (i2 - i1)
    positions[len(script_words)] = len(heard_words)
    return positions


def unheard_words(script_words: list[str], heard: list[dict[str, Any]]) -> list[str]:
    heard_words = [word["norm"] for word in heard]
    joined = "".join(heard_words)
    return [word for word in script_words if word not in joined and not any(same_word(word, other) for other in heard_words)]


def sentence_signals(
    script_words: list[str],
    heard: list[dict[str, Any]],
    language_probability: float | None,
) -> list[str]:
    """Return the traces of a slip in one aligned sentence."""
    signals = []
    if unheard_words(script_words, heard):
        signals.append("wrong_words")
    if language_probability is not None and language_probability < MIN_LANGUAGE_PROBABILITY:
        signals.append("foreign_language")
    if heard and sum(word["probability"] for word in heard) / len(heard) < MIN_WORD_CONFIDENCE:
        signals.append("low_confidence")
    return signals


def is_flagged(signals: list[str]) -> bool:
    return "wrong_words" in signals or len(signals) >= FLAG_SIGNALS


def analyze(script: str, words: list[dict[str, Any]], language_of_clip) -> list[dict[str, Any]]:
    """Check every script sentence against the words Whisper heard.

    ``language_of_clip(start, end)`` returns how likely that stretch of audio is to be
    in the script's language.
    """
    sentences = split_sentences(script)
    per_sentence = [tokens(sentence) for sentence in sentences]
    script_words = [word for group in per_sentence for word in group]
    heard = [{**word, "norm": normalize(word["word"].strip(" .,;:!?¿¡"))} for word in words]
    positions = align(script_words, [word["norm"] for word in heard])

    checked = []
    first_word = 0
    for index, (sentence, group) in enumerate(zip(sentences, per_sentence)):
        last_word = first_word + len(group)
        slice_end = positions[last_word]
        heard_here = heard[positions[first_word]:slice_end]
        first_word = last_word

        start = heard_here[0]["start"] if heard_here else None
        end = heard_here[-1]["end"] if heard_here else None
        long_enough = heard_here and end - start >= MIN_LANGUAGE_SECONDS
        probability = language_of_clip(start, end) if long_enough else None
        signals = sentence_signals(group, heard_here, probability)
        if not heard_here:
            signals = ["wrong_words", "foreign_language"]
        checked.append(
            {
                "index": index,
                "text": sentence,
                "heard": " ".join(word["word"].strip() for word in heard_here),
                "start": start,
                "end": end,
                "language_probability": None if probability is None else round(probability, 3),
                "signals": signals,
                "wrong_words": unheard_words(group, heard_here),
                "flagged": is_flagged(signals),
            }
        )
    return checked


class NarrationQC(BaseTool):
    name = "narration_qc"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "whisperx"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["python:faster_whisper"]
    install_instructions = "pip install faster-whisper \"av<19\"  # PyAV 19 breaks faster-whisper 1.2"
    agent_skills = ["speech-to-text"]
    usage_skills = ["meta/narration-qc"]

    capabilities = ["detect_language_slips", "compare_narration_to_script"]

    input_schema = {
        "type": "object",
        "required": ["audio_path", "script_text", "language"],
        "properties": {
            "audio_path": {"type": "string", "description": "Narration audio, before music is mixed in."},
            "script_text": {"type": "string", "description": "Exact text the voice read."},
            "language": {"type": "string", "description": "ISO 639-1 code of the script, e.g. es."},
            "model_size": {
                "type": "string",
                "enum": ["base", "small", "medium", "large-v3"],
                "default": "small",
            },
            "accepted_sentences": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Flagged sentences a person listened to and accepted, by their text.",
            },
            "report_path": {
                "type": "string",
                "description": "Where to write the JSON report. Defaults to <audio>.narration.json.",
            },
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=2048, vram_mb=0, disk_mb=500)
    idempotency_key_fields = ["audio_path", "script_text", "language", "model_size"]
    side_effects = ["writes a JSON narration report next to the audio (or report_path)"]
    user_visible_verification = ["Listen to every flagged sentence before accepting or regenerating it"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        audio_path = Path(inputs["audio_path"])
        if not audio_path.exists():
            return ToolResult(success=False, error=f"Audio not found: {audio_path}")
        start = time.time()
        try:
            sentences = self._check(inputs)
        except Exception as exc:  # noqa: BLE001 - surface any decode or model failure
            return ToolResult(success=False, error=f"Narration QC failed: {exc}")

        accepted = {normalize(text) for text in inputs.get("accepted_sentences") or []}
        flagged = []
        for sentence in sentences:
            sentence["accepted"] = sentence["flagged"] and normalize(sentence["text"]) in accepted
            if sentence["flagged"] and not sentence["accepted"]:
                flagged.append(sentence)

        report = {
            "audio": str(audio_path),
            "language": inputs["language"],
            "verdict": "review" if flagged else "pass",
            "sentences_checked": len(sentences),
            "flagged": flagged,
            "transcript": " ".join(sentence["heard"] for sentence in sentences),
            "sentences": sentences,
        }
        report_path = Path(inputs.get("report_path") or audio_path.with_suffix(".narration.json"))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return ToolResult(
            success=True,
            data={**report, "report_path": str(report_path)},
            artifacts=[str(report_path)],
            duration_seconds=round(time.time() - start, 2),
        )

    def _check(self, inputs: dict[str, Any]) -> list[dict[str, Any]]:
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio

        language = inputs["language"].split("-")[0].lower()
        model = WhisperModel(inputs.get("model_size", "small"), device="cpu", compute_type="int8")
        audio = decode_audio(str(inputs["audio_path"]), sampling_rate=SAMPLE_RATE)
        segments, _ = model.transcribe(audio, language=language, word_timestamps=True, vad_filter=True)
        words = [
            {"word": word.word, "start": word.start, "end": word.end, "probability": word.probability}
            for segment in segments
            for word in segment.words or []
        ]

        def language_of_clip(start: float, end: float) -> float:
            clip = audio[int(start * SAMPLE_RATE):int(end * SAMPLE_RATE)]
            _, _, probabilities = model.detect_language(audio=clip)
            return dict(probabilities).get(language, 0.0)

        return analyze(inputs["script_text"], words, language_of_clip)
