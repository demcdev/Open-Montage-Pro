"""Local export bundler — the first PUBLISH-tier tool.

Every pipeline ends in a `publish` stage that produces a `publish_log` artifact,
but `tools/publishers/` shipped empty, so the mechanical packaging (copying the
render, writing metadata files, laying out the export directory, and emitting a
schema-valid `publish_log`) had to be hand-rolled by the agent each time.

This tool does that packaging deterministically and locally — no external
account, no upload, no cost. It takes the final render path plus the SEO
metadata the publish-director skill prepares and writes a self-contained export
bundle a creator can hand to any platform, returning a validated `publish_log`
entry with `status: "exported"`.

It is also the delivery gate: a master only ships with a `technical_qc` report
of those exact bytes. No report, a report of another file, or a `block` verdict
refuses the export. A `warn` verdict needs a `qc_exception` that names the
decision_log entry accepting it. The policy lives in
`skills/meta/technical-qc-gate.md`.

A networked publisher (e.g. a YouTube uploader) can be added later as a separate
`provider` under the same `publish` capability.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tools.analysis.cold_review import MAX_ROUNDS, NARRATIVE_PIPELINES, approved_decisions, cold_path, project_of, read_report
from tools.analysis.technical_qc import file_sha256
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline_defs"

class ExportBundle(BaseTool):
    name = "export_bundle"
    version = "0.2.0"
    tier = ToolTier.PUBLISH
    capability = "publish"
    provider = "local"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = []  # pure filesystem packaging
    install_instructions = "No setup required — runs locally with the Python standard library."

    agent_skills = []

    capabilities = ["package_export", "write_publish_log", "enforce_technical_qc"]
    supports = {
        "local_offline": True,
        "free": True,
        "uploads": False,
    }
    best_for = [
        "packaging a finished render for hand-off to any platform",
        "producing a schema-valid publish_log without an external account",
        "offline / no-API-key publishing",
    ]
    not_good_for = [
        "uploading directly to YouTube/TikTok/etc. (no network publish)",
        "generating SEO metadata or thumbnails (the publish-director prepares those)",
    ]

    input_schema = {
        "type": "object",
        "required": ["video_path", "title", "pipeline"],
        "properties": {
            "video_path": {
                "type": "string",
                "description": "Path to the final rendered video (from render_report.outputs[].path).",
            },
            "title": {"type": "string", "description": "Video title / SEO title."},
            "project_name": {
                "type": "string",
                "description": "Project name; used for the export folder. Defaults to the video's parent-of-parent dir name.",
            },
            "export_dir": {
                "type": "string",
                "description": "Override the export root. Defaults to 'exports/<project_name>'.",
            },
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "chapters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "description": "Either {start_seconds, title} or {time, label}.",
                },
            },
            "subtitles_path": {"type": "string"},
            "stems_dir": {
                "type": "string",
                "description": "Folder with the audio stems from audio_mixer, copied to stems/.",
            },
            "thumbnail_path": {"type": "string"},
            "thumbnail_concept": {
                "type": "object",
                "description": "Thumbnail concept JSON when no rendered thumbnail exists.",
            },
            "platform": {
                "type": "string",
                "description": "Target platform label for the publish_log entry. Defaults to 'local'.",
            },
            "visibility": {"type": "string", "enum": ["public", "private", "unlisted"]},
            "qc_report_path": {
                "type": "string",
                "description": "technical_qc report of this master. Defaults to <video>.qc.json.",
            },
            "qc_exception": {
                "type": "object",
                "description": (
                    "Required to ship a master whose verdict is warn. Cannot override "
                    "block, a missing report, or a report of another file."
                ),
                "required": ["reason", "decision_id"],
                "properties": {
                    "reason": {"type": "string", "description": "Why the warnings are acceptable."},
                    "decision_id": {
                        "type": "string",
                        "description": "decision_log entry (category qc_exception) that accepted them.",
                    },
                },
            },
            "project_dir": {
                "type": "string",
                "description": "Project folder. Defaults to the parent of renders/.",
            },
            "pipeline": {
                "type": "string",
                "description": "Pipeline manifest name. Narrative pipelines need a current cold review and a decision_log.",
            },
            "cold_exception": {
                "type": "object",
                "description": (
                    "Required to ship a master whose cold review escalated after its last "
                    "round. Cannot override a missing report or one of another file."
                ),
                "required": ["reason", "decision_id"],
                "properties": {
                    "reason": {"type": "string", "description": "Why the user accepted the failed criteria."},
                    "decision_id": {
                        "type": "string",
                        "description": "decision_log entry (category cold_exception) with the user's approval.",
                    },
                },
            },
            "timestamp": {
                "type": "string",
                "description": "Override the ISO-8601 timestamp (mainly for deterministic tests).",
            },
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "publish_log": {"type": "object"},
            "export_path": {"type": "string"},
            "files_written": {"type": "array", "items": {"type": "string"}},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=0, network_required=False
    )
    side_effects = ["writes an export bundle directory to disk"]
    user_visible_verification = [
        "Open the export folder and confirm the video, metadata, and chapters are present and correct",
    ]

    # ---- Helpers ----

    @staticmethod
    def _format_chapter_time(seconds: float) -> str:
        seconds = int(round(seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _chapter_lines(self, chapters: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for ch in chapters:
            label = ch.get("title") or ch.get("label") or ""
            if "start_seconds" in ch or "time_seconds" in ch:
                ts = self._format_chapter_time(ch.get("start_seconds", ch.get("time_seconds", 0)))
            elif "time" in ch:
                ts = str(ch["time"])
            else:
                ts = "0:00"
            lines.append(f"{ts} - {label}".rstrip(" -"))
        return lines

    @staticmethod
    def _pipeline_gate(inputs: dict[str, Any]) -> Optional[str]:
        """A pipeline this repo does not know could not say which gates apply."""
        pipeline = inputs.get("pipeline")
        if not pipeline:
            return "pipeline is required: it decides which gates this master must pass."
        if not (PIPELINE_DIR / f"{pipeline}.yaml").is_file():
            return f"Unknown pipeline {pipeline!r}: no manifest in {PIPELINE_DIR}."
        return None

    @staticmethod
    def _decision_gate(video_path: Path, inputs: dict[str, Any]) -> Optional[str]:
        """A narrative master must leave a record of what was decided along the way."""
        if inputs.get("pipeline") not in NARRATIVE_PIPELINES:
            return None
        project = inputs.get("project_dir") or project_of(video_path) or video_path.parent
        decisions = approved_decisions(project)
        if not decisions:
            return f"No decisions in {project}: write artifacts/decision_log.json before exporting."
        if (Path(project) / "artifacts" / "sound_plan.json").is_file():
            return None
        if any(decision.get("category") == "sound_exception" for decision in decisions):
            return None
        return f"No sound plan in {project}: write artifacts/sound_plan.json or record a sound_exception decision."

    @staticmethod
    def _qc_gate(video_path: Path, inputs: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
        """Return (error, publish_log qc entry) for this master as it stands now."""
        report_path = Path(
            inputs.get("qc_report_path") or video_path.with_suffix(".qc.json")
        ).expanduser()
        if not report_path.is_file():
            return f"No technical_qc report at {report_path}. Run technical_qc on this master.", {}
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return f"Unreadable technical_qc report {report_path}: {exc}", {}
        if not isinstance(report, dict):
            return f"Unreadable technical_qc report {report_path}: not a JSON object", {}

        # The last check must describe these bytes; mastering or re-rendering voids it.
        if report.get("input_sha256") != file_sha256(video_path):
            return (
                f"technical_qc report {report_path} does not match {video_path.name}: "
                "the master changed after the check. Run technical_qc again.",
                {},
            )

        verdict = report.get("verdict")
        flagged = [
            f.get("message", "") for f in report.get("findings") or []
            if f.get("severity") == verdict
        ]
        if verdict == "block":
            return f"technical_qc verdict is block: {'; '.join(flagged)}", {}
        if verdict not in ("pass", "warn"):
            return f"technical_qc report {report_path} has no valid verdict: {verdict!r}", {}

        entry: dict[str, Any] = {
            "verdict": verdict,
            "profile": report.get("profile", ""),
            "report_path": str(report_path),
        }
        if verdict == "warn":
            exception = inputs.get("qc_exception") or {}
            reason = str(exception.get("reason") or "").strip()
            decision_id = str(exception.get("decision_id") or "").strip()
            if not (reason and decision_id):
                return (
                    f"technical_qc verdict is warn: {'; '.join(flagged)}. Fix them, declare "
                    "them in intentional_ranges and re-run, or pass qc_exception with "
                    "reason and decision_id.",
                    {},
                )
            entry["exception"] = {"reason": reason, "decision_id": decision_id}
        return None, entry

    @staticmethod
    def _cold_gate(video_path: Path, inputs: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
        """Return (error, publish_log cold review entry) for this master as it stands now."""
        if inputs.get("pipeline") not in NARRATIVE_PIPELINES:
            return None, {}
        report_path = cold_path(video_path)
        report = read_report(report_path)
        if report is None:
            return f"No cold review at {report_path}. Run skills/meta/cold-review.md on this master.", {}
        if report.get("input_sha256") != file_sha256(video_path):
            return (
                f"Cold review {report_path} does not match {video_path.name}: "
                "the master changed after the review. Review it again.",
                {},
            )

        verdict = report.get("verdict")
        failed = ", ".join(report.get("failed_criteria") or [])
        if verdict == "revise":
            return f"Cold review verdict is revise: fix {failed} and review again.", {}
        if verdict not in ("pass", "escalate"):
            return f"Cold review {report_path} has no valid verdict: {verdict!r}", {}

        entry: dict[str, Any] = {"verdict": verdict, "report_path": str(report_path), "gates": report.get("gates") or {}}
        if verdict == "escalate":
            exception = inputs.get("cold_exception") or {}
            reason = str(exception.get("reason") or "").strip()
            decision_id = str(exception.get("decision_id") or "").strip()
            if not (reason and decision_id):
                return (
                    f"Cold review still fails after {MAX_ROUNDS} rounds: {failed}. The user decides: "
                    "pass cold_exception with reason and decision_id to ship it anyway.",
                    {},
                )
            entry["exception"] = {"reason": reason, "decision_id": decision_id}
        return None, entry

    # ---- Execution ----

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        video_path = Path(inputs["video_path"]).expanduser()
        if not video_path.is_file():
            return ToolResult(success=False, error=f"video_path not found: {video_path}")

        pipeline_error = self._pipeline_gate(inputs)
        if pipeline_error:
            return ToolResult(success=False, error=pipeline_error)
        qc_error, qc_entry = self._qc_gate(video_path, inputs)
        if qc_error:
            return ToolResult(success=False, error=qc_error)
        cold_error, cold_entry = self._cold_gate(video_path, inputs)
        if cold_error:
            return ToolResult(success=False, error=cold_error)

        decision_error = self._decision_gate(video_path, inputs)
        if decision_error:
            return ToolResult(success=False, error=decision_error)

        title = inputs["title"]
        project_name = inputs.get("project_name") or self._infer_project_name(video_path)

        # Explicitly-provided optional assets must exist — silently dropping them
        # would ship a publish package missing part of an approved deliverable.
        for key in ("subtitles_path", "thumbnail_path"):
            val = inputs.get(key)
            if val and not Path(val).expanduser().is_file():
                return ToolResult(success=False, error=f"{key} provided but not found: {val}")
        stems_dir = inputs.get("stems_dir")
        if stems_dir and not Path(stems_dir).expanduser().is_dir():
            return ToolResult(success=False, error=f"stems_dir provided but not found: {stems_dir}")

        export_root = (
            Path(inputs["export_dir"]).expanduser()
            if inputs.get("export_dir")
            else self._default_export_dir(video_path, project_name)
        )

        video_dir = export_root / "video"
        meta_dir = export_root / "metadata"
        thumb_dir = export_root / "thumbnails"
        for d in (video_dir, meta_dir, thumb_dir):
            d.mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []

        # Video
        out_video = video_dir / f"output{video_path.suffix or '.mp4'}"
        shutil.copy2(video_path, out_video)
        files_written.append(str(out_video))

        if stems_dir:
            stems_out = export_root / "stems"
            stems_out.mkdir(parents=True, exist_ok=True)
            for stem in sorted(Path(stems_dir).expanduser().glob("*.wav")):
                shutil.copy2(stem, stems_out / stem.name)
                files_written.append(str(stems_out / stem.name))

        # Subtitles (optional)
        subs_in = inputs.get("subtitles_path")
        if subs_in:
            subs_in = Path(subs_in).expanduser()
            if subs_in.is_file():
                out_subs = video_dir / f"subtitles{subs_in.suffix or '.srt'}"
                shutil.copy2(subs_in, out_subs)
                files_written.append(str(out_subs))

        description = inputs.get("description", "")
        tags = inputs.get("tags", []) or []
        hashtags = inputs.get("hashtags", []) or []
        chapters = inputs.get("chapters", []) or []
        chapter_lines = self._chapter_lines(chapters)

        # metadata.json
        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "hashtags": hashtags,
            "chapters": chapters,
        }
        meta_json = meta_dir / "metadata.json"
        meta_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        files_written.append(str(meta_json))

        # QC report travels with the master it certifies
        qc_copy = meta_dir / "qc_report.json"
        shutil.copy2(qc_entry["report_path"], qc_copy)
        files_written.append(str(qc_copy))

        # description.txt (description + chapters appended, ready to paste)
        desc_parts = [description] if description else []
        if chapter_lines:
            desc_parts.append("\n".join(chapter_lines))
        desc_txt = meta_dir / "description.txt"
        desc_txt.write_text("\n\n".join(desc_parts) + ("\n" if desc_parts else ""), encoding="utf-8")
        files_written.append(str(desc_txt))

        # tags.txt (one per line)
        if tags:
            tags_txt = meta_dir / "tags.txt"
            tags_txt.write_text("\n".join(tags) + "\n", encoding="utf-8")
            files_written.append(str(tags_txt))

        # chapters.txt
        if chapter_lines:
            chapters_txt = meta_dir / "chapters.txt"
            chapters_txt.write_text("\n".join(chapter_lines) + "\n", encoding="utf-8")
            files_written.append(str(chapters_txt))

        # Thumbnail: real image if given, else concept JSON
        thumb_in = inputs.get("thumbnail_path")
        if thumb_in and Path(thumb_in).expanduser().is_file():
            thumb_in = Path(thumb_in).expanduser()
            out_thumb = thumb_dir / f"thumbnail{thumb_in.suffix or '.png'}"
            shutil.copy2(thumb_in, out_thumb)
            files_written.append(str(out_thumb))
        elif inputs.get("thumbnail_concept"):
            concept = thumb_dir / "concept.json"
            concept.write_text(json.dumps(inputs["thumbnail_concept"], indent=2), encoding="utf-8")
            files_written.append(str(concept))

        timestamp = inputs.get("timestamp") or datetime.now(timezone.utc).isoformat()
        entry: dict[str, Any] = {
            "platform": inputs.get("platform", "local"),
            "status": "exported",
            "export_path": str(export_root),
            "timestamp": timestamp,
            "qc": qc_entry,
            **({"cold_review": cold_entry} if cold_entry else {}),
            "metadata_used": {
                "title": title,
                "description": description,
                "hashtags": hashtags,
                "chapters": chapters,
            },
        }
        if inputs.get("visibility"):
            entry["visibility"] = inputs["visibility"]
        if not inputs.get("thumbnail_path"):
            entry["warnings"] = ["No thumbnail in this export."]

        publish_log = {"version": "1.0", "entries": [entry]}

        # Validate against the canonical schema so a bad entry fails here, not at checkpoint.
        try:
            from schemas.artifacts import validate_artifact

            validate_artifact("publish_log", publish_log)
        except Exception as exc:  # pragma: no cover - defensive
            return ToolResult(success=False, error=f"publish_log failed schema validation: {exc}")

        return ToolResult(
            success=True,
            data={
                "publish_log": publish_log,
                "export_path": str(export_root),
                "files_written": files_written,
            },
            artifacts=[str(out_video)],
        )

    @staticmethod
    def _default_export_dir(video_path: Path, project_name: str) -> Path:
        """Keep run output inside the project workspace.

        When the render lives at ``projects/<name>/renders/...`` (the OpenMontage
        convention), default the bundle to ``projects/<name>/exports/`` alongside
        ``artifacts/``, ``assets/`` and ``renders/``. Otherwise fall back to a
        top-level ``exports/<project_name>/``.
        """
        resolved = video_path.resolve()
        if resolved.parent.name == "renders":
            return resolved.parent.parent / "exports"
        return Path("exports") / project_name

    @staticmethod
    def _infer_project_name(video_path: Path) -> str:
        # projects/<name>/renders/final.mp4 -> <name>; fall back to the file stem.
        parents = video_path.resolve().parents
        if len(parents) >= 2:
            return parents[1].name
        return video_path.stem
