"""Contract tests for the YouTube Policy Gate.

The gate is an agent-facing contract: it must be discoverable from the guide and
the skill index, wired into every pipeline manifest and stage director, covered
by the reviewer, and its records must fit the canonical artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
SKILL = ROOT / "skills" / "meta" / "youtube-policy-gate.md"
MARK = "<!-- youtube-policy-gate -->"
SKILL_REF = "skills/meta/youtube-policy-gate.md"

# Pipelines that produce publishable videos. framework-smoke is a test pipeline.
MANIFESTS = sorted(
    p for p in (ROOT / "pipeline_defs").glob("*.yaml") if p.stem != "framework-smoke"
)
STAGE_FILES = (
    "idea-director.md",
    "proposal-director.md",
    "script-director.md",
    "asset-director.md",
    "publish-director.md",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_policy_gate_skill_and_reference_exist():
    assert SKILL.is_file(), "Missing YouTube Policy Gate meta skill"
    body = SKILL.read_text(encoding="utf-8")
    for needle in (
        "Proposal Policy Review",
        "Publish Checklist",
        "Channel Standards",
        "edit_decisions.subtitles.enabled",
        "youtube_policy_review",
        "youtube_policy_checklist",
    ):
        assert needle in body, f"Skill is missing: {needle}"
    assert (ROOT / "docs" / "youtube-policy-reference.md").is_file()


def test_policy_gate_is_discoverable_to_new_agents():
    index = (ROOT / "skills" / "INDEX.md").read_text(encoding="utf-8")
    assert "meta/youtube-policy-gate.md" in index

    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    assert "youtube-policy-gate.md" in guide
    assert "Do not burn subtitles" in guide

    reviewer = (ROOT / "skills" / "meta" / "reviewer.md").read_text(encoding="utf-8")
    assert "## YouTube Policy Review" in reviewer


def test_every_manifest_requires_the_policy_gate():
    for manifest_path in MANIFESTS:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert "meta/youtube-policy-gate" in manifest["required_skills"], manifest_path.name
    assert SKILL.is_file()


def test_stage_directors_carry_the_policy_gate():
    seen = 0
    for stage_file in STAGE_FILES:
        for director in (ROOT / "skills" / "pipelines").glob(f"*/{stage_file}"):
            text = director.read_text(encoding="utf-8")
            assert MARK in text, f"{director.relative_to(ROOT)} lacks the policy gate"
            assert SKILL_REF in text, f"{director.relative_to(ROOT)} does not reference the skill"
            seen += 1
    assert seen >= 40


def test_every_pipeline_has_a_first_stage_and_publish_gate():
    for manifest_path in MANIFESTS:
        pipeline = manifest_path.stem
        pipeline_dir = ROOT / "skills" / "pipelines"
        # animated-explainer manifest uses the "explainer" skill directory.
        dirs = [pipeline_dir / pipeline, pipeline_dir / pipeline.replace("animated-", "")]
        directory = next((d for d in dirs if d.is_dir()), None)
        assert directory is not None, f"No skill directory for {pipeline}"
        first = [directory / "idea-director.md", directory / "proposal-director.md"]
        assert any(f.is_file() and MARK in f.read_text(encoding="utf-8") for f in first), pipeline
        publish = directory / "publish-director.md"
        if publish.is_file():
            assert MARK in publish.read_text(encoding="utf-8"), pipeline


def test_no_burned_subtitles_standard_overrides_conflicting_directors():
    marker = "<!-- channel-standard-no-burned-subtitles -->"
    seen = 0
    for name in ("edit-director.md", "compose-director.md"):
        for director in (ROOT / "skills" / "pipelines").glob(f"*/{name}"):
            assert marker in director.read_text(encoding="utf-8"), director.relative_to(ROOT)
            seen += 1
    assert seen >= 20

    for manifest_path in MANIFESTS:
        text = manifest_path.read_text(encoding="utf-8")
        assert "Subtitles enabled" not in text, manifest_path.name
        assert "Subtitles are synced with speech" not in text, manifest_path.name


def test_policy_records_fit_the_canonical_artifacts():
    review = {
        "reviewed_at": "2026-10-19",
        "reference_doc_date": "2026-10-11",
        "made_for_kids": {"decision": "no", "reason": "Targets a general audience."},
        "ai_disclosure": {"decision": "not_required", "reason": "Non-realistic animation."},
        "music": {"source": "youtube_audio_library", "license_evidence": "assets/music/LICENSES.md"},
        "status": "pass",
    }
    proposal_schema = _load_json(ROOT / "schemas" / "artifacts" / "proposal_packet.schema.json")
    proposal = {
        "version": "1.0",
        "concept_options": [
            {
                "id": f"c{i}",
                "title": f"Concept {i}",
                "hook": "A precise hook under twenty words.",
                "narrative_structure": "story",
                "visual_approach": "Character animation with local rigs.",
                "target_duration_seconds": 480,
                "why_this_works": "It ties the audience problem to a visible payoff.",
            }
            for i in range(1, 4)
        ],
        "selected_concept": {"concept_id": "c1", "rationale": "Best fit for the brief."},
        "production_plan": {
            "pipeline": "character-animation",
            "stages": [{"stage": "proposal", "tools": [], "approach": "Plan the production."}],
            "render_runtime": "remotion",
        },
        "cost_estimate": {"total_estimated_usd": 0, "line_items": [], "budget_verdict": "no_budget_set"},
        "approval": {"status": "pending"},
        "metadata": {"youtube_policy_review": review},
    }
    jsonschema.validate(instance=proposal, schema=proposal_schema)

    publish_schema = _load_json(ROOT / "schemas" / "artifacts" / "publish_log.schema.json")
    assert "metadata" in publish_schema["properties"]
    script_schema = _load_json(ROOT / "schemas" / "artifacts" / "script.schema.json")
    assert "metadata" in script_schema["properties"]
    edit_schema = _load_json(ROOT / "schemas" / "artifacts" / "edit_decisions.schema.json")
    assert "enabled" in edit_schema["properties"]["subtitles"]["properties"]
