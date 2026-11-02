"""Contract tests for the mandatory creative brief (skills/meta/creative-intake.md).

Phase 1 of a narrative production must leave a `brief_creativo` (logline, stakes,
conflict, transformation, narrator) approved at the stage's own gate, before any
script is written. The skill, the directors of that stage, the manifests and the
script-writing core must agree on where it lives.
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
INTAKE = ROOT / "skills" / "meta" / "creative-intake.md"
MARK = "<!-- brief-creativo -->"

# pipeline -> (phase-1 director that carries the block, artifact that holds the brief)
PHASE1 = {
    "explainer": ("proposal-director.md", "proposal_packet"),
    "animation": ("proposal-director.md", "proposal_packet"),
    "character-animation": ("proposal-director.md", "proposal_packet"),
    "cinematic": ("proposal-director.md", "proposal_packet"),
    "avatar-spokesperson": ("idea-director.md", "brief"),
    "documentary-montage": ("idea-director.md", "brief"),
    "hybrid": ("idea-director.md", "brief"),
}
MANIFESTS = (
    "animated-explainer",
    "animation",
    "character-animation",
    "cinematic",
    "avatar-spokesperson",
    "documentary-montage",
    "hybrid",
)
FIELDS = (
    "logline",
    "tipo",
    "audiencia",
    "objetivo_emocional",
    "en_juego",
    "conflicto",
    "transformacion",
    "tono",
    "plataforma_formato",
    "duracion_objetivo_s",
    "narrador",
    "referencias",
    "restricciones",
    "origen",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_intake_defines_every_brief_field_and_where_it_lives():
    text = _read(INTAKE)
    for field in FIELDS:
        assert f"`{field}`" in text, f"creative-intake does not define `{field}`"
    assert "metadata.brief_creativo" in text
    for artifact in ("proposal_packet", "brief"):
        assert f"{artifact}.metadata.brief_creativo" in text, f"intake does not say where it lives in {artifact}"


def test_intake_example_is_valid_json_with_every_field():
    import json

    text = _read(INTAKE)
    start = text.index('"brief_creativo": {')
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            example = json.loads(text[brace : i + 1])
            break
    else:
        raise AssertionError("example block never closes")
    assert set(example) == set(FIELDS), f"example fields differ from the contract: {set(example) ^ set(FIELDS)}"


def test_phase1_directors_require_the_brief():
    for pipeline, (filename, artifact) in PHASE1.items():
        text = _read(ROOT / "skills" / "pipelines" / pipeline / filename)
        assert MARK in text, f"{pipeline}/{filename} has no creative brief block"
        assert f"{artifact}.metadata.brief_creativo" in text, f"{pipeline}/{filename} names the wrong artifact"
        assert "skills/meta/creative-intake.md" in text, f"{pipeline}/{filename} does not reference the skill"


def test_the_stage_artifact_matches_the_manifest():
    for pipeline, (filename, artifact) in PHASE1.items():
        manifest = "animated-explainer" if pipeline == "explainer" else pipeline
        data = yaml.safe_load(_read(ROOT / "pipeline_defs" / f"{manifest}.yaml"))
        stage_name = filename.removesuffix("-director.md")
        stage = next(s for s in data["stages"] if s["name"] == stage_name)
        assert artifact in stage.get("produces", []), f"{manifest}.{stage_name} does not produce {artifact}"


def test_manifests_list_the_intake_skill():
    for name in MANIFESTS:
        data = yaml.safe_load(_read(ROOT / "pipeline_defs" / f"{name}.yaml"))
        assert "meta/creative-intake" in data.get("required_skills", []), f"{name}.yaml does not require creative-intake"


def test_script_writing_core_demands_the_brief_before_writing():
    core = _read(ROOT / "skills" / "meta" / "guionista-core.md")
    assert "brief_creativo" in core and "creative-intake.md" in core
    assert "no se escribe guion" in core.lower(), "core must stop the script when the brief is missing"
