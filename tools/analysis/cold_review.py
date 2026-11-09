"""Cold review of a finished master, by a reviewer who did not make it.

``skills/meta/reviewer.md`` is self-review: the agent that made the video judges it.
This tool keeps the second opinion honest. ``prepare`` builds the only material the
``cold-viewer`` agent receives: the brief, frames, the transcript and the measured
reports, never the conversation. ``record`` turns its scores into a verdict tied to
the exact bytes reviewed, which ``export_bundle`` checks in narrative pipelines.

The reviewer cannot hear audio or see motion between frames, so voice and layout
scores are capped by what was measured: a missing or failing report wins over any
score. The policy lives in ``skills/meta/cold-review.md``.

``preview`` and ``record_preview`` run the same reviewer before the render, on the
script, the plan, the clips and stills, so problems are fixed while they are cheap. Those verdicts
warn and leave a record; they never stop a render. See
``skills/meta/pre-render-review.md``.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from lib.channel import channel_brief, load_channel
from tools.analysis.technical_qc import file_sha256
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

NARRATIVE_PIPELINES = {
    "animated-explainer",
    "animation",
    "avatar-spokesperson",
    "character-animation",
    "cinematic",
    "documentary-montage",
    "hybrid",
}
CRITERIA = ("hook", "pacing", "legibility", "continuity", "audio", "promise", "voice", "layout")
MIN_SCORE = 3
MAX_ROUNDS = 3
MAX_FRAMES = 40
FRAME_WIDTH = 960
SCENE_MOMENT = 0.35
SETTLE_SECONDS = 0.35
HOOK_SECONDS = 1.0
PREVIEW_STAGES = ("script", "plan", "clips", "frames")
MAX_PREVIEW_PASSES = 2
PREVIEW_SCALE = 0.5
SHEET_TILES = 4
SHEET_TILE_WIDTH = 480
AI_TAGS = ("ai generated", "ai-generated")
SPEECH_WORDS_PER_SECOND = 2.5
MIN_HOOKS = 3
MAX_HOOK_SECONDS = 5.0
MAX_OVERRUN = 1.15
MIN_BEAT_GAP_SECONDS = 5.0
BEAT_GAP_RATIO = 0.2
GENERIC_OPENINGS = ("en este video", "hola", "bienvenid", "hoy vamos a", "hoy te", "in this video", "welcome", "hey guys", "today we")
COMPOSER_DIR = Path(__file__).resolve().parent.parent.parent / "remotion-composer"


def cold_path(video_path: str | Path) -> Path:
    return Path(video_path).with_suffix(".cold.json")


def packet_dir(video_path: str | Path) -> Path:
    return Path(video_path).with_suffix(".cold")


def read_report(path: Path) -> dict[str, Any] | None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def project_of(video_path: Path) -> Path | None:
    """Return the project of a master kept at projects/<name>/renders/."""
    resolved = video_path.resolve()
    return resolved.parent.parent if resolved.parent.name == "renders" else None


def approved_decisions(project_dir: str | Path | None) -> list[dict[str, Any]]:
    """Return what the project's decision_log says was decided, for reviewers to respect."""
    if not project_dir:
        return []
    root = Path(project_dir)
    log = read_report(root / "artifacts" / "decision_log.json") or read_report(root / "decision_log.json") or {}
    return [
        {key: decision.get(key) for key in ("category", "subject", "selected", "reason")}
        for decision in log.get("decisions") or []
        if decision.get("user_visible", True)
    ]


def earlier_findings(project_dir: str | Path | None, stages: tuple[str, ...], cold_report: Path | None = None) -> list[dict[str, Any]]:
    """Return what earlier reviews already raised, so a new one can build on it."""
    if not project_dir:
        return []
    artifacts = Path(project_dir) / "artifacts"
    reports = {stage: read_report(artifacts / f"preview_{stage}.json") for stage in stages}
    if cold_report:
        reports["master"] = read_report(cold_report)
    return [
        {"source": source, "problem": finding.get("problem"), "proposed_fix": finding.get("proposed_fix")}
        for source, report in reports.items()
        for finding in (report or {}).get("findings") or []
    ]


def frame_times(
    duration: float,
    scenes: list[dict[str, Any]],
    layout: dict[str, Any] | None,
    cues: list[float] | None = None,
) -> list[float]:
    """Pick frames: the hook, two per scene, every moment the audit flagged and every cue.

    The second frame of a scene sits at its end, once its animation has settled, because
    a frame taken halfway through a movement shows a state no viewer is meant to judge.
    """
    times = [min(HOOK_SECONDS, duration / 2)]
    for scene in scenes:
        start, end = float(scene["start"]), float(scene["end"])
        times += [start + (end - start) * SCENE_MOMENT, end - min(SETTLE_SECONDS, (end - start) * 0.25)]
    if not scenes:
        step = max(duration / (MAX_FRAMES - 1), 2.0)
        times += [step * index for index in range(1, int(duration / step) + 1)]
    flagged = [finding["start"] for finding in (layout or {}).get("findings", [])] + [float(cue) for cue in cues or []]
    if len(times) + len(flagged) > MAX_FRAMES:
        stride = (len(times) + len(flagged)) / MAX_FRAMES
        times = [times[int(index * stride)] for index in range(int(len(times) / stride))]
    moments = {round(min(moment, max(duration - 0.1, 0)), 2) for moment in times + flagged}
    return sorted(moments)


def is_ai_tagged(tags: str) -> bool:
    lowered = str(tags or "").lower()
    return any(tag in lowered for tag in AI_TAGS)


def preview_verdict(verdict: str, pass_number: int) -> str:
    """After its last pass, a moment that still needs fixes goes to the user."""
    return "escalate" if verdict == "fix" and pass_number >= MAX_PREVIEW_PASSES else verdict


def spoken_seconds(text: str) -> float:
    return round(len(str(text).split()) / SPEECH_WORDS_PER_SECOND, 1)


def script_problems(script: str, hooks: list[str], beats: list[dict[str, Any]], target_seconds: float) -> list[str]:
    """Return what can be measured in a script, before any opinion on it."""
    problems = []
    if len(hooks) < MIN_HOOKS:
        problems.append(f"Only {len(hooks)} openings to compare; at least {MIN_HOOKS} are needed.")
    for hook in hooks:
        if spoken_seconds(hook) > MAX_HOOK_SECONDS:
            problems.append(f"Opening takes {spoken_seconds(hook)} s, over {MAX_HOOK_SECONDS:.0f} s: {hook}")
        if hook.strip().lower().startswith(GENERIC_OPENINGS):
            problems.append(f"Generic opening: {hook}")
    duration = spoken_seconds(script)
    if target_seconds and duration > target_seconds * MAX_OVERRUN:
        problems.append(f"Script takes about {duration} s for a {target_seconds:.0f} s target.")

    # Every stretch needs a reason to stay, so the map must run from start to end.
    limit = max(MIN_BEAT_GAP_SECONDS, (target_seconds or duration) * BEAT_GAP_RATIO)
    moments = [0.0, *sorted(float(beat["second"]) for beat in beats), duration]
    for start, end in zip(moments, moments[1:]):
        if end - start > limit:
            problems.append(f"No reason to keep watching from {start:.1f} to {end:.1f} s.")
    return problems


def measured_caps(packet: dict[str, Any]) -> dict[str, tuple[int, str]]:
    """Return the highest score each measured criterion may keep, and why."""
    caps: dict[str, tuple[int, str]] = {}
    layout = packet.get("layout")
    if layout is None:
        caps["layout"] = (1, "No layout audit for this render.")
    elif layout.get("verdict") == "block":
        caps["layout"] = (1, "The layout audit blocked this composition.")
    if packet.get("has_narration"):
        narration = packet.get("narration")
        if narration is None:
            caps["voice"] = (1, "No narration_qc report for this narration.")
        elif narration.get("verdict") != "pass":
            caps["voice"] = (1, "narration_qc has flagged sentences nobody resolved.")
    return caps


def evaluate(
    scores: dict[str, Any],
    packet: dict[str, Any],
    round_number: int,
) -> tuple[str, dict[str, Any], list[str]]:
    """Return (verdict, final scores, failed criteria)."""
    caps = measured_caps(packet)
    final: dict[str, Any] = {}
    for criterion in CRITERIA:
        entry = dict(scores.get(criterion) or {})
        if criterion == "voice" and not packet.get("has_narration"):
            final[criterion] = {"score": None, "evidence": "No narration in this video."}
            continue
        if not isinstance(entry.get("score"), int) or not 1 <= entry["score"] <= 5:
            raise ValueError(f"{criterion} needs a score from 1 to 5.")
        if not str(entry.get("evidence") or "").strip():
            raise ValueError(f"{criterion} needs evidence: a timestamp or a frame.")
        if criterion in caps and entry["score"] > caps[criterion][0]:
            entry["score"], entry["capped_by"] = caps[criterion]
        final[criterion] = entry

    failed = [name for name, entry in final.items() if entry["score"] is not None and entry["score"] < MIN_SCORE]
    if not failed:
        return "pass", final, failed
    return ("escalate" if round_number >= MAX_ROUNDS else "revise"), final, failed


class ColdReview(BaseTool):
    name = "cold_review"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]
    usage_skills = ["meta/cold-review"]

    capabilities = ["build_cold_review_packet", "record_cold_review", "preview_before_render"]

    input_schema = {
        "type": "object",
        "required": ["operation"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["prepare", "record", "preview", "record_preview"],
                "description": (
                    "prepare: build the packet for cold-viewer. record: score it and write <video>.cold.json. "
                    "preview: build a packet before the render, for one stage. "
                    "record_preview: write artifacts/preview_<stage>.json."
                ),
            },
            "video_path": {"type": "string", "description": "prepare and record: final master, after audio_master."},
            "cues": {
                "type": "array",
                "items": {"type": "number"},
                "description": "prepare and frames: exact seconds to include, such as a key word or figure.",
            },
            "project_dir": {
                "type": "string",
                "description": "preview and record_preview: project folder. record: also lists the previews that ran.",
            },
            "stage": {"type": "string", "enum": list(PREVIEW_STAGES), "description": "Moment to preview."},
            "script_text": {"type": "string", "description": "script: full narration."},
            "hooks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "script: alternative openings to compare.",
            },
            "retention_map": {
                "type": "array",
                "items": {"type": "object"},
                "description": "script: {second, reason} for each moment that gives a reason to keep watching.",
            },
            "target_seconds": {"type": "number", "description": "script: planned duration."},
            "best_hook": {"type": "string", "description": "record_preview: opening chosen by cold-viewer."},
            "lines": {
                "type": "array",
                "items": {"type": "object"},
                "description": "plan: {scene_id, narration, visual, on_screen} per script line.",
            },
            "clips": {
                "type": "array",
                "items": {"type": "object"},
                "description": "clips: {id, path, scene_id, narration, tags} per candidate.",
            },
            "engine": {"type": "string", "enum": ["remotion", "hyperframes"], "description": "frames: render engine."},
            "entry": {"type": "string", "description": "frames: Remotion entry."},
            "composition_id": {"type": "string", "description": "frames: Remotion composition."},
            "props_path": {"type": "string", "description": "frames: Remotion props JSON."},
            "public_dir": {"type": "string", "description": "frames: Remotion public directory."},
            "workspace_path": {"type": "string", "description": "frames: HyperFrames workspace."},
            "verdict": {"type": "string", "enum": ["go", "fix"], "description": "record_preview: cold-viewer's verdict."},
            "pass_number": {"type": "integer", "minimum": 1, "maximum": MAX_PREVIEW_PASSES, "default": 1},
            "brief": {"type": "object", "description": "prepare: the brief or delivery promise."},
            "scenes": {
                "type": "array",
                "description": "prepare: scene windows in seconds, from edit_decisions or scene_plan.",
                "items": {
                    "type": "object",
                    "required": ["start", "end"],
                    "properties": {
                        "id": {"type": "string"},
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                    },
                },
            },
            "has_narration": {"type": "boolean", "default": True, "description": "prepare: the video has a voice."},
            "narration_report_path": {"type": "string", "description": "prepare: narration_qc report."},
            "layout_report_path": {
                "type": "string",
                "description": "prepare: layout report. Defaults to <video>.layout.json.",
            },
            "qc_report_path": {
                "type": "string",
                "description": "prepare: technical_qc report. Defaults to <video>.qc.json.",
            },
            "scores": {
                "type": "object",
                "description": "record: {criterion: {score: 1-5, evidence: text}} from cold-viewer.",
            },
            "findings": {
                "type": "array",
                "items": {"type": "object"},
                "description": "record: cold-viewer's findings, each with a timestamp and a proposed fix.",
            },
            "round": {"type": "integer", "minimum": 1, "maximum": MAX_ROUNDS, "default": 1},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=50)
    idempotency_key_fields = ["operation", "video_path", "round"]
    side_effects = ["writes a review packet next to the video and <video>.cold.json"]
    user_visible_verification = ["Read the failed criteria and their evidence before shipping"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        operation = inputs["operation"]
        start = time.time()
        try:
            if operation == "preview":
                data = self._preview(inputs)
            elif operation == "record_preview":
                data = self._record_preview(inputs)
            else:
                video_path = Path(inputs["video_path"])
                if not video_path.is_file():
                    return ToolResult(success=False, error=f"Video not found: {video_path}")
                data = self._prepare(video_path, inputs) if operation == "prepare" else self._record(video_path, inputs)
        except Exception as exc:  # noqa: BLE001 - surface ffmpeg and scoring failures
            return ToolResult(success=False, error=f"Cold review failed: {exc}")
        return ToolResult(success=True, data=data, duration_seconds=round(time.time() - start, 2))

    def _duration(self, video_path: Path) -> float:
        probe = self.run_command(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
            timeout=60,
        )
        return float(probe.stdout.strip())

    def _prepare(self, video_path: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        duration = self._duration(video_path)
        layout = read_report(Path(inputs.get("layout_report_path") or video_path.with_suffix(".layout.json")))
        qc = read_report(Path(inputs.get("qc_report_path") or video_path.with_suffix(".qc.json")))
        narration_path = inputs.get("narration_report_path")
        narration = read_report(Path(narration_path)) if narration_path else None

        out_dir = packet_dir(video_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("frame_*.jpg"):
            old.unlink()
        frames = []
        for moment in frame_times(duration, inputs.get("scenes") or [], layout, inputs.get("cues")):
            frame = out_dir / f"frame_{moment:08.2f}.jpg"
            self.run_command(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(moment), "-i", str(video_path),
                 "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2", "-q:v", "3", str(frame)],
                timeout=120,
            )
            frames.append({"time": moment, "file": frame.name})

        project = inputs.get("project_dir") or project_of(video_path)
        packet = {
            "input_sha256": file_sha256(video_path),
            "duration_seconds": round(duration, 2),
            "brief": inputs.get("brief") or {},
            "scenes": inputs.get("scenes") or [],
            "has_narration": inputs.get("has_narration", True),
            "transcript": (narration or {}).get("transcript", ""),
            "narration": None if narration is None else {k: narration.get(k) for k in ("verdict", "flagged")},
            "layout": None if layout is None else {k: layout.get(k) for k in ("verdict", "findings", "samples_checked")},
            "technical_qc": None if qc is None else {k: qc.get(k) for k in ("verdict", "loudness", "findings")},
            "frames": frames,
            "approved_decisions": approved_decisions(project),
            "earlier_findings": earlier_findings(project, PREVIEW_STAGES, cold_path(video_path)),
            "channel": channel_brief(load_channel()),
        }
        packet_path = out_dir / "packet.json"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"packet_path": str(packet_path), "frames": len(frames), "caps": list(measured_caps(packet))}

    def _record(self, video_path: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        packet = read_report(packet_dir(video_path) / "packet.json")
        if packet is None:
            raise ValueError("No packet for this video. Run operation prepare first.")
        sha = file_sha256(video_path)
        if packet.get("input_sha256") != sha:
            raise ValueError("The video changed after prepare. Run operation prepare again.")

        round_number = int(inputs.get("round", 1))
        if not 1 <= round_number <= MAX_ROUNDS:
            raise ValueError(f"round must be 1 to {MAX_ROUNDS}.")
        verdict, scores, failed = evaluate(inputs.get("scores") or {}, packet, round_number)
        report = {
            "input": str(video_path),
            "input_sha256": sha,
            "verdict": verdict,
            "round": round_number,
            "scores": scores,
            "failed_criteria": failed,
            "findings": inputs.get("findings") or [],
            "gates": {
                "layout": (packet.get("layout") or {}).get("verdict"),
                "narration": (packet.get("narration") or {}).get("verdict") if packet.get("has_narration") else "no_narration",
            },
        }
        if inputs.get("project_dir"):
            artifacts = Path(inputs["project_dir"]) / "artifacts"
            previews = {stage: read_report(artifacts / f"preview_{stage}.json") for stage in PREVIEW_STAGES}
            report["previews"] = {stage: (found or {}).get("verdict", "missing") for stage, found in previews.items()}
        report_path = cold_path(video_path)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**report, "report_path": str(report_path)}

    def _preview(self, inputs: dict[str, Any]) -> dict[str, Any]:
        stage = inputs.get("stage")
        if stage not in PREVIEW_STAGES:
            raise ValueError(f"stage must be one of {PREVIEW_STAGES}.")
        out_dir = Path(inputs["project_dir"]) / "artifacts" / f"preview_{stage}"
        out_dir.mkdir(parents=True, exist_ok=True)
        packet: dict[str, Any] = {
            "stage": stage,
            "brief": inputs.get("brief") or {},
            "approved_decisions": approved_decisions(inputs["project_dir"]),
            "earlier_findings": earlier_findings(inputs["project_dir"], PREVIEW_STAGES[: PREVIEW_STAGES.index(stage) + 1]),
            "channel": channel_brief(load_channel()),
        }

        if stage == "script":
            if not inputs.get("script_text"):
                raise ValueError("script needs script_text.")
            hooks = inputs.get("hooks") or []
            beats = inputs.get("retention_map") or []
            packet.update(
                {
                    "script": inputs["script_text"],
                    "hooks": hooks,
                    "retention_map": beats,
                    "spoken_seconds": spoken_seconds(inputs["script_text"]),
                    "measured_problems": script_problems(inputs["script_text"], hooks, beats, float(inputs.get("target_seconds") or 0)),
                }
            )
        elif stage == "plan":
            if not inputs.get("lines"):
                raise ValueError("plan needs lines.")
            packet["lines"] = inputs["lines"]
        elif stage == "clips":
            if not inputs.get("clips"):
                raise ValueError("clips needs clips.")
            packet["clips"] = [self._contact_sheet(clip, out_dir) for clip in inputs["clips"]]
            packet["ai_tagged"] = [clip["id"] for clip in inputs["clips"] if is_ai_tagged(clip.get("tags"))]
        else:
            scenes = inputs.get("scenes")
            if not scenes:
                raise ValueError("frames needs scenes.")
            for old in out_dir.glob("frame*"):
                old.unlink()
            duration = max(float(scene["end"]) for scene in scenes)
            packet["scenes"] = scenes
            packet["frames"] = self._render_preview_frames(inputs, frame_times(duration, scenes, None, inputs.get("cues")), out_dir)

        packet_path = out_dir / "packet.json"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "packet_path": str(packet_path),
            "stage": stage,
            "ai_tagged": packet.get("ai_tagged", []),
            "measured_problems": packet.get("measured_problems", []),
        }

    def _contact_sheet(self, clip: dict[str, Any], out_dir: Path) -> dict[str, Any]:
        """Tile evenly spaced frames, and leave the file path out of what the viewer reads."""
        path = Path(clip["path"])
        if not path.is_file():
            raise ValueError(f"Clip not found: {path}")
        duration = self._duration(path)
        sheet = out_dir / f"sheet_{clip['id']}.jpg"
        self.run_command(
            ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf",
             f"fps={SHEET_TILES}/{duration},scale={SHEET_TILE_WIDTH}:-2,tile={SHEET_TILES}x1",
             "-frames:v", "1", "-q:v", "3", str(sheet)],
            timeout=120,
        )
        return {**{key: value for key, value in clip.items() if key != "path"}, "sheet": sheet.name}

    def _render_preview_frames(self, inputs: dict[str, Any], times: list[float], out_dir: Path) -> list[dict[str, Any]]:
        moments = ",".join(str(moment) for moment in times)
        if inputs.get("engine") == "hyperframes":
            from tools.video.hyperframes_compose import HyperFramesCompose

            workspace = Path(inputs["workspace_path"])
            args = ["snapshot", "--at", moments, "--no-end", "--output", str(out_dir.resolve())]
            proc = HyperFramesCompose()._run_hf(args, cwd=workspace, timeout=600, check=False)
            files = sorted(out_dir.glob("frame*.png"))
            if proc.returncode != 0 or len(files) != len(times):
                raise RuntimeError(f"hyperframes snapshot gave {len(files)} of {len(times)}: {(proc.stderr or '')[-500:]}")
            return [{"time": moment, "file": path.name} for moment, path in zip(times, files)]

        if not inputs.get("entry") or not inputs.get("composition_id"):
            raise ValueError("Remotion needs entry and composition_id.")
        cmd = [
            "node", "scripts/preview-frames.mjs",
            "--entry", str(Path(inputs["entry"]).resolve()),
            "--composition", inputs["composition_id"],
            "--out-dir", str(out_dir.resolve()),
            "--times", moments,
            "--scale", str(PREVIEW_SCALE),
        ]
        if inputs.get("props_path"):
            cmd += ["--props", str(Path(inputs["props_path"]).resolve())]
        if inputs.get("public_dir"):
            cmd += ["--public-dir", str(Path(inputs["public_dir"]).resolve())]
        proc = subprocess.run(cmd, cwd=COMPOSER_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout)[-1500:])
        return [{"time": moment, "file": f"frame_{moment:08.2f}.jpg"} for moment in times]

    def _record_preview(self, inputs: dict[str, Any]) -> dict[str, Any]:
        stage = inputs.get("stage")
        if stage not in PREVIEW_STAGES:
            raise ValueError(f"stage must be one of {PREVIEW_STAGES}.")
        pass_number = int(inputs.get("pass_number", 1))
        if not 1 <= pass_number <= MAX_PREVIEW_PASSES:
            raise ValueError(f"pass_number must be 1 to {MAX_PREVIEW_PASSES}.")

        artifacts = Path(inputs["project_dir"]) / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        verdict = inputs.get("verdict")
        findings = list(inputs.get("findings") or [])
        packet = read_report(artifacts / f"preview_{stage}" / "packet.json") or {}
        for clip in packet.get("ai_tagged") or []:
            findings.append({"scene_id": "", "problem": f"Clip {clip} is tagged as AI.", "proposed_fix": "Replace it with real footage."})
        for problem in packet.get("measured_problems") or []:
            findings.append({"scene_id": "", "problem": problem, "proposed_fix": "Fix it and repeat this moment."})
        if packet.get("ai_tagged") or packet.get("measured_problems"):
            verdict = "fix"
        if verdict not in ("go", "fix"):
            raise ValueError("verdict must be go or fix.")
        if verdict == "fix" and not findings:
            raise ValueError("A fix verdict needs findings.")

        report = {
            "stage": stage,
            "verdict": preview_verdict(verdict, pass_number),
            "pass_number": pass_number,
            "findings": findings,
        }
        if inputs.get("best_hook"):
            report["best_hook"] = inputs["best_hook"]
        report_path = artifacts / f"preview_{stage}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**report, "report_path": str(report_path)}
