"""Cold review must come from what reaches the viewer and hold at delivery.

The reviewer cannot hear or see motion, so measured reports overrule its scores, and
export_bundle must refuse a narrative master without a current review of those bytes.
These tests pin both, along with the wiring across manifests and directors.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.pipeline_loader import list_pipelines, load_pipeline
from schemas.artifacts import validate_artifact
from tools.analysis import cold_review
from tools.analysis.cold_review import CRITERIA, NARRATIVE_PIPELINES, ColdReview, evaluate, frame_times, measured_caps
from tools.analysis.technical_qc import file_sha256
from tools.publishers.export_bundle import ExportBundle
from tools.tool_registry import registry

ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN = {"has_narration": True, "narration": {"verdict": "pass"}, "layout": {"verdict": "pass"}}


def scores(value: int = 4, **overrides: int) -> dict:
    return {name: {"score": overrides.get(name, value), "evidence": "0:01"} for name in CRITERIA}


def _skill(pipeline: str, stage_name: str) -> Path:
    stage = next(s for s in load_pipeline(pipeline)["stages"] if s["name"] == stage_name)
    return ROOT / "skills" / f"{stage['skill']}.md"


def test_good_scores_pass():
    assert evaluate(scores(), CLEAN, 1)[0] == "pass"


def test_a_failed_criterion_asks_for_a_second_round():
    verdict, _, failed = evaluate(scores(hook=2), CLEAN, 1)
    assert (verdict, failed) == ("revise", ["hook"])


def test_after_three_rounds_the_user_decides():
    assert evaluate(scores(hook=2), CLEAN, 2)[0] == "revise"
    assert evaluate(scores(hook=2), CLEAN, 3)[0] == "escalate"


def test_three_is_enough():
    assert evaluate(scores(3), CLEAN, 1)[0] == "pass"


@pytest.mark.parametrize(
    ("packet", "criterion"),
    [
        ({**CLEAN, "layout": None}, "layout"),
        ({**CLEAN, "layout": {"verdict": "block"}}, "layout"),
        ({**CLEAN, "narration": None}, "voice"),
        ({**CLEAN, "narration": {"verdict": "review"}}, "voice"),
    ],
)
def test_measured_reports_overrule_the_score(packet, criterion):
    verdict, final, failed = evaluate(scores(5), packet, 1)
    assert verdict == "revise" and failed == [criterion]
    assert final[criterion]["score"] == 1 and final[criterion]["capped_by"]


def test_warnings_in_the_layout_report_do_not_cap():
    assert measured_caps({**CLEAN, "layout": {"verdict": "warn"}}) == {}


def test_voice_does_not_apply_without_narration():
    packet = {"has_narration": False, "narration": None, "layout": {"verdict": "pass"}}
    verdict, final, _ = evaluate({k: v for k, v in scores().items() if k != "voice"}, packet, 1)
    assert verdict == "pass" and final["voice"]["score"] is None


@pytest.mark.parametrize("bad", [0, 6, "4", None])
def test_scores_must_be_on_the_scale(bad):
    with pytest.raises(ValueError, match="hook"):
        evaluate({**scores(), "hook": {"score": bad, "evidence": "0:01"}}, CLEAN, 1)


def test_every_score_needs_evidence():
    with pytest.raises(ValueError, match="evidence"):
        evaluate({**scores(), "hook": {"score": 4, "evidence": " "}}, CLEAN, 1)


def test_frames_cover_the_hook_each_scene_and_flagged_moments():
    scenes = [{"start": 0, "end": 10}, {"start": 10, "end": 20}]
    layout = {"findings": [{"start": 13.0}]}
    assert frame_times(20, scenes, layout) == [1.0, 3.5, 9.65, 13.0, 13.5, 19.65]


def test_cues_add_exact_moments():
    assert 12.25 in frame_times(20, [{"start": 0, "end": 20}], None, [12.25])


def test_a_short_scene_keeps_its_last_frame_inside_it():
    times = frame_times(10, [{"start": 4, "end": 5}], None)
    assert 4.75 in times


def test_frames_stay_capped_and_keep_every_flagged_moment():
    scenes = [{"start": index, "end": index + 1} for index in range(100)]
    times = frame_times(100, scenes, {"findings": [{"start": 50.5}]})
    assert len(times) <= cold_review.MAX_FRAMES and 50.5 in times


def test_a_video_without_scenes_is_sampled_evenly():
    times = frame_times(60, [], None)
    assert 10 <= len(times) <= cold_review.MAX_FRAMES and times[-1] > 50


@pytest.fixture
def video(tmp_path) -> Path:
    path = tmp_path / "final.mp4"
    path.write_bytes(b"master")
    return path


@pytest.fixture
def prepared(video) -> Path:
    folder = cold_review.packet_dir(video)
    folder.mkdir()
    packet = {**CLEAN, "input_sha256": file_sha256(video)}
    (folder / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
    return video


def test_record_ties_the_verdict_to_the_bytes(prepared):
    result = ColdReview().execute({"operation": "record", "video_path": str(prepared), "scores": scores()})
    assert result.success and result.data["verdict"] == "pass"
    written = json.loads(cold_review.cold_path(prepared).read_text(encoding="utf-8"))
    assert written["input_sha256"] == file_sha256(prepared)


def test_record_refuses_a_video_that_changed_after_prepare(prepared):
    prepared.write_bytes(b"other")
    result = ColdReview().execute({"operation": "record", "video_path": str(prepared), "scores": scores()})
    assert not result.success and "changed" in result.error


def test_record_needs_a_packet(video):
    assert not ColdReview().execute({"operation": "record", "video_path": str(video), "scores": scores()}).success


def test_there_is_no_fourth_round(prepared):
    result = ColdReview().execute({"operation": "record", "video_path": str(prepared), "scores": scores(), "round": 4})
    assert not result.success and "round" in result.error


def _approve_qc(video: Path) -> None:
    report = {"input_sha256": file_sha256(video), "verdict": "pass", "profile": "youtube", "findings": []}
    video.with_suffix(".qc.json").write_text(json.dumps(report), encoding="utf-8")


def _review(video: Path, verdict: str, sha: str | None = None) -> None:
    report = {"input_sha256": sha or file_sha256(video), "verdict": verdict, "failed_criteria": ["hook"]}
    cold_review.cold_path(video).write_text(json.dumps(report), encoding="utf-8")


def _decide(project: Path) -> None:
    decision = {"subject": "Apertura", "selected": "Imagina esto", "reason": "Aprobada por el usuario"}
    (project / "decision_log.json").write_text(json.dumps({"decisions": [decision]}), encoding="utf-8")


def _export(video: Path, tmp_path: Path, **extra):
    _approve_qc(video)
    _decide(video.parent)
    inputs = {"video_path": str(video), "title": "t", "export_dir": str(tmp_path / "out"), "pipeline": "cinematic"}
    return ExportBundle().execute({**inputs, **extra})


def test_export_refuses_a_narrative_master_without_review(video, tmp_path):
    result = _export(video, tmp_path)
    assert not result.success and "cold review" in result.error.lower()


def test_export_refuses_a_review_of_other_bytes(video, tmp_path):
    _review(video, "pass", sha="0" * 64)
    result = _export(video, tmp_path)
    assert not result.success and "does not match" in result.error


def test_export_refuses_revise(video, tmp_path):
    _review(video, "revise")
    result = _export(video, tmp_path)
    assert not result.success and "hook" in result.error


def test_export_passes_a_current_review(video, tmp_path):
    _review(video, "pass")
    result = _export(video, tmp_path)
    assert result.success, result.error
    assert result.data["publish_log"]["entries"][0]["cold_review"]["verdict"] == "pass"
    validate_artifact("publish_log", result.data["publish_log"])


def test_escalate_needs_the_users_decision(video, tmp_path):
    _review(video, "escalate")
    assert not _export(video, tmp_path).success
    exception = {"reason": "lo acepto", "decision_id": "d-9"}
    result = _export(video, tmp_path, cold_exception=exception)
    assert result.success, result.error
    assert result.data["publish_log"]["entries"][0]["cold_review"]["exception"] == exception


def test_other_pipelines_export_without_review(video, tmp_path):
    result = _export(video, tmp_path, pipeline="talking-head")
    assert result.success, result.error
    assert "cold_review" not in result.data["publish_log"]["entries"][0]


def test_narrative_set_matches_real_pipelines():
    assert NARRATIVE_PIPELINES <= set(list_pipelines())


@pytest.mark.parametrize("pipeline", sorted(NARRATIVE_PIPELINES))
def test_narrative_pipelines_require_the_review(pipeline):
    manifest = load_pipeline(pipeline)
    compose = next(s for s in manifest["stages"] if s["name"] == "compose")
    assert "cold_review" in compose["required_tools"] and "cold_review" in compose["tools_available"]
    assert "meta/cold-review" in manifest["required_skills"]
    assert "<!-- cold-review-gate -->" in _skill(pipeline, "compose").read_text(encoding="utf-8")
    assert "<!-- cold-review-export -->" in _skill(pipeline, "publish").read_text(encoding="utf-8")


@pytest.mark.parametrize("pipeline", [name for name in list_pipelines() if name != "framework-smoke"])
def test_every_pipeline_knows_the_layout_gate(pipeline):
    assert "meta/layout-audit" in load_pipeline(pipeline)["required_skills"]
    assert "<!-- layout-audit-gate -->" in _skill(pipeline, "compose").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "pipeline",
    [
        name
        for name in list_pipelines()
        if any(
            stage["name"] == "assets" and "tts_selector" in (stage.get("tools_available") or [])
            for stage in load_pipeline(name)["stages"]
        )
    ],
)
def test_narrated_pipelines_check_their_narration(pipeline):
    manifest = load_pipeline(pipeline)
    assets = next(s for s in manifest["stages"] if s["name"] == "assets")
    assert "narration_qc" in assets["tools_available"]
    assert "meta/narration-qc" in manifest["required_skills"]
    assert "<!-- narration-qc-gate -->" in _skill(pipeline, "assets").read_text(encoding="utf-8")


def test_new_tools_are_registered():
    registry.discover()
    assert {"cold_review", "layout_audit", "narration_qc"} <= set(registry._tools)


def test_the_viewer_gets_no_other_tools():
    agent = (ROOT / ".claude" / "agents" / "cold-viewer.md").read_text(encoding="utf-8")
    assert "\ntools: Read\n" in agent


def test_the_viewer_never_asks_for_words_on_screen():
    agent = (ROOT / ".claude" / "agents" / "cold-viewer.md").read_text(encoding="utf-8")
    skill = (ROOT / "skills" / "meta" / "cold-review.md").read_text(encoding="utf-8")
    assert "no words on screen" in agent and "no fix may add words on screen" in agent
    assert "No-Text Rule" in skill


def test_exception_categories_exist_in_the_decision_log():
    schema = json.loads((ROOT / "schemas" / "artifacts" / "decision_log.schema.json").read_text(encoding="utf-8"))
    categories = schema["properties"]["decisions"]["items"]["properties"]["category"]["enum"]
    assert {"voice_language", "qc_exception", "cold_exception"} <= set(categories)


def test_a_narrative_export_needs_decisions(prepared, tmp_path):
    _approve_qc(prepared)
    _review(prepared, "pass")
    inputs = {"video_path": str(prepared), "title": "t", "export_dir": str(tmp_path / "out"), "pipeline": "cinematic"}
    result = ExportBundle().execute(inputs)
    assert not result.success and "decision_log" in result.error


def test_reviewers_receive_decisions_and_earlier_findings(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _decide(artifacts)
    finding = {"scene_id": "s1", "problem": "El pez no se ve", "proposed_fix": "Mostrarlo"}
    (artifacts / "preview_plan.json").write_text(json.dumps({"findings": [finding]}), encoding="utf-8")
    assert cold_review.approved_decisions(tmp_path)[0]["selected"] == "Imagina esto"
    earlier = cold_review.earlier_findings(tmp_path, cold_review.PREVIEW_STAGES)
    assert earlier == [{"source": "plan", "problem": "El pez no se ve", "proposed_fix": "Mostrarlo"}]


def test_a_project_without_a_log_has_no_decisions(tmp_path):
    assert cold_review.approved_decisions(tmp_path) == []
    assert cold_review.approved_decisions(None) == []
