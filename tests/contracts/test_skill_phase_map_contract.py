"""Contract tests for the skill phase map (skills/MAPA_POR_FASE.md).

The map tells the agent and the user which Layer 2 skill is read at each phase of
a production. It must cover every skill in core/, creative/ and meta/, point only
at files that exist, mark as required only what the manifests really require, and
be discoverable from the skill index and the guide.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS = ROOT / "skills"
MAP = SKILLS / "MAPA_POR_FASE.md"
SKILL_REF = re.compile(r"`((?:core|creative|meta)/[A-Za-z0-9_/-]+\.md)`")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _layer2_skills() -> set[str]:
    found = set()
    for folder in ("core", "creative", "meta"):
        for path in (SKILLS / folder).rglob("*.md"):
            found.add(path.relative_to(SKILLS).as_posix())
    return found


def _required_everywhere() -> set[str]:
    sets = []
    for path in (ROOT / "pipeline_defs").glob("*.yaml"):
        required = yaml.safe_load(_read(path)).get("required_skills") or []
        if required:
            sets.append({f"{name}.md" for name in required})
    return set.intersection(*sets)


def test_map_covers_every_layer2_skill():
    mapped = set(SKILL_REF.findall(_read(MAP)))
    missing = _layer2_skills() - mapped
    assert not missing, f"MAPA_POR_FASE.md does not list: {sorted(missing)}"


def test_map_points_only_at_existing_skills():
    for ref in SKILL_REF.findall(_read(MAP)):
        assert (SKILLS / ref).is_file(), f"MAPA_POR_FASE.md points at a missing skill: {ref}"


def test_required_everywhere_marks_match_the_manifests():
    marked = set()
    for line in _read(MAP).splitlines():
        if "✅ todos" in line:
            marked.update(SKILL_REF.findall(line))
    assert marked == _required_everywhere(), "the '✅ todos' rows do not match the skills every manifest requires"


def test_map_is_discoverable():
    assert "MAPA_POR_FASE.md" in _read(SKILLS / "INDEX.md"), "INDEX.md does not link the phase map"
    assert "skills/MAPA_POR_FASE.md" in _read(ROOT / "AGENT_GUIDE.md"), "AGENT_GUIDE.md does not mention the phase map"
