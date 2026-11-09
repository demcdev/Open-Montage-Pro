"""Local sound effects: a reusable catalog instead of generating the same whoosh twice.

``sound_library/catalog.json`` lists each effect with its category, tags, source and
license, so a project can cite where a sound came from. This tool only reads it.

A project's ``artifacts/sound_plan.json`` says what sounds when, by narration word or by
second. ``operation: resolve`` turns it into tracks for ``audio_mixer``, so a new voice
only needs resolving again::

    {"cues": [{"effect": "error", "word": "reprobaron"},
              {"effect": "whoosh_suave", "seconds": 15.4, "volume": 0.4}],
     "beds": [{"effect": "arrecife", "from": 0, "to": 16, "volume": 0.15}]}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
SFX_VOLUME = 0.5
BED_VOLUME = 0.15


class SoundLibrary(BaseTool):
    name = "sound_library"
    version = "0.1.0"
    tier = ToolTier.SOURCE
    capability = "sound_library"
    provider = "local"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = []
    install_instructions = (
        "Create sound_library/catalog.json with an 'effects' list and keep the audio files "
        "next to it. Override the location with the SOUND_LIBRARY_DIR environment variable."
    )

    usage_skills = ["creative/sound-design"]
    capabilities = ["list_sound_effects"]
    supports = {"local_offline": True, "free": True}
    best_for = ["transitions, impacts and ambience reused across videos"]
    not_good_for = ["a sound no entry describes (use music_gen with sound_effect: true)"]

    input_schema = {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["list", "resolve"], "default": "list"},
            "sound_plan_path": {"type": "string", "description": "resolve: path to sound_plan.json."},
            "words_path": {"type": "string", "description": "resolve: narration word timestamps, for cues by word."},
            "category": {"type": "string", "description": "Only this category, such as whoosh, impact, pop, ui or ambience."},
            "query": {"type": "string", "description": "Only effects with this word in their name or tags."},
            "library_dir": {"type": "string", "description": "Defaults to SOUND_LIBRARY_DIR, then <repo>/sound_library."},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=0, network_required=False)
    side_effects = []
    user_visible_verification = ["Listen to an effect in the mix before keeping it"]

    @staticmethod
    def _library_dir(inputs: Optional[dict[str, Any]] = None) -> Path:
        chosen = (inputs or {}).get("library_dir") or os.environ.get("SOUND_LIBRARY_DIR")
        return Path(chosen).expanduser() if chosen else _PROJECT_ROOT / "sound_library"

    def _catalog(self, library_dir: Path) -> list[dict[str, Any]]:
        try:
            catalog = json.loads((library_dir / "catalog.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [effect for effect in catalog.get("effects") or [] if (library_dir / effect["file"]).is_file()]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._catalog(self._library_dir()) else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def _resolve(self, inputs: dict[str, Any], library_dir: Path) -> ToolResult:
        plan = json.loads(Path(inputs["sound_plan_path"]).read_text(encoding="utf-8"))
        words: list[dict[str, Any]] = []
        if inputs.get("words_path"):
            words = json.loads(Path(inputs["words_path"]).read_text(encoding="utf-8"))
        catalog = self._catalog(library_dir)
        known = {effect["name"]: library_dir / effect["file"] for effect in catalog}
        lengths = {effect["name"]: float(effect.get("duration_seconds") or 10) for effect in catalog}
        tracks = []
        for cue in plan.get("cues") or []:
            if cue["effect"] not in known:
                return ToolResult(success=False, error=f"Unknown effect {cue['effect']!r}.")
            start = cue.get("seconds")
            if start is None:
                hits = [word for word in words if word["word"].strip(" .,;:!?¿¡").lower() == cue["word"].lower()]
                index = cue.get("occurrence", 1) - 1
                if index >= len(hits):
                    return ToolResult(success=False, error=f"Word {cue['word']!r} is not in the narration.")
                start = hits[index]["start"]
            tracks.append({"path": str(known[cue["effect"]]), "role": "sfx", "volume": cue.get("volume", SFX_VOLUME), "start_seconds": max(0.0, start + cue.get("offset", 0.0))})
        for bed in plan.get("beds") or []:
            if bed["effect"] not in known:
                return ToolResult(success=False, error=f"Unknown effect {bed['effect']!r}.")
            # A bed repeats its clip until it reaches "to"; the fades hide each seam.
            start = float(bed.get("from", 0.0))
            while start < float(bed.get("to", start + 1)):
                tracks.append({"path": str(known[bed["effect"]]), "role": "sfx", "volume": bed.get("volume", BED_VOLUME), "start_seconds": start, "fade_in_seconds": 0.5, "fade_out_seconds": 0.5})
                start += lengths[bed["effect"]] - 0.5
        return ToolResult(success=True, data={"tracks": tracks, "count": len(tracks)})

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        library_dir = self._library_dir(inputs)
        if inputs.get("operation") == "resolve":
            return self._resolve(inputs, library_dir)
        effects = self._catalog(library_dir)
        if inputs.get("category"):
            effects = [effect for effect in effects if effect.get("category") == inputs["category"]]
        if inputs.get("query"):
            word = inputs["query"].lower()
            effects = [effect for effect in effects if word in f"{effect.get('name', '')} {' '.join(effect.get('tags') or [])}".lower()]
        found = [{**effect, "path": str(library_dir / effect["file"])} for effect in effects]
        return ToolResult(success=True, data={"library_dir": str(library_dir), "count": len(found), "effects": found})
