"""Show what fills the disk under projects/ and output/, and move safe leftovers aside.

    .venv/Scripts/python.exe scripts/disk_report.py                     # report only, touches nothing
    .venv/Scripts/python.exe scripts/disk_report.py --detail            # also list every candidate
    .venv/Scripts/python.exe scripts/disk_report.py --apply depuracion  # move one category aside
    .venv/Scripts/python.exe scripts/disk_report.py --restore projects/_papelera/2026-11-08_231500

Nothing is ever deleted. --apply moves the chosen categories into
projects/_papelera/<timestamp>/ with a manifest of where each file came from, and
--restore puts a batch back. Empty the papelera by hand once the projects look right.
Backlot skips folders that start with "_", so the papelera never shows up as a project.

Candidates come only from rules that are safe to reverse:

    parcial     *.part files older than a day: downloads that never finished
    depuracion  dbg_, debug_, chunk_test, chk_ and test_ media, and *_prueba* media
    intermedio  media under hyperframes/**/{_montaje,out,snap}: regenerable, by rendering again
    scratch     files in output/scratch older than a week

A file whose name appears in one of its project's documents (json, md, yaml, txt) is
never a candidate. The events log is left out of that search because it records every
tool call, drafts included. Big files no rule covers are listed for a person to judge.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.paths import PROJECTS_DIR, REPO_ROOT, SCRATCH_DIR

TRASH_NAME = "_papelera"
MANIFEST_NAME = "manifest.json"
CATEGORIES = ("parcial", "depuracion", "intermedio", "scratch")

MEDIA_EXT = {
    ".mp4", ".mov", ".webm", ".mkv", ".ogv", ".avi",
    ".wav", ".mp3", ".m4a", ".aac", ".flac",
    ".png", ".jpg", ".jpeg", ".webp",
}
DOC_EXT = {".json", ".md", ".yaml", ".yml", ".txt"}
DEBUG_NAME = re.compile(r"^(dbg|debug|chunk_test|chk|test)(_|\d|$)|_prueba", re.IGNORECASE)
INTERMEDIATE_DIRS = {"_montaje", "out", "snap"}
SKIP_DIRS = {TRASH_NAME, "node_modules", ".git"}

PARTIAL_MIN_AGE = 24 * 3600
SCRATCH_MIN_AGE = 7 * 24 * 3600
LARGE_FILE_BYTES = 100 * 1024 * 1024
LARGE_FILE_LIMIT = 15


@dataclass
class Candidate:
    path: Path
    size: int
    category: str
    stored_as: str  # path inside a papelera batch, e.g. "projects/litio/renders/dbg.mp4"


@dataclass
class Report:
    project_sizes: dict[str, int] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    protected: int = 0
    large_unsorted: list[tuple[Path, int, bool]] = field(default_factory=list)


def _walk(root: Path):
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield Path(folder) / name


def _is_intermediate(rel: Path) -> bool:
    parts = rel.parts
    if "hyperframes" not in parts:
        return False
    return any(part in INTERMEDIATE_DIRS for part in parts[parts.index("hyperframes") + 1:-1])


def _documents_text(project: Path) -> str:
    """Every project document joined, minus intermediates and the events log."""
    chunks = []
    for path in _walk(project):
        if path.suffix.lower() not in DOC_EXT or _is_intermediate(path.relative_to(project)):
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def _is_cited(name: str, documents: str) -> bool:
    # JSON written with ensure_ascii stores "explotación" as "explotación".
    return name in documents or json.dumps(name)[1:-1] in documents


def _category(rel: Path, age: float) -> str | None:
    if rel.suffix == ".part":
        return "parcial" if age >= PARTIAL_MIN_AGE else None
    if rel.suffix.lower() not in MEDIA_EXT:
        return None
    if _is_intermediate(rel):
        return "intermedio"
    if DEBUG_NAME.search(rel.stem):
        return "depuracion"
    return None


def scan(projects_dir: Path = PROJECTS_DIR, scratch_dir: Path = SCRATCH_DIR, now: float | None = None) -> Report:
    now = time.time() if now is None else now
    report = Report()
    unsorted: list[tuple[Path, int, bool]] = []

    projects = sorted(projects_dir.iterdir()) if projects_dir.is_dir() else []
    for project in (p for p in projects if p.is_dir() and p.name not in SKIP_DIRS):
        documents = _documents_text(project)
        total = 0
        for path in _walk(project):
            stat = path.stat()
            total += stat.st_size
            rel = path.relative_to(project)
            category = _category(rel, now - stat.st_mtime)
            cited = category != "parcial" and _is_cited(path.name, documents)
            if category and not cited:
                stored = Path("projects") / project.name / rel
                report.candidates.append(Candidate(path, stat.st_size, category, stored.as_posix()))
            else:
                if category:
                    report.protected += 1
                if stat.st_size >= LARGE_FILE_BYTES:
                    unsorted.append((path, stat.st_size, cited))
        report.project_sizes[project.name] = total

    if scratch_dir.is_dir():
        for path in _walk(scratch_dir):
            stat = path.stat()
            if now - stat.st_mtime >= SCRATCH_MIN_AGE:
                stored = Path("scratch") / path.relative_to(scratch_dir)
                report.candidates.append(Candidate(path, stat.st_size, "scratch", stored.as_posix()))

    report.large_unsorted = sorted(unsorted, key=lambda item: -item[1])[:LARGE_FILE_LIMIT]
    return report


def apply(report: Report, categories: set[str], trash_root: Path) -> Path | None:
    """Move the chosen categories into a new papelera batch and return it."""
    chosen = [c for c in report.candidates if c.category in categories]
    if not chosen:
        return None
    batch = trash_root / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    moved = []
    try:
        for candidate in chosen:
            target = batch / candidate.stored_as
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(candidate.path), str(target))
            moved.append({
                "original": str(candidate.path),
                "stored_as": candidate.stored_as,
                "size": candidate.size,
                "category": candidate.category,
            })
    finally:
        # Written even after a failed move, so whatever did move can be restored.
        if moved:
            (batch / MANIFEST_NAME).write_text(json.dumps(moved, indent=2), encoding="utf-8")
    return batch


def restore(batch: Path) -> tuple[int, list[str]]:
    """Put a batch back. Returns how many files returned and which originals were in the way."""
    manifest = batch / MANIFEST_NAME
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    restored, blocked = 0, []
    for entry in entries:
        source, original = batch / entry["stored_as"], Path(entry["original"])
        if original.exists():
            blocked.append(entry["original"])
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(original))
        restored += 1
    if not blocked:
        manifest.unlink()
        for folder, _dirs, _files in sorted(os.walk(batch), key=lambda w: -len(w[0])):
            if not os.listdir(folder):
                os.rmdir(folder)
    return restored, blocked


def _fmt(size: float) -> str:
    if size >= 1024 ** 3:
        return f"{size / 1024 ** 3:.1f} GB"
    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.0f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size:.0f} B"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _clip_cache_line() -> str:
    from tools.video.clip_cache import default_cache_dir, default_max_total_bytes

    cache = default_cache_dir()
    size = sum(p.stat().st_size for p in _walk(cache)) if cache.is_dir() else 0
    return f"Caché de clips ({cache}): {_fmt(size)} de un tope de {_fmt(default_max_total_bytes())}"


def print_report(report: Report, detail: bool) -> None:
    usage = shutil.disk_usage(REPO_ROOT)
    print(f"Disco: {_fmt(usage.free)} libres de {_fmt(usage.total)}\n")

    by_project: dict[str, int] = {}
    for c in report.candidates:
        if c.stored_as.startswith("projects/"):
            name = c.stored_as.split("/")[1]
            by_project[name] = by_project.get(name, 0) + c.size
    print(f"projects/  {_fmt(sum(report.project_sizes.values()))}")
    for name, size in sorted(report.project_sizes.items(), key=lambda kv: -kv[1]):
        movable = f"   movible {_fmt(by_project[name])}" if name in by_project else ""
        print(f"  {_fmt(size):>9}  {name}{movable}")

    print("\nCandidatos por categoría")
    for category in CATEGORIES:
        items = [c for c in report.candidates if c.category == category]
        print(f"  {category:<11} {len(items):>4} archivos  {_fmt(sum(c.size for c in items)):>9}")
        if detail:
            for c in sorted(items, key=lambda c: -c.size):
                print(f"      {_fmt(c.size):>9}  {_rel(c.path)}")
    print(f"  Protegidos por estar citados en documentos del proyecto: {report.protected}")

    if report.large_unsorted:
        print("\nArchivos grandes sin categoría (revísalos a mano)")
        for path, size, cited in report.large_unsorted:
            note = "  (citado)" if cited else ""
            print(f"  {_fmt(size):>9}  {_rel(path)}{note}")

    print(f"\n{_clip_cache_line()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", metavar="CATEGORIAS",
                        help=f"categorías a mover, separadas por coma: {', '.join(CATEGORIES)}")
    parser.add_argument("--detail", action="store_true", help="lista cada candidato")
    parser.add_argument("--restore", metavar="LOTE", type=Path, help="carpeta de un lote de la papelera")
    args = parser.parse_args(argv)

    if args.restore:
        restored, blocked = restore(args.restore)
        print(f"Restaurados: {restored}")
        for original in blocked:
            print(f"  No se restauró, ya existe: {original}")
        return 1 if blocked else 0

    report = scan()
    print_report(report, args.detail)
    if not args.apply:
        print("\nNo se movió nada. Para mover una categoría: --apply depuracion")
        return 0

    categories = {c.strip() for c in args.apply.split(",") if c.strip()}
    unknown = categories - set(CATEGORIES)
    if unknown:
        parser.error(f"categorías desconocidas: {', '.join(sorted(unknown))}")
    batch = apply(report, categories, PROJECTS_DIR / TRASH_NAME)
    if batch is None:
        print("\nNo hay candidatos en esas categorías.")
        return 0
    moved = [c for c in report.candidates if c.category in categories]
    print(f"\nMovidos {len(moved)} archivos ({_fmt(sum(c.size for c in moved))}) a {_rel(batch)}")
    print(f"Para deshacer: --restore {_rel(batch)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
