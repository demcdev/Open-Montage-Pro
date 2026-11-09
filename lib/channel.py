"""The channel's identity (``channel/channel.yaml``): defaults every narrated video shares.

Stages read it for the voice, the playbook and the Remotion kit; reviewers get the part a
viewer can see or hear, so a video that drifts from the channel gets flagged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

CHANNEL_PATH = Path(__file__).resolve().parents[1] / "channel" / "channel.yaml"
REVIEW_KEYS = ("playbook", "voice", "character", "on_screen", "format", "close", "music")


def load_channel(path: Optional[Path] = None) -> dict[str, Any]:
    """Return the channel file, or {} when there is none."""
    try:
        data = yaml.safe_load((path or CHANNEL_PATH).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def channel_brief(channel: dict[str, Any]) -> dict[str, Any]:
    """What a reviewer checks the video against."""
    return {key: channel[key] for key in REVIEW_KEYS if key in channel}


def voice_warning(channel: dict[str, Any], decisions: list[dict[str, Any]]) -> Optional[str]:
    """Say when the recorded voice is not the channel's, or when no voice was recorded."""
    voice = (channel.get("voice") or {}).get("voice")
    if not voice:
        return None
    chosen = [str(d.get("selected") or "") for d in decisions if d.get("category") == "voice_selection"]
    if not chosen:
        return f"No voice_selection decision; the channel voice is {voice}."
    if voice not in chosen[-1]:
        return f"Voice {chosen[-1]!r} is not the channel voice {voice}."
    return None
