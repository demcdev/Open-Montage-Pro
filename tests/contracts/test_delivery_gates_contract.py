"""Mastering and technical QC are required steps, not options.

`skills/core/loudness-mastering.md` and `skills/meta/technical-qc-gate.md` say
every delivery goes through `audio_master` and `technical_qc`, and `export_bundle`
refuses a master without a current report. That only holds if every production
pipeline routes its delivery through those tools, so this contract pins the
manifests, the publish directors and the artifact schemas to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.pipeline_loader import list_pipelines, load_pipeline
from schemas.artifacts import validate_artifact

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINES = sorted(name for name in list_pipelines() if name != "framework-smoke")
# Manifest name -> skills/pipelines/<folder>, where the two differ.
DIRECTOR_FOLDER = {"animated-explainer": "explainer"}


def _stage(pipeline: str, name: str) -> dict:
    manifest = load_pipeline(pipeline)
    return next(stage for stage in manifest["stages"] if stage["name"] == name)


def test_every_production_pipeline_is_covered():
    assert len(PIPELINES) == 12


@pytest.mark.parametrize("pipeline", PIPELINES)
def test_compose_requires_mastering_and_qc(pipeline):
    stage = _stage(pipeline, "compose")
    gate = {"audio_master", "technical_qc"}
    assert gate <= set(stage["required_tools"])
    assert gate <= set(stage["tools_available"])
    assert not gate & set(stage.get("optional_tools") or [])
    criteria = " ".join(stage["success_criteria"])
    assert "audio_master" in criteria and "technical_qc" in criteria


@pytest.mark.parametrize("pipeline", PIPELINES)
def test_publish_requires_the_export_gate(pipeline):
    stage = _stage(pipeline, "publish")
    gate = {"technical_qc", "export_bundle"}
    assert gate <= set(stage["required_tools"])
    assert gate <= set(stage["tools_available"])
    assert not gate & set(stage.get("optional_tools") or [])
    assert any("export_bundle" in c for c in stage["success_criteria"])


@pytest.mark.parametrize("pipeline", PIPELINES)
def test_publish_director_routes_delivery_through_the_gate(pipeline):
    folder = DIRECTOR_FOLDER.get(pipeline, pipeline)
    text = (ROOT / "skills" / "pipelines" / folder / "publish-director.md").read_text(encoding="utf-8")
    assert "<!-- export-bundle-gate -->" in text
    assert "qc_exception" in text


def test_render_report_carries_mastering_and_qc():
    validate_artifact(
        "render_report",
        {
            "version": "1.0",
            "outputs": [
                {
                    "path": "renders/final.mp4",
                    "format": "mp4",
                    "resolution": "1920x1080",
                    "duration_seconds": 30.0,
                    "mastering": {"preset": "youtube", "verification_passed": True, "linear_mode": True},
                    "qc": {
                        "verdict": "pass",
                        "profile": "youtube",
                        "report_path": "renders/final.qc.json",
                        "integrated_lufs": -14.0,
                        "true_peak_dbtp": -1.2,
                    },
                }
            ],
        },
    )
