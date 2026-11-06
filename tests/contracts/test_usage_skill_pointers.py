"""Layer 2 skills must have a route to the agent.

`usage_skills` points a tool at its manuals under skills/, so they are read when
the tool is used and cost nothing otherwise. Every pointer must resolve, every
manual must be claimed by a tool, and the phase map must not hide a skill that
nothing loads.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.graphics.image_selector import ImageSelector
from tools.tool_registry import registry
from tools.video.video_selector import VideoSelector

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
MAP = SKILLS / "MAPA_POR_FASE.md"
PIPELINE_DIRECTORS = SKILLS / "pipelines"

registry.discover()
POINTERS = sorted(
    (name, skill) for name, tool in registry._tools.items() for skill in tool.get_info()["usage_skills"]
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _map_rows(mark: str) -> list[str]:
    return [line for line in _read(MAP).splitlines() if line.startswith("|") and mark in line]


def test_tools_declare_usage_skills():
    assert len(POINTERS) >= 40


@pytest.mark.parametrize(("tool", "skill"), POINTERS, ids=str)
def test_usage_skill_pointer_resolves(tool, skill):
    assert not skill.endswith(".md"), f"{tool}: write {skill} without .md"
    assert (SKILLS / f"{skill}.md").is_file(), f"{tool} points at a missing manual: {skill}"


def test_every_prompting_and_usage_manual_is_claimed_by_a_tool():
    claimed = {skill for _, skill in POINTERS}
    manuals = {p.relative_to(SKILLS).with_suffix("").as_posix() for p in (SKILLS / "creative" / "prompting").glob("*.md")}
    manuals |= {p.relative_to(SKILLS).with_suffix("").as_posix() for p in (SKILLS / "creative").glob("*-usage.md")}
    assert not manuals - claimed


def test_base_tool_defaults_to_no_usage_skills():
    bare = [tool for tool in registry._tools.values() if not tool.usage_skills]
    assert bare and all(tool.get_info()["usage_skills"] == [] for tool in bare)


@pytest.mark.parametrize(
    ("selector", "provider"),
    [(ImageSelector, "flux_image"), (VideoSelector, "veo_video")],
)
def test_selectors_pass_the_chosen_tools_manuals_on(selector, provider):
    tool = registry.get(provider)
    payload = selector._tool_context_payload(tool)
    assert payload["required_usage_skills"] == tool.usage_skills


def test_map_hides_no_unexplained_skill():
    for row in _map_rows("⚪"):
        if row.startswith("| ⚪ |"):  # the legend
            continue
        assert re.search(r"⚪ \(.+\)", row), f"skill nobody loads, with no reason given: {row}"


def test_map_tool_marks_match_the_tools():
    claimed = {skill for _, skill in POINTERS}
    rows = _map_rows("🔧")
    assert len(rows) >= 20
    for row in rows:
        if row.startswith("| 🔧 |"):  # the legend
            continue
        for ref in re.findall(r"`((?:core|creative|meta)/[A-Za-z0-9_/-]+)\.md`", row):
            assert ref in claimed, f"the map says a tool claims {ref}, but none does"
        for name in re.findall(r"`([a-z0-9]+(?:_[a-z0-9]+)+)`", row):
            assert registry.get(name) is not None, f"the map names an unknown tool: {name}"


@pytest.mark.parametrize(
    ("director", "skill"),
    [
        ("explainer/script-director.md", "creative/storytelling"),
        ("explainer/asset-director.md", "creative/broll-planning"),
        ("documentary-montage/asset-director.md", "creative/broll-planning"),
        ("explainer/scene-director.md", "creative/data-visualization"),
        ("cinematic/compose-director.md", "creative/video-stitching"),
        ("cinematic/compose-director.md", "core/color-grading"),
        ("talking-head/asset-director.md", "core/subtitle-sync"),
        ("talking-head/compose-director.md", "creative/enhancement-strategy"),
        ("explainer/edit-director.md", "creative/sound-design"),
        ("localization-dub/edit-director.md", "creative/sound-design"),
    ],
)
def test_directors_cite_their_craft_skills(director, skill):
    assert f"`skills/{skill}.md`" in _read(PIPELINE_DIRECTORS / director)


def test_sound_skills_state_their_scope():
    design = _read(SKILLS / "creative" / "sound-design.md")
    assert "`skills/creative/audio-post-cinema.md`" in design
    assert "`skills/core/loudness-mastering.md`" in design
    assert "sound-design.md" in _read(SKILLS / "creative" / "audio-post-cinema.md")


def test_guide_tells_the_agent_to_read_usage_skills():
    guide = _read(ROOT / "AGENT_GUIDE.md")
    assert "`usage_skills`" in guide
    assert "skills/meta/capability-extension.md" in guide
