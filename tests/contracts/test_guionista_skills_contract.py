"""Contract tests for the guionista (scriptwriting) skills.

The skills are an agent-facing contract: a shared core plus one skill per type of
video. They must exist, be discoverable from the guide and the skill index, be
linked from the script-writing director of the pipelines they apply to, and be
listed in those pipeline manifests (which must point at files that exist).
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
META = ROOT / "skills" / "meta"
CORE = "guionista-core"
FICTION = "guionista-ficcion-animada"
DOC = "guionista-documental"
MARK = "<!-- guionista-skill -->"

# pipeline -> (director file that carries the link, skills it must reference)
LINKS = {
    "character-animation": ("script-director.md", (CORE, FICTION)),
    "cinematic": ("script-director.md", (CORE, FICTION)),
    "animation": ("script-director.md", (CORE, FICTION, DOC)),
    "explainer": ("script-director.md", (CORE, DOC)),
    "hybrid": ("script-director.md", (CORE, DOC)),
    "avatar-spokesperson": ("script-director.md", (CORE, DOC)),
    "documentary-montage": ("scene-director.md", (CORE, DOC)),
}
# manifest -> required_skills entries it must carry
MANIFEST_SKILLS = {
    "character-animation": (CORE, FICTION),
    "cinematic": (CORE, FICTION),
    "animation": (CORE, FICTION, DOC),
    "animated-explainer": (CORE, DOC),
    "hybrid": (CORE, DOC),
    "avatar-spokesperson": (CORE, DOC),
    "documentary-montage": (CORE, DOC),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_guionista_skills_exist_with_required_sections():
    core = _read(META / f"{CORE}.md")
    for needle in ("YouTube Policy Gate", "script.schema.json", "promesa", "bucles abiertos", "Localización"):
        assert needle in core, f"core is missing: {needle}"
    fiction = _read(META / f"{FICTION}.md")
    for needle in ("Deseo", "libro de reglas", "cliffhanger", "required_actions", "Cortes relámpago"):
        assert needle.lower() in fiction.lower(), f"fiction skill is missing: {needle}"
    doc = _read(META / f"{DOC}.md")
    for needle in ("source_ref", "afirmación", "difamación", "licencia"):
        assert needle.lower() in doc.lower(), f"documentary skill is missing: {needle}"
    for name in (FICTION, DOC):
        assert f"{CORE}.md" in _read(META / f"{name}.md"), f"{name} must point at the core"
    assert "desde el final del puente" in core.lower(), "core must say when three open loops are required"
    assert "en un mismo plano" in fiction.lower(), "fiction skill must limit characters per shot, not per scene"
    assert "humor por colisión" in fiction.lower(), "fiction skill must list humor by collision as a pillar"
    assert "lo gigante" in fiction.lower() and "lo cotidiano" in fiction.lower(), "the collision pillar must name the giant-versus-everyday clash"


def test_guionista_skills_are_discoverable():
    index = _read(ROOT / "skills" / "INDEX.md")
    guide = _read(ROOT / "AGENT_GUIDE.md")
    for name in (CORE, FICTION, DOC):
        assert f"meta/{name}.md" in index, f"INDEX.md does not list {name}"
        assert f"skills/meta/{name}.md" in guide, f"AGENT_GUIDE.md does not mention {name}"


def test_script_writing_directors_link_the_skills():
    for pipeline, (filename, skills) in LINKS.items():
        text = _read(ROOT / "skills" / "pipelines" / pipeline / filename)
        assert MARK in text, f"{pipeline}/{filename} has no guionista block"
        for name in skills:
            assert f"skills/meta/{name}.md" in text, f"{pipeline}/{filename} does not reference {name}"


def test_manifests_list_the_skills_and_files_exist():
    for pipeline, skills in MANIFEST_SKILLS.items():
        data = yaml.safe_load(_read(ROOT / "pipeline_defs" / f"{pipeline}.yaml"))
        required = data.get("required_skills", [])
        for name in skills:
            entry = f"meta/{name}"
            assert entry in required, f"{pipeline}.yaml required_skills is missing {entry}"
            assert (ROOT / "skills" / f"{entry}.md").is_file(), f"{entry}.md does not exist"
