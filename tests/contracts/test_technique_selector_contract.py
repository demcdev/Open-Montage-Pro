"""Contract tests for technique selection.

Narrative pipelines choose their techniques, with a reason, before locking an
engine. The catalog must only promise what the project can run, the selector's
recipes must come from the catalog, and the schema, manifests and directors must
agree on where `technique_stack` lives and that later stages work from it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tools.tool_registry import ToolRegistry

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS = ROOT / "skills"
CATALOG = SKILLS / "creative" / "technique-catalog.md"
SELECTOR = SKILLS / "meta" / "technique-selector.md"
MOTION = ROOT / "remotion-composer" / "src" / "lib" / "motion-catalog.json"

PROPOSAL_PATH = "proposal_packet.production_plan.technique_stack"
BRIEF_PATH = "brief.metadata.technique_stack"
# manifest -> (director folder, stage that chooses, where the stack lives)
PIPELINES = {
    "animated-explainer": ("explainer", "proposal", PROPOSAL_PATH),
    "animation": ("animation", "proposal", PROPOSAL_PATH),
    "character-animation": ("character-animation", "proposal", PROPOSAL_PATH),
    "cinematic": ("cinematic", "proposal", PROPOSAL_PATH),
    "avatar-spokesperson": ("avatar-spokesperson", "idea", BRIEF_PATH),
    "documentary-montage": ("documentary-montage", "idea", BRIEF_PATH),
    "hybrid": ("hybrid", "idea", BRIEF_PATH),
}
ROW = re.compile(r"^\| `((?:src|cut|cam|mot|fin|snd|post)_[a-z0-9_]+)` \|(.*)\|$", re.MULTILINE)
REF = re.compile(r"`(tool|skill|camera|transition|fx|text|scene|overlay):([^`]+)`")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _rows() -> dict[str, list[str]]:
    rows = {}
    for technique_id, body in ROW.findall(_read(CATALOG)):
        assert technique_id not in rows, f"{technique_id} appears twice"
        rows[technique_id] = [cell.strip() for cell in body.split("|")]
    return rows


def _stack_schema() -> dict:
    schema = json.loads(_read(ROOT / "schemas" / "artifacts" / "proposal_packet.schema.json"))
    return schema["$defs"]["technique_stack"]


def _selector_example() -> dict:
    text = _read(SELECTOR)
    start = text.index("{", text.index('"technique_stack": {'))
    depth = 0
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return json.loads(text[start : i + 1])
    raise AssertionError("example block never closes")


@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.discover()
    return reg


def test_every_row_has_all_columns_and_a_valid_id():
    rows = _rows()
    assert len(rows) >= 60
    pattern = _stack_schema()["properties"]["techniques"]["items"]["properties"]["technique_id"]["pattern"]
    for technique_id, cells in rows.items():
        assert len(cells) == 5, f"{technique_id} has {len(cells)} columns"
        assert re.fullmatch(pattern, technique_id)


def test_every_reference_points_at_something_real(registry):
    motion = json.loads(_read(MOTION))
    known = {
        "camera": {entry["id"] for entry in motion["camera"]},
        "transition": {entry["id"] for entry in motion["transitions"]},
        "fx": {entry["id"] for entry in motion["fx"]},
    }
    scene_types = _read(ROOT / "remotion-composer" / "SCENE_TYPES.md")
    text_modes = _read(ROOT / "docs" / "MOTION_CATALOG.md")
    for technique_id, cells in _rows().items():
        refs = REF.findall(cells[3])
        assert refs, f"{technique_id} does not say how it runs"
        for kind, value in refs:
            where = f"{technique_id} -> {kind}:{value}"
            if kind == "tool":
                assert registry.get(value) is not None, where
            elif kind == "skill":
                assert (SKILLS / value).is_file(), where
            elif kind in known:
                assert value in known[kind], where
            elif kind == "text":
                assert f"| `{value}` |" in text_modes, where
            else:
                assert f"`{value}`" in scene_types, where


def test_no_gpu_column_is_honest(registry):
    rows = _rows()
    for technique_id, cells in rows.items():
        value = cells[4]
        gpu_tools = [
            name
            for kind, name in REF.findall(cells[3])
            if kind == "tool" and registry.get(name).get_info()["runtime"] == "local_gpu"
        ]
        if value.startswith("`→ "):
            target = value.strip("`→ ")
            assert target in rows, f"{technique_id} falls back to unknown {target}"
            assert not rows[target][4].startswith("`→"), f"{technique_id} falls back to a technique that needs a GPU"
        else:
            assert value in ("`local`", "`nube`"), f"{technique_id}: {value}"
            assert not gpu_tools, f"{technique_id} says {value} but {gpu_tools} needs a local GPU"


def test_recipes_cover_the_schema_goals_and_use_catalog_techniques():
    rows = _rows()
    goals = _stack_schema()["properties"]["goal"]["enum"]
    section = _read(SELECTOR).split("### 3.")[1].split("### 4.")[0]
    recipes = dict(re.findall(r"^\| `([a-z_]+)` \|[^|]*\|(.*)\|$", section, re.MULTILINE))
    recipes.pop("goal")  # table header
    assert set(recipes) == set(goals)
    for goal, recipe in recipes.items():
        ids = re.findall(r"`([a-z0-9_]+)`", recipe)
        unknown = set(ids) - set(rows)
        assert not unknown, f"{goal} uses techniques outside the catalog: {unknown}"
        if goal != "other":
            assert 3 <= len(ids) <= 8, f"{goal} breaks the selector's own limits"
            assert {i.split("_")[0] for i in ids} >= {"src", "cut", "snd"}, f"{goal} lacks origin, editing or sound"


def test_selector_example_matches_the_schema_and_the_catalog():
    example = _selector_example()
    Draft202012Validator(_stack_schema()).validate(example)
    used = {entry["technique_id"] for entry in example["techniques"] + example["rejected"]}
    assert used <= set(_rows())


@pytest.mark.parametrize(
    "broken",
    [
        {"goal": "explainer", "techniques": [], "decision_id": "d-1"},
        {"goal": "vlog", "techniques": [{}], "decision_id": "d-1"},
        {"goal": "explainer", "techniques": [{"technique_id": "cut_hard", "role": "hero", "purpose": "x", "execution": "y"}] * 3, "decision_id": "d-1"},
        {"goal": "explainer", "techniques": [{"technique_id": "cut_hard", "role": "accent", "execution": "y"}] * 3, "decision_id": "d-1"},
        {"goal": "explainer", "techniques": [{"technique_id": "cut_hard", "role": "accent", "purpose": "x", "execution": "y"}] * 9, "decision_id": "d-1"},
        {"goal": "explainer", "techniques": [{"technique_id": "cut_hard", "role": "accent", "purpose": "x", "execution": "y"}] * 3},
    ],
)
def test_schema_rejects_an_unjustified_stack(broken):
    assert list(Draft202012Validator(_stack_schema()).iter_errors(broken))


def test_proposal_plan_and_decision_log_accept_the_stack():
    packet = json.loads(_read(ROOT / "schemas" / "artifacts" / "proposal_packet.schema.json"))
    plan = packet["properties"]["production_plan"]["properties"]
    assert plan["technique_stack"] == {"$ref": "#/$defs/technique_stack"}
    log = json.loads(_read(ROOT / "schemas" / "artifacts" / "decision_log.schema.json"))
    categories = log["properties"]["decisions"]["items"]["properties"]["category"]["enum"]
    assert "technique_selection" in categories


@pytest.mark.parametrize("manifest", PIPELINES)
def test_manifest_requires_the_selection(manifest):
    _, stage_name, path = PIPELINES[manifest]
    data = yaml.safe_load(_read(ROOT / "pipeline_defs" / f"{manifest}.yaml"))
    assert "meta/technique-selector" in data["required_skills"]
    stage = next(s for s in data["stages"] if s["name"] == stage_name)
    assert path.split(".")[0] in stage["produces"]
    assert "decision_log" in stage["produces"]
    assert any(path in criterion and "technique_selection" in criterion for criterion in stage["success_criteria"])


@pytest.mark.parametrize("manifest", PIPELINES)
def test_directors_choose_the_stack_and_later_stages_use_it(manifest):
    folder, stage_name, path = PIPELINES[manifest]
    base = SKILLS / "pipelines" / folder
    chooser = _read(base / f"{stage_name}-director.md")
    assert "<!-- technique-selector -->" in chooser
    assert path in chooser and "skills/meta/technique-selector.md" in chooser
    for later in ("scene-director.md", "edit-director.md"):
        text = _read(base / later)
        assert "<!-- technique-stack -->" in text, f"{folder}/{later}"
        assert path in text, f"{folder}/{later} names the wrong artifact"


def test_technique_comes_before_the_runtime():
    assert "`skills/meta/technique-selector.md`" in _read(SKILLS / "meta" / "animation-runtime-selector.md")
    selector = _read(SELECTOR)
    assert selector.index("técnicas (este skill)") < selector.index("motor (animation-runtime-selector)")


def test_reviewer_and_guide_know_about_it():
    reviewer = _read(SKILLS / "meta" / "reviewer.md")
    assert "technique_stack" in reviewer and "technique_selection" in reviewer
    assert "skills/meta/technique-selector.md" in _read(ROOT / "AGENT_GUIDE.md")
