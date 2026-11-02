"""Contract tests for the Narrative DNA of the video reference analyst.

A reference video must be translated into the vocabulary of the script-writing
skills (hook, beats, open loops, cadence, narrator, pace, humor, ending) and stored
in `replication_guidance.narrative_dna` of the VideoAnalysisBrief, so the script
stage copies the retention pattern and not just the look.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from schemas.artifacts import validate_artifact  # noqa: E402

from tests.contracts.test_phase0_contracts import sample_artifact  # noqa: E402

ANALYST = ROOT / "skills" / "meta" / "video-reference-analyst.md"
CORE = ROOT / "skills" / "meta" / "guionista-core.md"
FIELDS = (
    "hook",
    "bridge",
    "stakes",
    "structure",
    "beats",
    "open_loops",
    "interruption_cadence_s",
    "narrator",
    "pace",
    "humor",
    "ending",
    "payoffs",
    "transformation",
    "what_to_keep",
    "what_to_change",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_analyst_defines_every_narrative_dna_field():
    text = _read(ANALYST)
    assert "### Narrative DNA (MANDATORY)" in text
    assert "replication_guidance.narrative_dna" in text
    for field in FIELDS:
        assert f"`{field}`" in text, f"the analyst does not define `{field}`"


def test_analyst_says_to_measure_and_not_to_copy():
    text = _read(ANALYST).lower()
    assert "measure, do not guess" in text
    assert "pattern, not copy" in text
    assert "inferred" in text


def test_analyst_feeds_the_creative_brief_and_the_script_stage():
    text = _read(ANALYST)
    assert "brief_creativo" in text and "skills/meta/creative-intake.md" in text
    assert "narrative_dna" in text and "skills/meta/guionista-core.md" in text


def test_script_core_reads_the_dna_as_a_pattern():
    core = _read(CORE)
    assert "narrative_dna" in core
    assert "video-reference-analyst.md" in core
    assert "patrón estructural" in core.lower()


def test_schema_accepts_narrative_dna_in_replication_guidance():
    brief = sample_artifact("video_analysis_brief")
    guidance = dict(brief.get("replication_guidance") or {})
    guidance["narrative_dna"] = {
        "hook": {"type": "result_first", "line": "…", "lands_at_s": 3},
        "beats": [{"t": 0, "beat": "hook", "function": "open the question"}],
        "open_loops": [{"opens_at": 12, "closes_at": 95, "question": "where is the edge?"}],
        "interruption_cadence_s": {"median": 18, "max": 40},
        "narrator": {"type": "single_narrator", "person": "second"},
        "pace": {"wpm": 140, "voice_share": 0.88, "longest_silence_s": 1.2},
        "what_to_keep": ["hook type", "open-loop count"],
        "what_to_change": ["subject", "visual treatment"],
    }
    brief["replication_guidance"] = guidance
    validate_artifact("video_analysis_brief", brief)
