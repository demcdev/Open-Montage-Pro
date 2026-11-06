"""The change map must read the repo correctly and never copy a secret.

scripts/change_map.py builds its map from git and from references in the repo, so
these tests pin the parts a reader trusts: which files changed, which tools exist,
what depends on what, and that sensitive files stay out of the generated page.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from tools.tool_registry import ToolRegistry

ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = importlib.util.spec_from_file_location("change_map", ROOT / "scripts" / "change_map.py")
change_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(change_map)

MODIFIED = """diff --git a/tools/base_tool.py b/tools/base_tool.py
index 111..222 100644
--- a/tools/base_tool.py
+++ b/tools/base_tool.py
@@ -10,2 +12,3 @@ class BaseTool:
 keep
-old
+new
+extra
"""
ADDED = """diff --git a/skills/meta/new.md b/skills/meta/new.md
new file mode 100644
--- /dev/null
+++ b/skills/meta/new.md
@@ -0,0 +1 @@
+hello
"""
DELETED = """diff --git a/docs/old.md b/docs/old.md
deleted file mode 100644
--- a/docs/old.md
+++ /dev/null
@@ -1 +0,0 @@
-bye
"""
SECRET = """diff --git a/.env b/.env
--- a/.env
+++ b/.env
@@ -1 +1 @@
-API_KEY=old
+API_KEY=new
"""
BINARY = """diff --git a/assets/a.png b/assets/a.png
new file mode 100644
Binary files /dev/null and b/assets/a.png differ
"""


def _files() -> tuple[list[str], dict[str, dict]]:
    files = change_map.repo_files()
    return files, change_map.load_pipelines(files)


def test_parse_diff_reads_status_lines_and_position():
    changes = change_map.parse_diff(MODIFIED + ADDED + DELETED + BINARY)
    record = changes["tools/base_tool.py"]
    assert (record["status"], record["add"], record["del"], record["line"]) == ("modified", 2, 1, 12)
    assert changes["skills/meta/new.md"]["status"] == "added"
    assert changes["docs/old.md"]["status"] == "deleted"
    assert changes["assets/a.png"]["diff"] == ""


def test_long_diffs_are_cut_and_say_so():
    body = "\n".join(f"+line {i}" for i in range(change_map.MAX_DIFF_LINES + 5))
    text = ADDED.replace("+hello", body)
    record = change_map.parse_diff(text)["skills/meta/new.md"]
    assert record["truncated"] and record["add"] == change_map.MAX_DIFF_LINES + 5
    assert record["diff"].count("\n") < change_map.MAX_DIFF_LINES


@pytest.mark.parametrize("path", [".env", ".env.local", "config/.env.example", "certs/server.pem", "deploy.key", "credentials.json", "secrets.yaml"])
def test_sensitive_files_are_refused(path):
    assert change_map.is_sensitive(path)
    assert change_map.read_text(path) is None


def test_secret_diffs_never_enter_the_map():
    changes = change_map.parse_diff(MODIFIED + SECRET)
    assert set(changes) == {"tools/base_tool.py"}
    assert "API_KEY" not in json.dumps(changes)


def test_no_sensitive_file_is_listed():
    assert not [path for path in change_map.repo_files() if change_map.is_sensitive(path)]


@pytest.mark.parametrize(
    ("path", "layer", "key"),
    [
        ("AGENT_GUIDE.md", "guide", "agent-guide"),
        ("pipeline_defs/animated-explainer.yaml", "pipelines", "pipeline/explainer"),
        ("skills/pipelines/explainer/scene-director.md", "pipelines", "pipeline/explainer"),
        ("skills/creative/prompting/veo-prompting.md", "skills", "skills/prompting"),
        ("skills/meta/reviewer.md", "skills", "skills/meta"),
        (".agents/skills/gsap-core/SKILL.md", "skills", "capa3"),
        ("tools/base_tool.py", "tools", "tools/core"),
        ("tools/video/video_compose.py", "tools", "tools/video"),
        ("schemas/artifacts/brief.schema.json", "schemas", "schemas/artifacts"),
        ("remotion-composer/src/Root.tsx", "engines", "remotion-composer"),
        ("tests/contracts/test_change_map.py", "tests", "tests/contracts"),
        ("config.yaml", "repo", "repo"),
    ],
)
def test_classify(path, layer, key):
    assert change_map.classify(path, {"pipeline_defs/animated-explainer.yaml": "explainer"})[:2] == (layer, key)


def test_python_refs_finds_every_tool_in_a_file_and_skips_helpers():
    text = (
        "from .base import thing\n"
        "class First(BaseTool):\n    name = 'first'\n    capability = 'x'\n    usage_skills = ['core/ffmpeg']\n"
        "class Second(BaseTool):\n    name = 'second'\n    capability = 'x'\n"
        "class Source:\n    name = 'stock'\n"
    )
    refs, tools = change_map.python_refs(text, "tools/video/thing.py", {"tools.video.base": "tools/video/base.py"})
    assert refs == {"tools/video/base.py"}
    assert [tool["name"] for tool in tools] == ["first", "second"]
    assert tools[0]["usage_skills"] == ["core/ffmpeg"]


def test_tool_names_match_the_registry():
    registry = ToolRegistry()
    registry.discover()
    files, manifests = _files()
    _, tool_files = change_map.build_references(files, manifests)
    assert set(tool_files) == set(registry._tools)


def test_references_cover_each_kind_of_link():
    files, manifests = _files()
    edges, _ = change_map.build_references(files, manifests)
    assert ("tools/video/veo_video.py", "skills/creative/prompting/veo-prompting.md") in edges
    assert ("pipeline_defs/animated-explainer.yaml", "skills/meta/technique-selector.md") in edges
    assert ("pipeline_defs/animated-explainer.yaml", "schemas/artifacts/proposal_packet.schema.json") in edges
    assert ("tools/video/video_compose.py", "tools/base_tool.py") in edges


def test_every_file_lands_in_a_known_layer():
    files, manifests = _files()
    folders = change_map.director_folders(manifests)
    layers = {layer["id"] for layer in change_map.LAYERS}
    assert {change_map.classify(path, folders)[0] for path in files} <= layers


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ({"unchanged"}, "unchanged"),
        ({"unchanged", "impacted"}, "impacted"),
        ({"added", "unchanged"}, "added"),
        ({"deleted"}, "deleted"),
        ({"added", "modified"}, "modified"),
        ({"added", "deleted"}, "modified"),
    ],
)
def test_group_status(statuses, expected):
    assert change_map.group_status(statuses) == expected


def test_a_changed_file_marks_who_cites_it():
    record = {"path": "tools/base_tool.py", "status": "modified", "add": 1, "del": 0, "diff": "@@\n+x", "truncated": False, "line": 1}
    data = change_map.build_map({record["path"]: record}, {"title": "t", "scope": "s", "branch": "b", "base": "h"}, "change")
    tools_video = next(node for node in data["nodes"] if node["id"] == "g-tools-video")
    assert tools_video["status"] == "impacted"
    compose = next(f for f in tools_video["files"] if f["path"] == "tools/video/video_compose.py")
    assert compose["via"] == ["tools/base_tool.py"]
    assert any(link["from"] == "g-tools-core" and link["to"] == "g-tools-video" for link in data["impact"]["links"])
    assert any(item["node"] == "g-tools-core" for item in data["attention"])


def test_system_map_shows_no_change():
    data = change_map.build_map({}, {"title": "t", "scope": "s", "branch": "b"}, "system")
    assert {node["status"] for node in data["nodes"]} == {"unchanged"}
    assert not data["impact"]["links"] and not data["attention"]
    assert len(data["pipelines"]) == data["meta"]["counts"]["pipelines"] > 0


def test_page_cannot_be_broken_out_of():
    page = change_map.render({"meta": {"title": "</script><script>alert(1)</script>"}})
    payload = re.search(r'id="change-data">(.*?)</script>', page, re.S).group(1)
    assert "<" not in payload
    assert json.loads(payload)["meta"]["title"].startswith("</script>")


def test_template_is_generic():
    template = change_map.TEMPLATE.read_text(encoding="utf-8")
    assert template.count(change_map.PLACEHOLDER) == 1
    assert not re.search(r"VTEX|comprador|\bPDP\b", template)
    assert ".change-maps/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
