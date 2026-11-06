"""The probe must find planted layout mistakes in a real browser and spare look-alikes.

Renders remotion-composer/scripts/layout-fixture.tsx through the real audit. It needs
Node and the composer's node_modules, and takes about 30 seconds.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tools.analysis.layout_audit import COMPOSER_DIR, LayoutAudit

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (COMPOSER_DIR / "node_modules").exists(),
    reason="needs Node and remotion-composer/node_modules",
)


@pytest.fixture(scope="module")
def report(tmp_path_factory) -> dict:
    result = LayoutAudit().execute(
        {
            "engine": "remotion",
            "entry": str(COMPOSER_DIR / "scripts" / "layout-fixture.tsx"),
            "composition_id": "LayoutFixture",
            "every_seconds": 1,
            "report_path": str(tmp_path_factory.mktemp("layout") / "fixture.layout.json"),
        }
    )
    assert result.success, result.error
    return result.data


def test_every_sample_was_measured(report):
    assert report["samples_checked"] == report["samples_expected"] == 3


def test_planted_mistakes_are_found_and_block(report):
    found = {(f["rule"], f["text"], f["severity"]) for f in report["findings"]}
    assert found == {
        ("text_off_canvas", "fuera del lienzo", "block"),
        ("text_cut_off", "texto recortado por su caja", "block"),
        ("text_overlap", "primer titulo", "block"),
        ("text_covered", "tapado por grafico", "block"),
        ("graphic_off_canvas", "svg", "warn"),
    }


def test_look_alikes_are_left_alone(report):
    reported = {f["text"] for f in report["findings"]} | {f.get("other", "") for f in report["findings"]}
    assert not reported & {
        "con sombra",
        "texto visible",
        "texto oculto",
        "encimado adrede uno",
        "encimado adrede dos",
        "sale adrede del lienzo",
        "ignorado por completo",
        "sobre tarjeta",
    }


def test_verdict_and_report_file(report):
    assert report["verdict"] == "block"
    assert Path(report["report_path"]).exists()
