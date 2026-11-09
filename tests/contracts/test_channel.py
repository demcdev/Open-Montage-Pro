"""The channel file, its playbook and the Remotion kit agree, and drift gets flagged."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lib.channel import CHANNEL_PATH, channel_brief, load_channel, voice_warning
from styles.playbook_loader import load_playbook, validate_accessibility, validate_playbook

ROOT = Path(__file__).resolve().parent.parent.parent
KIT = ROOT / "remotion-composer" / "src" / "channel"


def test_the_channel_playbook_is_valid_and_accessible():
    channel = load_channel()
    playbook = load_playbook(channel["playbook"])
    validate_playbook(playbook)
    assert validate_accessibility(playbook)["pass"]


def test_the_remotion_tokens_match_the_playbook():
    tokens = (KIT / "tokens.ts").read_text(encoding="utf-8")
    palette = load_playbook(load_channel()["playbook"])["visual_language"]["color_palette"]
    for name, color in {"night": palette["background"], "cyan": palette["primary"][0], "magenta": palette["accent"][0], "gold": palette["accent"][1], "text": palette["text"]}.items():
        assert re.search(rf'\b{name}: "{color}"', tokens, re.IGNORECASE), name


def test_the_kit_exports_what_the_channel_names():
    index = (KIT / "index.ts").read_text(encoding="utf-8")
    channel = load_channel()
    for component in (channel["character"]["component"], channel["close"]["component"]):
        assert re.search(rf"\b{component}\b", index), component


def test_reviewers_get_what_a_viewer_sees_and_hears():
    brief = channel_brief(load_channel())
    assert {"playbook", "voice", "character", "on_screen"} <= set(brief)


def test_a_missing_channel_file_is_empty(tmp_path):
    assert load_channel(tmp_path / "none.yaml") == {}


def test_the_voice_warning_names_the_drift():
    channel = {"voice": {"voice": "es-MX-JorgeNeural"}}
    assert voice_warning(channel, [{"category": "voice_selection", "selected": "es-MX-JorgeNeural"}]) is None
    assert "not the channel voice" in voice_warning(channel, [{"category": "voice_selection", "selected": "es-ES-AlvaroNeural"}])
    assert "No voice_selection" in voice_warning(channel, [])
    assert voice_warning({}, []) is None
