"""Catch narration voices whose own language differs from the script's.

Microsoft and Google voice names start with their locale (fr-FR-RemyMultilingualNeural,
es-US-Chirp3-HD-Puck). A multilingual voice reading another language detects it from
the text alone, which is where a foreign accent can surface mid-narration, so the
mismatch has to be an approved choice instead of a default.
"""

from __future__ import annotations

import re
from typing import Any

_LOCALE_PREFIX = re.compile(r"^([a-z]{2,3})-[A-Z]{2}-")


def voice_language(voice: str | None) -> str | None:
    """Return the language in a voice name, or None when the name does not state one."""
    match = _LOCALE_PREFIX.match(str(voice or ""))
    return match.group(1) if match else None


def mismatch_error(inputs: dict[str, Any], voice: str | None = None) -> str | None:
    """Return why this narration must not run, or None when it may.

    Nothing can be compared without a language_code or a voice that names its
    language, so those cases pass; the approved TTS sample covers them.
    """
    voice = voice or inputs.get("voice") or inputs.get("voice_id")
    spoken = str(inputs.get("language_code") or "").split("-")[0].lower()
    native = voice_language(voice)
    if not spoken or not native or native == spoken:
        return None
    if inputs.get("allow_voice_language_mismatch"):
        return None
    return (
        f"Voice {voice} is {native} but the script is {spoken}, so its accent may change "
        f"mid-narration. Use a native {spoken} voice, or log a voice_language decision the "
        "user approved and pass allow_voice_language_mismatch=true."
    )
