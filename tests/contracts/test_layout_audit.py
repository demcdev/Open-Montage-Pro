"""Layout findings must reach a verdict the render path obeys.

The browser side is covered by tests/qa/test_layout_audit.py. These tests pin the
rules in between: what lasts long enough to block, how HyperFrames reports map onto
the same rules, and that each render path stops on a block.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.analysis import layout_audit
from tools.analysis.layout_audit import (
    HYPERFRAMES_RULES,
    build_report,
    evaluate,
    hyperframes_samples,
    render_gate,
)
from tools.video.hyperframes_compose import HyperFramesCompose
from tools.video.video_compose import VideoCompose

OVERLAP = {"rule": "text_overlap", "text": "uno", "other": "dos", "box": [0, 0, 10, 10]}


def _samples(times: list[float], finding: dict) -> list[dict]:
    return [{"time": moment, "findings": [finding]} for moment in times]


@pytest.mark.parametrize(
    ("times", "severity"),
    [
        ([1.0], "warn"),
        ([1.0, 1.5], "warn"),
        ([1.0, 1.5, 2.0], "block"),
        ([1.0, 1.5, 2.0, 2.5], "block"),
    ],
)
def test_only_lasting_problems_block(times, severity):
    assert [f["severity"] for f in evaluate(_samples(times, OVERLAP), 0.5)] == [severity]


def test_gaps_split_a_problem_in_two():
    findings = evaluate(_samples([1.0, 1.5, 5.0, 5.5], OVERLAP), 0.5)
    assert [(f["start"], f["end"]) for f in findings] == [(1.0, 1.5), (5.0, 5.5)]
    assert {f["severity"] for f in findings} == {"warn"}


def test_graphics_leaving_the_canvas_never_block():
    finding = {"rule": "graphic_off_canvas", "text": "svg"}
    assert evaluate(_samples([0, 1, 2, 3, 4], finding), 1.0)[0]["severity"] == "warn"


def test_different_texts_stay_separate_findings():
    other = {**OVERLAP, "text": "tres"}
    samples = [{"time": 0, "findings": [OVERLAP, other]}]
    assert len(evaluate(samples, 0.5)) == 2


def test_clean_run_passes():
    report = build_report("remotion", [{"time": 0, "findings": []}], 0.5, 1, 1)
    assert (report["verdict"], report["exit_code"]) == ("pass", 0)


def test_block_verdict_uses_the_technical_qc_scale():
    report = build_report("remotion", _samples([0, 1, 2], OVERLAP), 1.0, 3, 3)
    assert (report["verdict"], report["exit_code"], report["counts"]["block"]) == ("block", 1, 1)


@pytest.mark.parametrize(("code", "rule"), HYPERFRAMES_RULES.items())
def test_hyperframes_codes_map_onto_the_rules(code, rule):
    samples = hyperframes_samples([{"code": code, "time": 2.0, "text": "uno", "rect": {"left": 1, "top": 2, "right": 3, "bottom": 4}}])
    assert samples[0]["time"] == 2.0
    assert samples[0]["findings"][0]["rule"] == rule
    assert samples[0]["findings"][0]["box"] == [1, 2, 3, 4]


def test_unknown_hyperframes_codes_warn_instead_of_blocking():
    findings = [{"code": "escaped_container", "time": moment, "selector": "#x"} for moment in (0, 1, 2, 3)]
    assert evaluate(hyperframes_samples(findings), 1.0)[0]["severity"] == "warn"


@pytest.mark.parametrize(
    "report",
    [
        {"browserSkipped": True, "layout": {"samples": [], "findings": []}, "runtime": {"findings": [{"message": "no browser"}]}},
        {"browserSkipped": False, "layout": {"samples": [], "findings": []}},
        {},
    ],
)
def test_a_hyperframes_check_that_measured_nothing_is_not_a_pass(monkeypatch, tmp_path, report):
    (tmp_path / "index.html").write_text('<div data-composition-id="main" data-duration="4"></div>', encoding="utf-8")
    monkeypatch.setattr(HyperFramesCompose, "execute", lambda self, inputs: _Result(False, {"report": report}))
    result = layout_audit.LayoutAudit().execute({"engine": "hyperframes", "workspace_path": str(tmp_path)})
    assert not result.success and "measured no samples" in result.error


def test_a_stale_browser_path_is_not_passed_to_hyperframes(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setenv("HYPERFRAMES_BROWSER_PATH", str(tmp_path / "missing.exe"))
    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: seen.update(kwargs["env"]))
    HyperFramesCompose()._run_hf(["check"], cwd=None, timeout=5, check=False)
    assert seen and "HYPERFRAMES_BROWSER_PATH" not in seen


class _Result:
    def __init__(self, success, data=None, error=None):
        self.success, self.data, self.error = success, data or {}, error


@pytest.fixture
def real_gate(monkeypatch):
    """Undo the session stub so this module tests the real gate."""
    monkeypatch.setattr(layout_audit, "render_gate", render_gate)


def test_gate_stops_on_block(monkeypatch, real_gate, tmp_path):
    report = build_report("remotion", _samples([0, 1, 2], OVERLAP), 1.0, 3, 3)
    monkeypatch.setattr(layout_audit.LayoutAudit, "execute", lambda self, inputs: _Result(True, report))
    error = render_gate({}, tmp_path / "video.mp4")
    assert "text_overlap" in error and "uno" in error and "video.layout.json" in error


def test_gate_lets_warnings_through(monkeypatch, real_gate, tmp_path):
    report = build_report("remotion", _samples([0], OVERLAP), 1.0, 1, 1)
    monkeypatch.setattr(layout_audit.LayoutAudit, "execute", lambda self, inputs: _Result(True, report))
    assert render_gate({}, tmp_path / "video.mp4") is None


def test_a_failed_audit_leaves_no_report(monkeypatch, real_gate, tmp_path):
    stale = tmp_path / "video.layout.json"
    stale.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(layout_audit.LayoutAudit, "execute", lambda self, inputs: _Result(False, error="no chrome"))
    assert render_gate({}, tmp_path / "video.mp4") is None
    assert not stale.exists()


def test_gate_can_be_skipped_for_drafts(monkeypatch, real_gate, tmp_path):
    monkeypatch.setattr(layout_audit.LayoutAudit, "execute", lambda self, inputs: pytest.fail("audit ran"))
    assert render_gate({}, tmp_path / "video.mp4", skip=True) is None


def test_gate_writes_next_to_the_master(monkeypatch, real_gate, tmp_path):
    seen = {}
    report = build_report("remotion", [], 0.5, 1, 1)

    def execute(self, inputs):
        seen.update(inputs)
        return _Result(True, report)

    monkeypatch.setattr(layout_audit.LayoutAudit, "execute", execute)
    render_gate({"engine": "remotion"}, tmp_path / "video.mp4")
    assert Path(seen["report_path"]) == tmp_path / "video.layout.json"


@pytest.mark.parametrize("tool", [VideoCompose, HyperFramesCompose])
def test_render_tools_declare_the_draft_switch(tool):
    assert "skip_layout_audit" in tool.input_schema["properties"]


def test_every_render_path_goes_through_the_gate():
    compose = Path("tools/video/video_compose.py").read_text(encoding="utf-8")
    hyperframes = Path("tools/video/hyperframes_compose.py").read_text(encoding="utf-8")
    assert compose.count("layout_error = render_gate(") == 2
    assert hyperframes.count("layout_error = self._layout_gate(") == 2


def test_the_audit_can_measure_compositions_with_video():
    script = Path("remotion-composer/scripts/layout-audit.mjs").read_text(encoding="utf-8")
    assert 'imageFormat: "jpeg"' in script


def test_probe_rules_are_the_ones_the_audit_blocks_on():
    probe = Path("remotion-composer/scripts/layout-probe.js").read_text(encoding="utf-8")
    assert all(f'rule: "{rule}"' in probe for rule in layout_audit.BLOCKING_RULES)
