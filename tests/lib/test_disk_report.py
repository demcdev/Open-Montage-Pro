"""The disk report only ever proposes files that are safe to move, and can put them back."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from scripts import disk_report
from scripts.disk_report import apply, restore, scan

DAY = 24 * 3600


def _file(path: Path, size: int = 10, *, age: float = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if age:
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
    return path


def _categories(report) -> dict[str, str]:
    return {c.path.name: c.category for c in report.candidates}


def test_only_the_safe_rules_produce_candidates(tmp_path):
    projects, scratch = tmp_path / "projects", tmp_path / "output" / "scratch"
    p = projects / "demo"
    _file(p / "renders" / "dbg_clip.mp4")
    _file(p / "renders" / "chunk_test2.mp4")
    _file(p / "renders" / "chk3d_luna.png")
    _file(p / "renders" / "borrador_1min_prueba.mp4")
    _file(p / "renders" / "testimonio.mp4")          # "test" is a prefix of a real word
    _file(p / "renders" / "final.mp4")
    _file(p / "renders" / "dbg_notes.json")          # not media
    _file(p / "hyperframes" / "_montaje" / "voz.wav")
    _file(p / "hyperframes" / "luna_v5" / "out" / "luna.mp4")
    _file(p / "hyperframes" / "luna_v5" / "index.mp4")  # composition source, not an intermediate
    _file(p / "assets" / "clip.mp4.part", age=2 * DAY)
    _file(p / "assets" / "fresh.mp4.part")           # may still be downloading
    _file(scratch / "old.mp4", age=8 * DAY)
    _file(scratch / "new.mp4")

    assert _categories(scan(projects, scratch)) == {
        "dbg_clip.mp4": "depuracion",
        "chunk_test2.mp4": "depuracion",
        "chk3d_luna.png": "depuracion",
        "borrador_1min_prueba.mp4": "depuracion",
        "voz.wav": "intermedio",
        "luna.mp4": "intermedio",
        "clip.mp4.part": "parcial",
        "old.mp4": "scratch",
    }


def test_a_file_cited_by_a_project_document_is_protected(tmp_path):
    projects = tmp_path / "projects"
    p = projects / "demo"
    _file(p / "renders" / "dbg_keep.mp4")
    _file(p / "renders" / "dbg_explotación.mp4")
    _file(p / "renders" / "dbg_loose.mp4")
    (p / "artifacts").mkdir()
    (p / "artifacts" / "edit_decisions.json").write_text(
        json.dumps({"clips": ["renders/dbg_keep.mp4", "renders/dbg_explotación.mp4"]}),
        encoding="utf-8",
    )
    # The events log mentions every tool output; it must not protect anything.
    (p / "events.jsonl").write_text('{"output": "renders/dbg_loose.mp4"}\n', encoding="utf-8")

    report = scan(projects, tmp_path / "none")
    assert _categories(report) == {"dbg_loose.mp4": "depuracion"}
    assert report.protected == 2


def test_a_concat_list_inside_an_intermediate_does_not_protect_its_siblings(tmp_path):
    projects = tmp_path / "projects"
    montage = projects / "demo" / "hyperframes" / "_montaje"
    _file(montage / "video_mudo.mp4")
    (montage / "videos.txt").write_text("file 'video_mudo.mp4'\n", encoding="utf-8")
    assert _categories(scan(projects, tmp_path / "none")) == {"video_mudo.mp4": "intermedio"}


def test_big_files_no_rule_covers_are_listed_for_a_person(tmp_path, monkeypatch):
    monkeypatch.setattr(disk_report, "LARGE_FILE_BYTES", 100)
    projects = tmp_path / "projects"
    big = _file(projects / "demo" / "renders" / "amaneceres.mp4", 500)
    _file(projects / "demo" / "renders" / "small.mp4", 50)
    report = scan(projects, tmp_path / "none")
    assert report.candidates == []
    assert report.large_unsorted == [(big, 500, False)]
    assert report.project_sizes == {"demo": 550}


def test_the_papelera_is_not_scanned_as_a_project(tmp_path):
    projects = tmp_path / "projects"
    _file(projects / "_papelera" / "2026-01-01_000000" / "projects" / "demo" / "dbg_a.mp4")
    report = scan(projects, tmp_path / "none")
    assert report.candidates == [] and report.project_sizes == {}


def test_apply_moves_only_the_chosen_categories_and_restore_puts_them_back(tmp_path):
    projects, scratch = tmp_path / "projects", tmp_path / "output" / "scratch"
    debug = _file(projects / "demo" / "renders" / "dbg_a.mp4", 7)
    voice = _file(projects / "demo" / "hyperframes" / "_montaje" / "voz.wav")
    old = _file(scratch / "old.mp4", age=8 * DAY)

    batch = apply(scan(projects, scratch), {"depuracion", "scratch"}, projects / "_papelera")
    assert not debug.exists() and not old.exists() and voice.exists()
    assert (batch / "projects" / "demo" / "renders" / "dbg_a.mp4").read_bytes() == b"x" * 7
    manifest = json.loads((batch / "manifest.json").read_text(encoding="utf-8"))
    assert {entry["category"] for entry in manifest} == {"depuracion", "scratch"}

    assert restore(batch) == (2, [])
    assert debug.read_bytes() == b"x" * 7 and old.exists()
    assert not batch.exists()


def test_restore_never_overwrites_a_file_that_came_back(tmp_path):
    projects = tmp_path / "projects"
    debug = _file(projects / "demo" / "renders" / "dbg_a.mp4", 7)
    batch = apply(scan(projects, tmp_path / "none"), {"depuracion"}, projects / "_papelera")
    _file(debug, 3)  # regenerated meanwhile

    restored, blocked = restore(batch)
    assert (restored, blocked) == (0, [str(debug)])
    assert debug.read_bytes() == b"x" * 3
    assert (batch / "manifest.json").exists()


def test_apply_with_nothing_to_move_creates_no_batch(tmp_path):
    projects = tmp_path / "projects"
    _file(projects / "demo" / "renders" / "final.mp4")
    assert apply(scan(projects, tmp_path / "none"), {"depuracion"}, projects / "_papelera") is None
    assert not (projects / "_papelera").exists()
