"""Layout audit for compositions, run on the composition itself before the render.

It measures real boxes in the browser at samples across the timeline and catches
what frame review misses between samples: text outside the canvas, text cut by its
container, text on top of other text, and text hidden behind a graphic.

Remotion goes through ``remotion-composer/scripts/layout-audit.mjs``, which adds a
probe to the bundle, so hand-authored projects need no changes. HyperFrames has the
same measurements in ``hyperframes check``, read here with its layout section only.

A problem that lasts at least ``BLOCK_SECONDS`` blocks the render. Anything shorter
is usually an element entering or leaving, so it stays a warning. Intentional cases
are declared in the composition with ``data-layout-allow-overlap`` or
``data-layout-allow-overflow``.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from tools.analysis.technical_qc import VERDICT_EXIT, verdict_for
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

log = logging.getLogger(__name__)

BLOCK_SECONDS = 1.0
DEFAULT_STEP_SECONDS = 0.5
MIN_HYPERFRAMES_SAMPLES = 9
MAX_HYPERFRAMES_ISSUES = 5000
BLOCKING_RULES = {"text_off_canvas", "text_cut_off", "text_overlap", "text_covered"}

# hyperframes check codes for the same problems layout-probe.js reports.
HYPERFRAMES_RULES = {
    "canvas_overflow": "text_off_canvas",
    "text_box_overflow": "text_cut_off",
    "clipped_text": "text_cut_off",
    "content_overlap": "text_overlap",
    "text_occluded": "text_covered",
    "panel_out_of_canvas": "graphic_off_canvas",
}

COMPOSER_DIR = Path(__file__).resolve().parent.parent.parent / "remotion-composer"
_ROOT_DURATION = re.compile(r'data-composition-id="[^"]*"[^>]*?data-duration="([\d.]+)"')


def evaluate(samples: list[dict[str, Any]], step: float) -> list[dict[str, Any]]:
    """Join each problem across samples into one finding with its time range."""
    tracks: dict[tuple[str, str, str], list[tuple[float, dict[str, Any]]]] = {}
    for sample in samples:
        for finding in sample.get("findings", []):
            key = (finding["rule"], finding.get("text", ""), finding.get("other", ""))
            tracks.setdefault(key, []).append((sample["time"], finding))

    findings = []
    for (rule, text, other), seen in tracks.items():
        seen.sort(key=lambda item: item[0])
        runs = [[seen[0]]]
        for item in seen[1:]:
            if item[0] - runs[-1][-1][0] > step * 1.5:
                runs.append([])
            runs[-1].append(item)
        for run in runs:
            start, end = run[0][0], run[-1][0]
            lasting = end - start >= BLOCK_SECONDS
            finding = {
                "rule": rule,
                "severity": "block" if rule in BLOCKING_RULES and lasting else "warn",
                "start": round(start, 2),
                "end": round(end, 2),
                "samples": len(run),
                "text": text,
                "box": run[0][1].get("box"),
            }
            if other:
                finding["other"] = other
            findings.append(finding)
    return sorted(findings, key=lambda item: (item["severity"] != "block", item["start"], item["rule"]))


def hyperframes_samples(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn the flat findings of hyperframes check into one entry per sampled time."""
    by_time: dict[float, list[dict[str, Any]]] = {}
    for finding in findings:
        rule = HYPERFRAMES_RULES.get(finding.get("code"), finding.get("code", "unknown"))
        rect = finding.get("rect") or {}
        by_time.setdefault(float(finding.get("time", 0)), []).append(
            {
                "rule": rule,
                "text": finding.get("text") or finding.get("selector", ""),
                "other": finding.get("containerSelector", "") if rule == "text_overlap" else "",
                "box": [round(rect[side]) for side in ("left", "top", "right", "bottom") if side in rect],
            }
        )
    return [{"time": moment, "findings": items} for moment, items in sorted(by_time.items())]


def build_report(engine: str, samples: list[dict[str, Any]], step: float, checked: int, expected: int) -> dict[str, Any]:
    """Build the report for this engine's samples."""
    findings = evaluate(samples, step)
    verdict = verdict_for(findings)
    return {
        "engine": engine,
        "verdict": verdict,
        "exit_code": VERDICT_EXIT[verdict],
        "samples_checked": checked,
        "samples_expected": expected,
        "step_seconds": step,
        "findings": findings,
        "counts": {sev: sum(1 for f in findings if f["severity"] == sev) for sev in ("block", "warn")},
    }


def render_gate(audit_inputs: dict[str, Any], output_path: Path, skip: bool = False) -> str | None:
    """Audit a composition before its render. Return why it must not render, or None.

    The report lands next to the master, where cold review expects it. An audit that
    could not run leaves no report, and cold review treats that as a failure, so a
    broken browser never stops a render here.
    """
    if skip:
        return None
    report_path = Path(output_path).with_suffix(".layout.json")
    result = LayoutAudit().execute({**audit_inputs, "report_path": str(report_path)})
    if not result.success:
        log.warning("Layout audit did not run: %s", result.error)
        report_path.unlink(missing_ok=True)
        return None
    if result.data["verdict"] != "block":
        return None
    blocking = [f for f in result.data["findings"] if f["severity"] == "block"]
    details = "; ".join(f"{f['rule']} at {f['start']}-{f['end']}s: {f['text']}" for f in blocking[:8])
    return (
        f"Layout audit blocked the render ({len(blocking)} problems): {details}. "
        f"Fix the composition or declare intentional cases. Report: {report_path}"
    )


class LayoutAudit(BaseTool):
    name = "layout_audit"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "chromium"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:node"]
    install_instructions = "Install Node.js 22+ and run `npm install` in remotion-composer/."
    agent_skills = ["remotion-best-practices", "hyperframes-cli"]
    usage_skills = ["meta/layout-audit"]

    capabilities = [
        "detect_text_off_canvas",
        "detect_text_cut_off",
        "detect_text_overlap",
        "detect_text_covered",
        "detect_graphic_off_canvas",
    ]

    input_schema = {
        "type": "object",
        "required": ["engine"],
        "properties": {
            "engine": {"type": "string", "enum": ["remotion", "hyperframes"]},
            "entry": {"type": "string", "description": "Remotion entry .tsx that calls registerRoot."},
            "composition_id": {"type": "string", "description": "Remotion composition to audit."},
            "props_path": {"type": "string", "description": "Remotion input props JSON."},
            "public_dir": {"type": "string", "description": "Remotion public directory."},
            "width": {"type": "integer", "description": "Remotion width override, as passed to the render."},
            "height": {"type": "integer", "description": "Remotion height override, as passed to the render."},
            "workspace_path": {"type": "string", "description": "HyperFrames workspace with index.html."},
            "every_seconds": {
                "type": "number",
                "default": DEFAULT_STEP_SECONDS,
                "description": "Time between samples.",
            },
            "report_path": {
                "type": "string",
                "description": "Where to write the JSON report. Defaults to a temporary file.",
            },
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=2048, vram_mb=0, disk_mb=200)
    idempotency_key_fields = ["engine", "entry", "composition_id", "workspace_path", "every_seconds"]
    side_effects = ["writes a JSON layout report to report_path"]
    user_visible_verification = ["Open each flagged time and confirm the problem or declare it intentional"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        step = float(inputs.get("every_seconds") or DEFAULT_STEP_SECONDS)
        try:
            if inputs["engine"] == "remotion":
                report = self._audit_remotion(inputs, step)
            else:
                report = self._audit_hyperframes(inputs, step)
        except Exception as exc:  # noqa: BLE001 - surface any browser or parse failure
            return ToolResult(success=False, error=f"Layout audit failed: {exc}")

        report_path = Path(inputs.get("report_path") or tempfile.mkstemp(suffix=".layout.json")[1])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return ToolResult(
            success=True,
            data={**report, "report_path": str(report_path)},
            artifacts=[str(report_path)],
            duration_seconds=round(time.time() - start, 2),
        )

    def _audit_remotion(self, inputs: dict[str, Any], step: float) -> dict[str, Any]:
        if not inputs.get("entry") or not inputs.get("composition_id"):
            raise ValueError("Remotion needs entry and composition_id.")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "samples.json"
            cmd = [
                "node", "scripts/layout-audit.mjs",
                "--entry", str(Path(inputs["entry"]).resolve()),
                "--composition", inputs["composition_id"],
                "--out", str(out),
                "--every-seconds", str(step),
            ]
            if inputs.get("props_path"):
                cmd += ["--props", str(Path(inputs["props_path"]).resolve())]
            if inputs.get("public_dir"):
                cmd += ["--public-dir", str(Path(inputs["public_dir"]).resolve())]
            if inputs.get("width") and inputs.get("height"):
                cmd += ["--width", str(inputs["width"]), "--height", str(inputs["height"])]
            proc = subprocess.run(cmd, cwd=COMPOSER_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or proc.stdout)[-1500:])
            raw = json.loads(out.read_text(encoding="utf-8"))

        samples = [{**sample, "time": sample["frame"] / raw["fps"]} for sample in raw["samples"]]
        report = build_report("remotion", samples, step, len(samples), raw["expected_samples"])
        report["composition"] = raw["composition"]
        return report

    def _audit_hyperframes(self, inputs: dict[str, Any], step: float) -> dict[str, Any]:
        from tools.video.hyperframes_compose import HyperFramesCompose

        if not inputs.get("workspace_path"):
            raise ValueError("HyperFrames needs workspace_path.")
        index = Path(inputs["workspace_path"]) / "index.html"
        match = _ROOT_DURATION.search(index.read_text(encoding="utf-8"))
        duration = float(match.group(1)) if match else 0.0
        expected = max(MIN_HYPERFRAMES_SAMPLES, round(duration / step))

        result = HyperFramesCompose().execute(
            {
                "operation": "check",
                "workspace_path": inputs["workspace_path"],
                "skip_contrast": True,
                "samples": expected,
                "collapse_static": False,
                "max_issues": MAX_HYPERFRAMES_ISSUES,
            }
        )
        report = result.data.get("report") or {}
        layout = report.get("layout")
        # A skipped browser reports an empty layout section, which must not read as clean.
        if layout is None or report.get("browserSkipped") or not layout.get("samples"):
            findings = (report.get("runtime") or {}).get("findings") or []
            detail = findings[0].get("message") if findings else result.error
            raise RuntimeError(f"hyperframes check measured no samples: {detail}")
        checked = len(layout["samples"])
        spacing = duration / checked if duration else step
        return build_report("hyperframes", hyperframes_samples(layout.get("findings", [])), spacing, checked, expected)
