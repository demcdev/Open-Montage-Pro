"""Problems should surface before the render, and leave a record at the final review.

Each previewable moment gets a packet for cold-viewer and a verdict in artifacts/.
Measured facts win here too: a clip tagged as AI cannot pass on opinion.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.pipeline_loader import load_pipeline
from tools.analysis import cold_review
from tools.analysis.cold_review import (
    CRITERIA,
    MAX_PREVIEW_PASSES,
    NARRATIVE_PIPELINES,
    ColdReview,
    is_ai_tagged,
    preview_verdict,
    script_problems,
    spoken_seconds,
)
from tools.analysis.technical_qc import file_sha256
from tools.video.hyperframes_compose import HyperFramesCompose

ROOT = Path(__file__).resolve().parent.parent.parent
LINE = {"scene_id": "s1", "narration": "El volcán explota.", "visual": "Lava tranquila", "on_screen": "1815"}
FINDING = {"scene_id": "s1", "problem": "La lava está tranquila.", "proposed_fix": "Usar una columna de ceniza."}
needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def preview(project: Path, **inputs):
    return ColdReview().execute({"operation": "preview", "project_dir": str(project), **inputs})


def record(project: Path, stage: str = "plan", **inputs):
    return ColdReview().execute({"operation": "record_preview", "project_dir": str(project), "stage": stage, **inputs})


@pytest.fixture
def clip(tmp_path) -> Path:
    path = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x180:rate=10", str(path)],
        check=True,
    )
    return path


def test_the_plan_packet_holds_only_what_the_viewer_needs(tmp_path):
    result = preview(tmp_path, stage="plan", lines=[LINE], brief={"promise": "p"})
    assert result.success, result.error
    packet = json.loads(Path(result.data["packet_path"]).read_text(encoding="utf-8"))
    assert packet["stage"] == "plan" and packet["lines"] == [LINE]
    assert set(packet) == {"stage", "brief", "lines", "approved_decisions", "earlier_findings"}
    assert Path(result.data["packet_path"]).parent.name == "preview_plan"


def test_an_empty_plan_is_refused(tmp_path):
    assert not preview(tmp_path, stage="plan", lines=[]).success


def test_an_unknown_stage_is_refused(tmp_path):
    assert not preview(tmp_path, stage="sound").success


@needs_ffmpeg
def test_clips_become_contact_sheets(tmp_path, clip):
    clips = [{"id": "a", "path": str(clip), "scene_id": "s1", "narration": "x", "tags": "lava"}]
    result = preview(tmp_path, stage="clips", clips=clips)
    assert result.success, result.error
    folder = Path(result.data["packet_path"]).parent
    packet = json.loads(Path(result.data["packet_path"]).read_text(encoding="utf-8"))
    assert (folder / packet["clips"][0]["sheet"]).is_file()
    assert "path" not in packet["clips"][0]
    assert packet["ai_tagged"] == []


def test_a_missing_clip_fails(tmp_path):
    assert not preview(tmp_path, stage="clips", clips=[{"id": "a", "path": str(tmp_path / "no.mp4")}]).success


@pytest.mark.parametrize(
    ("tags", "expected"),
    [("ai generated, lava", True), ("AI-Generated", True), ("lava, smoke", False), ("", False), ("mountain, rain", False)],
)
def test_ai_tags_are_read(tags, expected):
    assert is_ai_tagged(tags) is expected


@needs_ffmpeg
def test_a_clip_tagged_as_ai_cannot_pass(tmp_path, clip):
    clips = [{"id": "a", "path": str(clip), "tags": "ai generated"}]
    assert preview(tmp_path, stage="clips", clips=clips).data["ai_tagged"] == ["a"]
    result = record(tmp_path, "clips", verdict="go")
    assert result.data["verdict"] == "fix"
    assert any("a" in finding["problem"] for finding in result.data["findings"])


def test_frames_are_asked_of_the_engine_at_each_scene(tmp_path, monkeypatch):
    seen = {}

    def render(self, inputs, times, out_dir):
        seen["times"] = times
        (out_dir / "frame_00001.00.jpg").write_bytes(b"x")
        return [{"time": 1.0, "file": "frame_00001.00.jpg"}]

    monkeypatch.setattr(ColdReview, "_render_preview_frames", render)
    result = preview(tmp_path, stage="frames", engine="remotion", scenes=[{"id": "s1", "start": 0, "end": 10}])
    assert result.success, result.error
    assert seen["times"] == [1.0, 3.5, 9.65]
    packet = json.loads(Path(result.data["packet_path"]).read_text(encoding="utf-8"))
    assert packet["frames"] == [{"time": 1.0, "file": "frame_00001.00.jpg"}]


def test_frames_need_scenes(tmp_path):
    assert not preview(tmp_path, stage="frames", engine="remotion").success


def test_hyperframes_snapshots_are_taken_at_the_chosen_times(tmp_path, monkeypatch):
    calls = []

    def run(self, args, *, cwd, timeout, check):
        calls.append(args)
        for index in range(2):
            (tmp_path / "out" / f"frame-0{index}.png").write_bytes(b"x")
        return subprocess.CompletedProcess(args, 0, "", "")

    (tmp_path / "out").mkdir()
    monkeypatch.setattr(HyperFramesCompose, "_run_hf", run)
    frames = ColdReview()._render_preview_frames({"engine": "hyperframes", "workspace_path": str(tmp_path)}, [1.0, 2.5], tmp_path / "out")
    assert calls[0][:3] == ["snapshot", "--at", "1.0,2.5"] and "--no-end" in calls[0]
    assert [frame["time"] for frame in frames] == [1.0, 2.5]


@pytest.mark.parametrize(
    ("verdict", "pass_number", "expected"),
    [("go", 1, "go"), ("fix", 1, "fix"), ("go", 2, "go"), ("fix", MAX_PREVIEW_PASSES, "escalate")],
)
def test_preview_verdicts(verdict, pass_number, expected):
    assert preview_verdict(verdict, pass_number) == expected


def test_a_recorded_preview_lands_in_artifacts(tmp_path):
    result = record(tmp_path, verdict="fix", findings=[FINDING])
    assert result.success, result.error
    written = json.loads((tmp_path / "artifacts" / "preview_plan.json").read_text(encoding="utf-8"))
    assert written["verdict"] == "fix" and written["findings"] == [FINDING]


def test_fix_needs_something_to_fix(tmp_path):
    result = record(tmp_path, verdict="fix", findings=[])
    assert not result.success and "findings" in result.error


def test_there_is_no_third_pass(tmp_path):
    result = record(tmp_path, verdict="go", pass_number=MAX_PREVIEW_PASSES + 1)
    assert not result.success and "pass_number" in result.error


def test_the_final_review_says_which_previews_ran(tmp_path):
    record(tmp_path, verdict="go")
    video = tmp_path / "final.mp4"
    video.write_bytes(b"master")
    folder = cold_review.packet_dir(video)
    folder.mkdir()
    packet = {"has_narration": False, "layout": {"verdict": "pass"}, "input_sha256": file_sha256(video)}
    (folder / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
    scores = {name: {"score": 4, "evidence": "0:01"} for name in CRITERIA if name != "voice"}
    result = ColdReview().execute(
        {"operation": "record", "video_path": str(video), "scores": scores, "project_dir": str(tmp_path)}
    )
    assert result.data["previews"] == {"script": "missing", "plan": "go", "clips": "missing", "frames": "missing"}


HOOKS = ["Un verano no llegó.", "¿Quién robó el verano?", "Nevó en junio."]
SCRIPT = " ".join(["palabra"] * 75)
MAP = [{"second": 0, "reason": "a"}, {"second": 6, "reason": "b"}, {"second": 12, "reason": "c"}, {"second": 18, "reason": "d"}, {"second": 24, "reason": "e"}]


def test_speech_time_comes_from_the_word_count():
    assert spoken_seconds(SCRIPT) == 30.0


def test_a_sound_script_has_no_measured_problems():
    assert script_problems(SCRIPT, HOOKS, MAP, 30) == []


def test_openings_must_be_compared():
    assert any("openings" in problem for problem in script_problems(SCRIPT, HOOKS[:2], MAP, 30))


def test_a_long_opening_is_flagged():
    long_hook = " ".join(["palabra"] * 15)
    assert any("Opening takes" in problem for problem in script_problems(SCRIPT, [*HOOKS, long_hook], MAP, 30))


@pytest.mark.parametrize("hook", ["Hola a todos, hoy veremos algo.", "En este video verás todo.", "Welcome back."])
def test_generic_openings_are_flagged(hook):
    assert any("Generic" in problem for problem in script_problems(SCRIPT, [*HOOKS, hook], MAP, 30))


def test_an_overlong_script_is_flagged():
    assert any("target" in problem for problem in script_problems(SCRIPT, HOOKS, MAP, 20))


def test_a_stretch_without_a_reason_to_stay_is_flagged():
    problems = script_problems(SCRIPT, HOOKS, [{"second": 0, "reason": "a"}, {"second": 22, "reason": "b"}], 30)
    assert any("from 0.0 to 22.0" in problem for problem in problems)


def test_measured_problems_overrule_the_viewer(tmp_path):
    prepared = preview(tmp_path, stage="script", script_text=SCRIPT, hooks=HOOKS[:1], retention_map=MAP, target_seconds=30)
    assert prepared.data["measured_problems"]
    result = record(tmp_path, "script", verdict="go")
    assert result.data["verdict"] == "fix" and result.data["findings"]


def test_the_chosen_opening_is_kept(tmp_path):
    preview(tmp_path, stage="script", script_text=SCRIPT, hooks=HOOKS, retention_map=MAP, target_seconds=30)
    result = record(tmp_path, "script", verdict="go", best_hook=HOOKS[2])
    assert result.data["verdict"] == "go" and result.data["best_hook"] == HOOKS[2]


def test_a_script_is_needed(tmp_path):
    assert not preview(tmp_path, stage="script", hooks=HOOKS).success


def test_the_viewer_knows_each_moment():
    agent = (ROOT / ".claude" / "agents" / "cold-viewer.md").read_text(encoding="utf-8")
    assert all(f"`{stage}`" in agent for stage in cold_review.PREVIEW_STAGES)
    assert '"verdict"' in agent
    assert agent.index("do not give scores") < agent.index("1. Read `skills/meta/cold-review.md`")


@pytest.mark.parametrize("pipeline", sorted(NARRATIVE_PIPELINES))
def test_narrative_pipelines_review_before_rendering(pipeline):
    manifest = load_pipeline(pipeline)
    assert "meta/pre-render-review" in manifest["required_skills"]
    stages = {stage["name"]: stage for stage in manifest["stages"]}
    for name in ("script", "scene_plan", "assets", "compose"):
        assert "cold_review" in stages[name]["tools_available"], name
        text = (ROOT / "skills" / f"{stages[name]['skill']}.md").read_text(encoding="utf-8")
        assert "<!-- pre-render-review -->" in text, name
