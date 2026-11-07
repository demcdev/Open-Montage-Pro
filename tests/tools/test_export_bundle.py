"""Tests for the export_bundle publisher tool.

Covers the tool contract, registry discovery, the export bundle layout, a
schema-valid publish_log, chapter formatting, the missing-video error path, and
the technical_qc delivery gate.
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.analysis.technical_qc import file_sha256
from tools.publishers.export_bundle import ExportBundle
from tools.base_tool import ToolStatus, ToolTier
from tools.tool_registry import ToolRegistry
from schemas.artifacts import validate_artifact


def _write_qc(video: Path, verdict: str = "pass", findings: list | None = None) -> Path:
    report = video.with_suffix(".qc.json")
    report.write_text(
        json.dumps(
            {
                "input": str(video),
                "input_sha256": file_sha256(video),
                "profile": "youtube",
                "verdict": verdict,
                "findings": findings or [],
            }
        ),
        encoding="utf-8",
    )
    return report


def _make_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42fakevideo")
    _write_qc(path)


def test_contract_metadata():
    tool = ExportBundle()
    info = tool.get_info()
    assert info["name"] == "export_bundle"
    assert info["capability"] == "publish"
    assert info["tier"] == ToolTier.PUBLISH.value
    assert info["provider"] == "local"
    assert info["resource_profile"]["network_required"] is False
    assert tool.get_status() == ToolStatus.AVAILABLE
    assert tool.estimate_cost({}) == 0.0


def test_missing_video_errors(tmp_path):
    result = ExportBundle().execute(
        {"pipeline": "clip-factory", "video_path": str(tmp_path / "nope.mp4"), "title": "X"}
    )
    assert result.success is False
    assert "not found" in (result.error or "")


def test_export_bundle_layout_and_publish_log(tmp_path):
    video = tmp_path / "projects" / "demo" / "renders" / "final.mp4"
    _make_video(video)
    subs = tmp_path / "subs.srt"
    subs.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n", encoding="utf-8")

    result = ExportBundle().execute(
        {
            "pipeline": "clip-factory", "video_path": str(video),
            "title": "Vector Databases Explained in 60 Seconds",
            "export_dir": str(tmp_path / "out"),
            "description": "A quick explainer.",
            "tags": ["vector db", "explainer"],
            "hashtags": ["#ai", "#database"],
            "chapters": [
                {"start_seconds": 0, "title": "Intro"},
                {"start_seconds": 75, "title": "How it works"},
            ],
            "subtitles_path": str(subs),
            "thumbnail_concept": {"text_overlay": "100x FASTER"},
            "platform": "youtube",
            "visibility": "unlisted",
            "timestamp": "2026-06-29T10:30:00+00:00",
        }
    )
    assert result.success is True
    root = Path(result.data["export_path"])

    # Layout
    assert (root / "video" / "output.mp4").is_file()
    assert (root / "video" / "subtitles.srt").is_file()
    assert (root / "metadata" / "metadata.json").is_file()
    assert (root / "metadata" / "description.txt").is_file()
    assert (root / "metadata" / "tags.txt").is_file()
    assert (root / "metadata" / "chapters.txt").is_file()
    assert (root / "thumbnails" / "concept.json").is_file()

    # tags one-per-line
    assert (root / "metadata" / "tags.txt").read_text().splitlines() == ["vector db", "explainer"]
    # chapter formatting (75s -> 1:15)
    assert "1:15 - How it works" in (root / "metadata" / "chapters.txt").read_text()

    # publish_log is schema-valid and shaped right
    plog = result.data["publish_log"]
    validate_artifact("publish_log", plog)
    entry = plog["entries"][0]
    assert entry["status"] == "exported"
    assert entry["platform"] == "youtube"
    assert entry["visibility"] == "unlisted"
    assert entry["export_path"] == str(root)
    assert entry["metadata_used"]["title"].startswith("Vector Databases")


def test_chapter_time_formatting_hours(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    result = ExportBundle().execute(
        {
            "pipeline": "clip-factory", "video_path": str(video),
            "title": "Long",
            "export_dir": str(tmp_path / "out"),
            "chapters": [{"time_seconds": 3725, "label": "Deep dive"}],  # 1:02:05
        }
    )
    assert result.success is True
    txt = (Path(result.data["export_path"]) / "metadata" / "chapters.txt").read_text()
    assert "1:02:05 - Deep dive" in txt


def test_infer_project_name(tmp_path):
    video = tmp_path / "projects" / "my-cool-video" / "renders" / "final.mp4"
    _make_video(video)
    result = ExportBundle().execute(
        {"pipeline": "clip-factory", "video_path": str(video), "title": "T", "export_dir": str(tmp_path / "out")}
    )
    # export still works; project name inference exercised via no-export_dir path below
    assert result.success is True


def test_missing_optional_asset_errors(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    for key in ("subtitles_path", "thumbnail_path"):
        result = ExportBundle().execute(
            {
                "pipeline": "clip-factory", "video_path": str(video),
                "title": "T",
                "export_dir": str(tmp_path / "out"),
                key: str(tmp_path / "does_not_exist.x"),
            }
        )
        assert result.success is False, key
        assert key in (result.error or "")


def test_default_export_dir_inside_project_workspace(tmp_path):
    # projects/<name>/renders/final.mp4 -> projects/<name>/exports (no export_dir given)
    video = tmp_path / "projects" / "demo" / "renders" / "final.mp4"
    _make_video(video)
    result = ExportBundle().execute({"pipeline": "clip-factory", "video_path": str(video), "title": "T"})
    assert result.success is True
    assert Path(result.data["export_path"]) == (tmp_path / "projects" / "demo" / "exports").resolve()


def _export(video: Path, tmp_path: Path, **extra):
    return ExportBundle().execute(
        {"pipeline": "clip-factory", "video_path": str(video), "title": "T", "export_dir": str(tmp_path / "out"), **extra}
    )


WARNING = [{"check": "freeze", "severity": "warn", "message": "Frozen picture 2.50s"}]
BLOCK = [{"check": "loudness", "severity": "block", "message": "Integrated -30.0 LUFS"}]


def test_pass_verdict_is_recorded_and_travels_with_the_master(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    result = _export(video, tmp_path)
    assert result.success is True
    plog = result.data["publish_log"]
    validate_artifact("publish_log", plog)
    qc = plog["entries"][0]["qc"]
    assert qc["verdict"] == "pass"
    assert qc["profile"] == "youtube"
    assert qc["report_path"] == str(video.with_suffix(".qc.json"))
    assert (tmp_path / "out" / "metadata" / "qc_report.json").is_file()


def test_export_refused_without_qc_report(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    video.with_suffix(".qc.json").unlink()
    result = _export(video, tmp_path)
    assert result.success is False
    assert "technical_qc" in (result.error or "")
    assert not (tmp_path / "out").exists()


def test_export_refused_when_master_changed_after_qc(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    video.write_bytes(video.read_bytes() + b"remastered")
    result = _export(video, tmp_path)
    assert result.success is False
    assert "changed" in (result.error or "")
    assert not (tmp_path / "out").exists()


def test_export_refused_for_report_of_another_file(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    other = tmp_path / "p" / "renders" / "other.mp4"
    _make_video(video)
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_bytes(b"different master")
    result = _export(video, tmp_path, qc_report_path=str(_write_qc(other)))
    assert result.success is False


def test_block_verdict_cannot_be_excepted(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    _write_qc(video, "block", BLOCK)
    result = _export(video, tmp_path, qc_exception={"reason": "ship it", "decision_id": "d-1"})
    assert result.success is False
    assert "-30.0 LUFS" in (result.error or "")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "exception",
    [None, {}, {"reason": "fine"}, {"decision_id": "d-1"}, {"reason": " ", "decision_id": "d-1"}],
)
def test_warn_verdict_needs_a_complete_exception(tmp_path, exception):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    _write_qc(video, "warn", WARNING)
    extra = {} if exception is None else {"qc_exception": exception}
    result = _export(video, tmp_path, **extra)
    assert result.success is False
    assert "Frozen picture" in (result.error or "")


def test_warn_verdict_ships_with_recorded_exception(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    _write_qc(video, "warn", WARNING)
    exception = {"reason": "Planned hold on the title card", "decision_id": "d-7"}
    result = _export(video, tmp_path, qc_exception=exception)
    assert result.success is True
    plog = result.data["publish_log"]
    validate_artifact("publish_log", plog)
    assert plog["entries"][0]["qc"]["verdict"] == "warn"
    assert plog["entries"][0]["qc"]["exception"] == exception


@pytest.mark.parametrize("content", ["not json", "[]", '{"verdict": "great"}'])
def test_unusable_report_is_refused(tmp_path, content):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    video.with_suffix(".qc.json").write_text(content, encoding="utf-8")
    assert _export(video, tmp_path).success is False


def test_report_without_verdict_is_refused(tmp_path):
    video = tmp_path / "p" / "renders" / "final.mp4"
    _make_video(video)
    report = video.with_suffix(".qc.json")
    report.write_text(
        json.dumps({"input_sha256": file_sha256(video), "verdict": "great"}), encoding="utf-8"
    )
    result = _export(video, tmp_path)
    assert result.success is False
    assert "verdict" in (result.error or "")


def test_registry_discovers_export_bundle():
    reg = ToolRegistry()
    reg.discover()
    assert reg.get("export_bundle") is not None
    assert reg.get_by_capability("publish")[0].name == "export_bundle"


def _bundle_inputs(tmp_path: Path, **extra) -> dict:
    video = tmp_path / "renders" / "final.mp4"
    _make_video(video)
    return {"video_path": str(video), "title": "t", "export_dir": str(tmp_path / "out"), **extra}


def test_export_refused_without_a_pipeline(tmp_path):
    result = ExportBundle().execute(_bundle_inputs(tmp_path))
    assert not result.success and "pipeline is required" in result.error


def test_export_refused_with_an_unknown_pipeline(tmp_path):
    result = ExportBundle().execute(_bundle_inputs(tmp_path, pipeline="nope"))
    assert not result.success and "Unknown pipeline" in result.error


def test_an_export_without_thumbnail_says_so(tmp_path):
    result = ExportBundle().execute(_bundle_inputs(tmp_path, pipeline="clip-factory"))
    assert result.data["publish_log"]["entries"][0]["warnings"] == ["No thumbnail in this export."]
