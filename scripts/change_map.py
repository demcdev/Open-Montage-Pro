"""Generate an interactive map of a change, or of the whole system.

    .venv/Scripts/python.exe scripts/change_map.py                 # uncommitted work
    .venv/Scripts/python.exe scripts/change_map.py --commit HEAD   # one commit
    .venv/Scripts/python.exe scripts/change_map.py --base main     # this branch against main
    .venv/Scripts/python.exe scripts/change_map.py --system        # the system, no change

Add --open to open the map, --title to name it and --exclude GLOB to leave files out.
Maps land in .change-maps/, which git ignores because each one copies its diffs.

Everything comes from git and from references in the repo (manifests, usage_skills,
imports, cited paths), so a map shows what was touched and what depends on it. It cannot
say why a change was made, and it reads references from the working tree even for an old
commit. Secrets never enter a map: see is_sensitive.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import webbrowser
from collections import Counter, defaultdict
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).with_name("change_map_template.html")
OUT_DIR = ROOT / ".change-maps"
PLACEHOLDER = "__CHANGE_MAP_DATA__"

MAX_DIFF_LINES = 400
MAX_LISTED_FILES = 150
MAX_LISTED_TESTS = 30
HUB_DEPENDENTS = 15

LAYERS = [
    {"id": "guide", "label": "Guía", "hint": "AGENT_GUIDE, docs"},
    {"id": "pipelines", "label": "Pipelines", "hint": "manifiesto + directores"},
    {"id": "tools", "label": "Herramientas", "hint": "tools/"},
    {"id": "skills", "label": "Skills", "hint": "skills/, .agents/"},
    {"id": "schemas", "label": "Schemas", "hint": "schemas/"},
    {"id": "engines", "label": "Motores", "hint": "render y librerías"},
    {"id": "tests", "label": "Tests", "hint": "tests/"},
    {"id": "repo", "label": "Repo", "hint": "scripts y config"},
]
GROUP_WHY = {
    "agent-guide": "Las reglas que el agente lee antes de actuar: cómo elegir pipeline, cuándo preguntar y qué no hacer.",
    "project-context": "Resumen de la arquitectura para quien entra al proyecto.",
    "agent-instructions": "Puntos de entrada para cada agente (Claude, Codex, Cursor, Copilot). Casi todos remiten a AGENT_GUIDE.",
    "docs": "Documentación para personas.",
    "tools/core": "La base de las herramientas: BaseTool, el registro que las descubre, costos y enrutado de proveedores.",
    "tools/video": "Generación, edición y composición de video. Aquí están video_compose y los proveedores de video.",
    "tools/audio": "Voz, música, mezcla y mastering.",
    "tools/graphics": "Imágenes, diagramas y animación matemática.",
    "tools/analysis": "Transcripción, análisis de video y control técnico.",
    "tools/avatar": "Lip-sync y cabezas parlantes.",
    "tools/enhancement": "Quitar fondo, escalar y restaurar imagen.",
    "tools/subtitle": "Subtítulos.",
    "skills/core": "Manuales de oficio básico: ffmpeg, color, subtítulos, loudness y especificaciones de entrega.",
    "skills/creative": "Manuales creativos: montaje, cinematografía, sonido y catálogo de técnicas.",
    "skills/prompting": "Cómo escribirle a cada modelo de generación. Se leen desde usage_skills.",
    "skills/meta": "Cómo trabaja el agente: selección de técnicas, revisión, checkpoints y puertas de calidad.",
    "skills/index": "Índices que dicen qué skill existe y cuándo se carga.",
    "capa3": "Conocimiento externo sobre motores y APIs. Se llega aquí con agent_skills.",
    "schemas/artifacts": "El contrato de lo que cada etapa entrega. Si cambia, cambian todas las etapas que lo usan.",
    "remotion-composer": "Motor de render en React para escenas, tipografía y gráficos.",
    "lib": "Librerías compartidas del proyecto.",
    "backlot": "Tablero en el navegador que muestra una producción mientras corre.",
    "ink-theater": "Motor de animación dibujada a tinta.",
    "styles": "Estilos visuales reutilizables.",
    "tests/contracts": "Tests que comprueban que manifiestos, skills, schemas y herramientas siguen de acuerdo entre sí.",
    "tests/tools": "Tests de cada herramienta.",
    "scripts": "Utilidades que se corren a mano.",
}
AGENT_FILES = {"CLAUDE.md", "AGENTS.md", "CODEX.md", "COPILOT.md", "CURSOR.md", ".windsurfrules"}
DOC_FILES = {"CONTRIBUTING.md", "PROMPT_GALLERY.md", "README.md", "README_zh-CN.md", "LICENSE"}
ENGINES = {"remotion-composer", "ink-theater", "backlot", "lib", "styles"}
SCANNED_SUFFIXES = {".py", ".md", ".yaml", ".yml"}
CODE_SUFFIXES = {".py", ".ts", ".tsx"}
TOOL_ATTRS = {"name", "capability", "usage_skills", "agent_skills"}

PATH_REF = re.compile(r"(?:skills|schemas|tools|pipeline_defs|docs|remotion-composer|lib|scripts|styles)/[\w./-]+\.(?:md|py|json|ya?ml|tsx?)")
NAME_REF = re.compile(r"""["'`]([\w.-]+\.(?:md|ya?ml|json))["'`]""")
HUNK = re.compile(r"^@@ -\S+ \+(\d+)")


def run_git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    return done.stdout


def is_sensitive(path: str) -> bool:
    """True for files whose content must never be read or copied into a map."""
    name = PurePosixPath(path).name.lower()
    return (
        name.startswith(".env")
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
        or name in {"credentials.json", "secrets.json", "secrets.yaml", "secrets.yml", "id_rsa"}
    )


def read_text(path: str) -> str | None:
    if is_sensitive(path):
        return None
    try:
        data = (ROOT / path).read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def parse_diff(text: str) -> dict[str, dict]:
    """Split `git diff` output into one record per file, dropping sensitive files."""
    changes = {}
    for chunk in re.split(r"(?m)^(?=diff --git )", text):
        if not chunk.startswith("diff --git "):
            continue
        lines = chunk.replace("\r\n", "\n").rstrip("\n").split("\n")
        first_hunk = next((i for i, line in enumerate(lines) if line.startswith("@@")), len(lines))
        head, body = lines[:first_hunk], lines[first_hunk:]
        path = _diff_path(head)
        if is_sensitive(path):
            continue
        status = "modified"
        if any(line.startswith("new file mode") for line in head):
            status = "added"
        elif any(line.startswith("deleted file mode") for line in head):
            status = "deleted"
        hunk = HUNK.match(body[0]) if body else None
        changes[path] = {
            "path": path,
            "status": status,
            "add": sum(line.startswith("+") for line in body),
            "del": sum(line.startswith("-") for line in body),
            "diff": "\n".join(body[:MAX_DIFF_LINES]),
            "truncated": len(body) > MAX_DIFF_LINES,
            "line": int(hunk.group(1)) if hunk else 1,
        }
    return changes


def _diff_path(head: list[str]) -> str:
    path = None
    for line in head:
        if line.startswith("rename to "):
            return line[len("rename to "):]
        if line.startswith("+++ b/"):
            return line[len("+++ b/"):].rstrip("\t")
        if line.startswith("--- a/"):
            path = line[len("--- a/"):].rstrip("\t")
    if path:
        return path
    return head[0].split(" b/", 1)[-1]


def untracked_change(path: str) -> dict:
    text = read_text(path)
    record = {"path": path, "status": "added", "add": 0, "del": 0, "diff": "", "truncated": False, "line": 1}
    if text is None:
        return record
    lines = text.replace("\r\n", "\n").rstrip("\n").split("\n")
    record["add"] = len(lines)
    body = [f"@@ -0,0 +1,{len(lines)} @@", *(f"+{line}" for line in lines)]
    record["diff"] = "\n".join(body[:MAX_DIFF_LINES])
    record["truncated"] = len(body) > MAX_DIFF_LINES
    return record


def repo_files() -> list[str]:
    names = run_git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    return sorted(name for name in set(names) if not is_sensitive(name))


def collect_changes(args: argparse.Namespace) -> tuple[dict[str, dict], dict]:
    branch = run_git("rev-parse", "--abbrev-ref", "HEAD").strip()
    meta = {"branch": branch}
    if args.commit:
        short = run_git("rev-parse", "--short", args.commit).strip()
        subject = run_git("log", "-1", "--format=%s", args.commit).strip()
        changes = parse_diff(run_git("show", "--format=", "-M", "--no-color", "--no-ext-diff", args.commit))
        meta |= {"title": subject, "scope": f"Commit {short}", "base": short, "slug": short}
    elif args.base:
        base = run_git("merge-base", args.base, "HEAD").strip()
        changes = parse_diff(run_git("diff", "-M", "--no-color", "--no-ext-diff", base, "HEAD"))
        meta |= {
            "title": f"{branch} frente a {args.base}",
            "scope": f"Todo lo que la rama agrega sobre {args.base}.",
            "base": f"{args.base} · {base[:7]}",
            "slug": branch,
        }
    else:
        changes = parse_diff(run_git("diff", "-M", "--no-color", "--no-ext-diff", "HEAD"))
        for path in run_git("ls-files", "--others", "--exclude-standard").splitlines():
            if not is_sensitive(path):
                changes[path] = untracked_change(path)
        meta |= {
            "title": f"Trabajo sin commit en {branch}",
            "scope": "Lo que hay en la carpeta frente al último commit, incluidos los archivos nuevos.",
            "base": "HEAD · " + run_git("rev-parse", "--short", "HEAD").strip(),
            "slug": branch,
        }
    excluded = [path for path in changes if any(fnmatch(path, glob) for glob in args.exclude)]
    for path in excluded:
        del changes[path]
    return changes, meta


# --- Reading the repo -------------------------------------------------------------


def load_pipelines(files: list[str]) -> dict[str, dict]:
    manifests = {}
    for path in files:
        if not (path.startswith("pipeline_defs/") and path.endswith((".yaml", ".yml"))):
            continue
        text = read_text(path)
        data = yaml.safe_load(text) if text else None
        if isinstance(data, dict) and data.get("stages"):
            manifests[path] = data
    return manifests


def manifest_skills(data: dict) -> list[str]:
    refs = list(data.get("required_skills") or [])
    refs.append((data.get("orchestration") or {}).get("skill"))
    refs.extend(stage.get("skill") for stage in data["stages"])
    return [ref for ref in refs if ref]


def manifest_tools(data: dict) -> set[str]:
    names = set((data.get("reference_input") or {}).get("analysis_tools") or [])
    for stage in data["stages"]:
        names.update(stage.get("tools_available") or [])
        for sub in stage.get("sub_stages") or []:
            names.update(sub.get("tools_available") or [])
    return names


def stage_artifacts(stage: dict) -> tuple[list[str], list[str]]:
    consumed = list(stage.get("required_artifacts_in") or []) + list(stage.get("optional_artifacts_in") or [])
    return consumed, list(stage.get("produces") or [])


def director_folders(manifests: dict[str, dict]) -> dict[str, str]:
    """Map each manifest to its folder under skills/pipelines, when it has one."""
    folders = {}
    for path, data in manifests.items():
        for ref in manifest_skills(data):
            if ref.startswith("pipelines/"):
                folders[path] = ref.split("/")[1]
                break
    return folders


def classify(path: str, folders: dict[str, str]) -> tuple[str, str, str]:
    """Return the layer, group key and group label a file belongs to."""
    parts = path.split("/")
    top = parts[0]
    if path == "AGENT_GUIDE.md":
        return "guide", "agent-guide", "AGENT_GUIDE"
    if path == "PROJECT_CONTEXT.md":
        return "guide", "project-context", "PROJECT_CONTEXT"
    if path in AGENT_FILES or top in {".cursor", ".codex"} or parts[:2] in (
        [".claude", "agents"],
        [".claude", "commands"],
    ):
        return "guide", "agent-instructions", "Instrucciones por agente"
    if path in DOC_FILES or top == "docs":
        return "guide", "docs", "Documentación"
    if top == "pipeline_defs":
        stem = PurePosixPath(path).stem
        folder = folders.get(path, stem)
        return "pipelines", f"pipeline/{folder}", folder
    if parts[:2] == ["skills", "pipelines"] and len(parts) > 3:
        return "pipelines", f"pipeline/{parts[2]}", parts[2]
    if parts[:3] == ["skills", "creative", "prompting"]:
        return "skills", "skills/prompting", "skills/prompting"
    if top == "skills":
        if len(parts) == 2:
            return "skills", "skills/index", "skills: índices"
        return "skills", f"skills/{parts[1]}", f"skills/{parts[1]}"
    if parts[:2] in ([".agents", "skills"], [".claude", "skills"]):
        return "skills", "capa3", "Capa 3 (.agents)"
    if top == "tools":
        if len(parts) == 2:
            return "tools", "tools/core", "tools: núcleo"
        return "tools", f"tools/{parts[1]}", f"tools/{parts[1]}"
    if top == "schemas" and len(parts) > 2:
        return "schemas", f"schemas/{parts[1]}", f"schemas/{parts[1]}"
    if top in ENGINES:
        return "engines", top, top
    if top == "tests":
        if len(parts) == 2:
            return "tests", "tests/core", "tests: base"
        return "tests", f"tests/{parts[1]}", f"tests/{parts[1]}"
    if top == "scripts":
        return "repo", "scripts", "scripts"
    return "repo", "repo", "Config y raíz"


def python_refs(text: str, path: str, modules: dict[str, str]) -> tuple[set[str], list[dict[str, object]]]:
    """Return the repo files a module imports, plus the name and skill pointers of its tools."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set(), []
    refs: set[str] = set()
    tools: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    refs.add(modules[alias.name])
        elif isinstance(node, ast.ImportFrom):
            package = node.module or ""
            if node.level:
                base = path.split("/")[:-node.level]
                package = ".".join(base + ([package] if package else []))
            for alias in node.names:
                refs.update(modules[name] for name in (f"{package}.{alias.name}", package) if name in modules)
        elif isinstance(node, ast.ClassDef):
            tool: dict[str, object] = {}
            for item in node.body:
                target = item.targets[0] if isinstance(item, ast.Assign) else item.target if isinstance(item, ast.AnnAssign) else None
                if isinstance(target, ast.Name) and target.id in TOOL_ATTRS and item.value:
                    try:
                        tool[target.id] = ast.literal_eval(item.value)
                    except ValueError:
                        pass
            if tool.get("name") and tool.get("capability"):
                tools.append(tool)
    return refs, tools


def build_references(files: list[str], manifests: dict[str, dict]) -> tuple[set[tuple[str, str]], dict[str, str]]:
    """Return every (citing file, cited file) pair and the file of each tool name."""
    known = set(files)
    by_name: dict[str, list[str]] = defaultdict(list)
    modules: dict[str, str] = {}
    for path in files:
        by_name[PurePosixPath(path).name].append(path)
        if path.endswith(".py"):
            module = path[:-3].replace("/", ".").removesuffix(".__init__")
            modules[module] = path

    edges: set[tuple[str, str]] = set()
    tool_files: dict[str, str] = {}
    pointers: list[tuple[str, dict[str, object]]] = []
    for path in files:
        if PurePosixPath(path).suffix not in SCANNED_SUFFIXES or path.startswith((".agents/", ".claude/skills/")):
            continue
        text = read_text(path)
        if text is None:
            continue
        cited = {ref for ref in PATH_REF.findall(text) if ref in known}
        if path.endswith(".py"):
            cited |= {by_name[n][0] for n in NAME_REF.findall(text) if len(by_name.get(n, [])) == 1}
            imported, tools = python_refs(text, path, modules)
            cited |= imported
            if path.startswith("tools/"):
                for tool in tools:
                    tool_files[str(tool["name"])] = path
                    pointers.append((path, tool))
        edges.update((path, target) for target in cited if target != path)

    for path, tool in pointers:
        for skill in tool.get("usage_skills") or []:
            edges.add((path, f"skills/{skill}.md"))
        for skill in tool.get("agent_skills") or []:
            edges.add((path, f".agents/skills/{skill}/SKILL.md"))
    for path, data in manifests.items():
        edges.update((path, f"skills/{ref}.md") for ref in manifest_skills(data))
        edges.update((path, tool_files[name]) for name in manifest_tools(data) if name in tool_files)
        for stage in data["stages"]:
            for artifact in sum(stage_artifacts(stage), []):
                edges.add((path, f"schemas/artifacts/{artifact}.schema.json"))
    return {(a, b) for a, b in edges if a in known and b in known}, tool_files


# --- Building the map -------------------------------------------------------------


def slug(key: str) -> str:
    return "g-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def group_status(statuses: set[str]) -> str:
    touched = statuses - {"unchanged", "impacted"}
    if touched == {"added"}:
        return "added"
    if touched == {"deleted"}:
        return "deleted"
    if touched:
        return "modified"
    return "impacted" if "impacted" in statuses else "unchanged"


def group_why(key: str, files: list[str], manifests: dict[str, dict]) -> str:
    if key in GROUP_WHY:
        return GROUP_WHY[key]
    for path in files:
        if path in manifests:
            return " ".join(str(manifests[path].get("description", "")).split()) or f"Pipeline {path}."
    if key.startswith("pipeline/"):
        return "Directores de este pipeline."
    if key.startswith("schemas/"):
        return "Contratos de datos de esta área."
    if key.startswith("tools/"):
        return "Herramientas de esta área."
    if key.startswith("tests/"):
        return "Tests de esta área."
    return "Archivos de configuración y de la raíz del repo."


def build_stages(manifests, changes, tool_files, classify_file) -> list[dict]:
    pipelines = []
    for path, data in sorted(manifests.items()):
        _, key, _ = classify_file(path)
        stages = []

        def artifacts(names: list[str]) -> list[dict]:
            return [{"name": name, "changed": f"schemas/artifacts/{name}.schema.json" in changes} for name in names]

        for stage in data["stages"]:
            consumed, produced = stage_artifacts(stage)
            tools = [
                {
                    "name": name,
                    "group": slug(classify_file(tool_files[name])[1]),
                    "changed": tool_files[name] in changes,
                }
                for name in stage.get("tools_available") or []
                if name in tool_files
            ]
            skill = stage.get("skill")
            skill_changed = bool(skill) and f"skills/{skill}.md" in changes
            inputs, outputs = artifacts(consumed), artifacts(produced)
            stages.append({
                "name": stage.get("name", ""),
                "skill": skill.split("/")[-1] if skill else "",
                "skillChanged": skill_changed,
                "approval": bool(stage.get("human_approval_default")),
                "in": inputs,
                "out": outputs,
                "tools": tools,
                "changed": skill_changed or any(item["changed"] for item in tools + inputs + outputs),
            })
        pipelines.append({
            "name": data.get("name", PurePosixPath(path).stem),
            "group": slug(key),
            "description": " ".join(str(data.get("description", "")).split()),
            "stages": stages,
            "changed": path in changes or any(s["changed"] for s in stages),
        })
    return sorted(pipelines, key=lambda p: (not p["changed"], p["name"]))


def build_map(changes: dict[str, dict], meta: dict, mode: str) -> dict:
    files = sorted(set(repo_files()) | set(changes))
    manifests = load_pipelines(files)
    folders = director_folders(manifests)
    edges, tool_files = build_references(files, manifests)
    classify_file = lambda path: classify(path, folders)

    impacted: dict[str, set[str]] = defaultdict(set)
    test_hits: dict[str, set[str]] = defaultdict(set)
    dependents: dict[str, set[str]] = defaultdict(set)
    tests_of: dict[str, set[str]] = defaultdict(set)
    for citing, cited in edges:
        if citing.startswith("tests/"):
            tests_of[cited].add(citing)
            if cited in changes:
                test_hits[citing].add(cited)
        else:
            dependents[cited].add(citing)
            if cited in changes and citing not in changes:
                impacted[citing].add(cited)

    members: dict[str, list[str]] = defaultdict(list)
    placed: dict[str, tuple[str, str]] = {}
    for path in files:
        layer, key, label = classify_file(path)
        members[key].append(path)
        placed[key] = (layer, label)

    nodes = []
    for key, paths in members.items():
        layer, label = placed[key]
        records = []
        statuses = set()
        unchanged = 0
        for path in paths:
            if path in changes:
                records.append(changes[path])
                statuses.add(changes[path]["status"])
            elif path in impacted:
                via = sorted(impacted[path])
                records.append({"path": path, "status": "impacted", "via": via[:3] + ([f"{len(via) - 3} más"] if len(via) > 3 else [])})
                statuses.add("impacted")
            else:
                statuses.add("unchanged")
                unchanged += 1
                if unchanged <= MAX_LISTED_FILES:
                    records.append({"path": path, "status": "unchanged"})
        touched = [r for r in records if r["status"] not in {"unchanged", "impacted"}]
        common = PurePosixPath(paths[0]).parent.as_posix() if len(paths) > 1 else paths[0]
        nodes.append({
            "id": slug(key),
            "label": label,
            "path": common if common != "." else "raíz del repo",
            "layer": layer,
            "kind": f"{len(paths)} archivo{'s' if len(paths) != 1 else ''}",
            "status": group_status(statuses),
            "why": group_why(key, paths, manifests),
            "files": records,
            "fileCount": len(paths),
            "hidden": max(unchanged - MAX_LISTED_FILES, 0),
            "changed": len(touched),
            "impactedCount": sum(r["status"] == "impacted" for r in records),
            "add": sum(r["add"] for r in touched),
            "del": sum(r["del"] for r in touched),
            "tests": sorted({t for path in paths for t in tests_of.get(path, ())})[:MAX_LISTED_TESTS],
        })
    order = {layer["id"]: i for i, layer in enumerate(LAYERS)}
    nodes.sort(key=lambda n: (order[n["layer"]], n["label"]))

    group_of = {path: slug(classify_file(path)[1]) for path in files}
    layer_of = {node["id"]: node["layer"] for node in nodes}
    weights: Counter = Counter()
    impact_edges = set()
    links: dict[tuple[str, str], set[str]] = defaultdict(set)
    for citing, cited in edges:
        a, b = group_of[citing], group_of[cited]
        if citing in impacted and cited in impacted[citing]:
            links[b, a].add(citing)
        if a == b or layer_of[a] == layer_of[b] or "tests" in (layer_of[a], layer_of[b]):
            continue
        weights[a, b] += 1
        if citing in impacted and cited in impacted[citing]:
            impact_edges.add((a, b))

    tests = [
        {"path": path, "hits": len(hits), "changed": path in changes}
        for path, hits in test_hits.items()
    ] + [
        {"path": path, "hits": 0, "changed": True}
        for path in changes
        if path.startswith("tests/") and path.endswith(".py") and path not in test_hits and changes[path]["status"] != "deleted"
    ]
    tests.sort(key=lambda t: (-t["hits"], t["path"]))
    tests = tests[:MAX_LISTED_TESTS]
    command = ".venv/Scripts/python.exe -m pytest " + " ".join(t["path"] for t in tests) if tests else ""

    return {
        "meta": {
            **{k: v for k, v in meta.items() if k != "slug"},
            "mode": mode,
            "generatedAt": datetime.now().astimezone().isoformat(timespec="minutes"),
            "repoRoot": ROOT.as_posix(),
            "summary": summarize(changes, nodes, mode),
            "counts": count(changes, impacted, nodes, edges, tool_files, manifests, mode),
        },
        "layers": LAYERS,
        "nodes": nodes,
        "edges": [
            {"from": a, "to": b, "count": n, "impact": (a, b) in impact_edges}
            for (a, b), n in sorted(weights.items())
        ],
        "impact": {
            "links": [{"from": a, "to": b, "count": len(citing)} for (a, b), citing in sorted(links.items())],
            "tests": tests,
            "command": command,
        },
        "attention": review_first(changes, dependents, test_hits, group_of, {node["id"]: node["label"] for node in nodes}),
        "pipelines": build_stages(manifests, changes, tool_files, classify_file),
    }


def summarize(changes: dict[str, dict], nodes: list[dict], mode: str) -> list[str]:
    if mode == "system":
        return [
            "Cada franja es una capa y cada bloque agrupa archivos que viven juntos.",
            "Una línea significa que un bloque cita o usa al otro. Pasa el cursor por un bloque para aislar sus conexiones.",
            "En Etapas del pipeline eliges uno y ves qué recibe, qué produce y con qué herramientas trabaja cada etapa.",
        ]
    if not changes:
        return ["No hay cambios en este rango."]
    lines = []
    for layer in LAYERS:
        touched = [n for n in nodes if n["layer"] == layer["id"] and n["changed"]]
        if touched:
            total = sum(n["changed"] for n in touched)
            add, removed = sum(n["add"] for n in touched), sum(n["del"] for n in touched)
            names = ", ".join(n["label"] for n in touched[:4]) + (f" y {len(touched) - 4} más" if len(touched) > 4 else "")
            lines.append(f"{layer['label']}: {total} archivo{'s' if total != 1 else ''} (+{add} −{removed}) en {names}.")
    return lines


def count(changes, impacted, nodes, edges, tool_files, manifests, mode) -> dict:
    if mode == "system":
        in_layer = lambda layer: sum(n["fileCount"] for n in nodes if n["layer"] == layer)
        return {
            "files": sum(n["fileCount"] for n in nodes),
            "pipelines": len(manifests),
            "tools": len(tool_files),
            "skills": sum(n["fileCount"] for n in nodes if n["id"].startswith("g-skills")),
            "schemas": in_layer("schemas"),
            "tests": in_layer("tests"),
            "references": len(edges),
        }
    statuses = Counter(record["status"] for record in changes.values())
    return {
        "added": statuses["added"],
        "modified": statuses["modified"],
        "deleted": statuses["deleted"],
        "impacted": len(impacted),
        "add": sum(record["add"] for record in changes.values()),
        "del": sum(record["del"] for record in changes.values()),
    }


def review_first(changes, dependents, test_hits, group_of, labels) -> list[dict]:
    """Facts git and the references can prove, most dangerous first."""
    items = []
    for path, record in sorted(changes.items()):
        if record["status"] == "deleted":
            count_dependents = len(dependents.get(path, ()))
            items.append({
                "title": f"Se eliminó {path}",
                "detail": f"{count_dependents} archivos todavía lo citan." if count_dependents else "Nada lo cita ya.",
                "node": group_of[path],
            })
    for path in sorted(changes):
        if path.startswith("schemas/") and path.endswith(".json") and changes[path]["status"] == "modified":
            items.append({"title": f"Cambió un contrato: {PurePosixPath(path).name}", "detail": "Afecta a toda etapa que lo produce o lo recibe.", "node": group_of[path]})
    hubs = sorted(
        ((len(dependents[path]), path) for path in changes if len(dependents.get(path, ())) >= HUB_DEPENDENTS),
        reverse=True,
    )
    for total, path in hubs[:5]:
        items.append({"title": f"{PurePosixPath(path).name} es muy citado", "detail": f"{total} archivos dependen de él.", "node": group_of[path]})
    covered = {path for hits in test_hits.values() for path in hits}
    untested: dict[str, int] = Counter()
    for path, record in changes.items():
        code = PurePosixPath(path).suffix in CODE_SUFFIXES and not path.startswith("tests/")
        if code and record["status"] != "deleted" and path not in covered and not path.endswith("__init__.py"):
            untested[group_of[path]] += 1
    for group, total in untested.most_common(4):
        items.append({
            "title": f"{labels[group]}: {total} archivo{'s' if total != 1 else ''} de código sin un test que lo cite",
            "detail": "No significa que no estén probados: ningún test los nombra directamente.",
            "node": group,
        })
    return items[:12]


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return TEMPLATE.read_text(encoding="utf-8").replace(PLACEHOLDER, payload, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--commit", help="map one commit")
    source.add_argument("--base", help="map this branch against a base ref")
    source.add_argument("--system", action="store_true", help="map the system with no change")
    parser.add_argument("--title", help="title shown on the map")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="leave matching files out of the change")
    parser.add_argument("--open", action="store_true", help="open the map in the browser")
    args = parser.parse_args()

    if args.system:
        changes: dict[str, dict] = {}
        meta = {
            "title": "Cómo está armado OpenMontage",
            "scope": "Vista general: las capas del proyecto y cómo se citan entre sí.",
            "branch": run_git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "slug": "sistema",
        }
    else:
        changes, meta = collect_changes(args)
    if args.title:
        meta["title"] = args.title

    html = render(build_map(changes, meta, "system" if args.system else "change"))
    OUT_DIR.mkdir(exist_ok=True)
    name = "sistema" if args.system else f"{datetime.now():%Y%m%d-%H%M}-{re.sub(r'[^a-z0-9]+', '-', meta['slug'].lower()).strip('-')}"
    out = OUT_DIR / f"{name}.html"
    out.write_text(html, encoding="utf-8")
    print(out)
    if args.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
