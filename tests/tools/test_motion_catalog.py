"""Consistency tests for the Remotion motion/camera/fx catalog.

The JSON catalog is the source of truth; these tests make sure every id it
advertises is actually implemented by the TypeScript engine, and that the
edit_decisions schema can carry the new fields.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
LIB = ROOT / "remotion-composer" / "src" / "lib"
CATALOG = json.loads((LIB / "motion-catalog.json").read_text(encoding="utf-8"))
MOTION_TS = (LIB / "motion.ts").read_text(encoding="utf-8")
STAGE_TS = (LIB / "stage.tsx").read_text(encoding="utf-8")
TRANS_TS = (LIB / "transitions.tsx").read_text(encoding="utf-8")
CINE_TS = (ROOT / "remotion-composer" / "src" / "components" / "Cinematic.tsx").read_text(encoding="utf-8")

VEC_KEYS = {"s", "x", "y", "r", "b"}
MOD_KEYS = {"shake", "orbit", "float", "pulse", "wiggle"}


def test_camera_ids_and_aliases_are_unique():
    seen: dict[str, str] = {}
    for m in CATALOG["camera"]:
        for name in [m["id"], *m.get("aliases", [])]:
            assert name not in seen, f"{name!r} used by {seen[name]!r} and {m['id']!r}"
            seen[name] = m["id"]
    assert len(CATALOG["camera"]) >= 80


def test_camera_definitions_are_well_formed():
    eases = set(CATALOG["ease"])
    for m in CATALOG["camera"]:
        assert m["ease"] in eases, f"{m['id']}: unknown ease {m['ease']}"
        assert set(m["from"]) <= VEC_KEYS and set(m["to"]) <= VEC_KEYS, m["id"]
        assert set(m.get("mods", {})) <= MOD_KEYS, m["id"]
        assert m["ai_prompt"].count("Movement:") == 1 and "Speed:" in m["ai_prompt"] and "Framing:" in m["ai_prompt"] and "End:" in m["ai_prompt"], m["id"]
        assert m["summary"]


def test_every_ease_is_implemented():
    for name in CATALOG["ease"]:
        assert re.search(rf"^\s+{name}:", MOTION_TS, re.M), f"ease {name} missing in motion.ts"


def test_every_transition_is_implemented():
    for t in CATALOG["transitions"]:
        assert re.search(rf"^\s+{t['id']}:", TRANS_TS, re.M), f"transition {t['id']} missing in transitions.tsx"


def test_every_fx_is_implemented():
    for f in CATALOG["fx"]:
        fid = f["id"]
        implemented = (
            f'case "{fid}"' in STAGE_TS
            or re.search(rf"^\s+{fid}:", STAGE_TS, re.M)
            or f'"{fid}"' in STAGE_TS
        )
        assert implemented, f"fx {fid} not referenced in stage.tsx"


def test_text_modes_are_implemented():
    modes = re.findall(r'"(\w+)"', re.search(r"export const TEXT_MODES: TextMode\[\] = \[(.*?)\];", CINE_TS, re.S).group(1))
    assert len(modes) == 12
    for mode in modes:
        assert f'case "{mode}"' in CINE_TS or f'"{mode}"' in CINE_TS


def test_edit_decisions_schema_accepts_camera_and_fx():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "artifacts" / "edit_decisions.schema.json").read_text(encoding="utf-8"))
    doc = {
        "version": "1.0",
        "render_runtime": "remotion",
        "fx": ["film_grain", {"type": "vignette", "strength": 0.5}],
        "autoCamera": True,
        "defaultTransition": "dissolve",
        "cuts": [
            {
                "id": "c1", "source": "a.jpg", "in_seconds": 0, "out_seconds": 3, "type": "stat_card", "stat": "1,3 s",
                "camera": {"move": "dolly_in", "origin": {"x": 60, "y": 50}}, "fx": ["halation"], "transition_out": "whip_pan_right",
            },
            {"id": "c2", "source": "b.jpg", "in_seconds": 3, "out_seconds": 6, "camera": "handheld"},
        ],
    }
    jsonschema.validate(doc, schema)


def test_docs_are_in_sync_with_catalog():
    docs = (ROOT / "docs" / "MOTION_CATALOG.md").read_text(encoding="utf-8")
    for m in CATALOG["camera"]:
        assert f"`{m['id']}`" in docs, f"docs out of date: run scripts/generate_motion_docs.py ({m['id']})"
