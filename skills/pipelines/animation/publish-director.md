# Publish Director - Animation Pipeline

## When To Use

Package the animation so the metadata, thumbnail concept, and platform framing reflect the actual visual system of the project.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/publish_log.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["compose"]["render_report"]`, `state.artifacts["proposal"]["proposal_packet"]`, `state.artifacts["research"]["research_brief"]`, `state.artifacts["script"]["script"]` | Final outputs and topic framing |
| Playbook | Active style playbook | Visual naming consistency |

## Process

### 1. Match Packaging To The Animation Mode

Examples:

- diagram-heavy videos should look structured and legible,
- kinetic-type pieces should package around strong copy,
- illustrative animation should package around hero imagery.

### 2. Preserve Visual-System Truth

Store in `publish_log.metadata`:

- `animation_mode`
- `hero_frame_notes`
- `thumbnail_concept`
- `platform_notes`

### 3. Quality Gate

- metadata fits the actual animation mode,
- thumbnail concept matches the final visual system,
- exports are labeled by purpose and platform,
- the package is usable without extra manual work.

## Common Pitfalls

- Writing generic metadata that ignores the animation style.
- Creating a thumbnail concept unrelated to the final frames.
- Mixing platform variants without clear labels.

<!-- export-bundle-gate -->
## Export Bundle Gate (Binding)

Package every shipped master with `export_bundle`, after its last `technical_qc` run; never hand-write the export folder or the `publish_log` entry. The tool reads `<master>.qc.json` (or `qc_report_path`) and refuses a master with no report, a report of different bytes, or a `block` verdict. A `warn` verdict ships only with `qc_exception` (`reason` plus the `decision_id` of the `qc_exception` entry in `decision_log`). Any change to the master after the check, `audio_master` included, voids the report: run `technical_qc` again. One `export_bundle` call per master.

<!-- cold-review-export -->
## Cold Review At Export (Binding)

Pass `pipeline` with this manifest's name to `export_bundle`. The tool refuses a master with no `<master>.cold.json`, a review of different bytes, a `revise` verdict, or a project with no decisions in `decision_log.json`. An `escalate` verdict ships only with `cold_exception` (`reason` plus the `decision_id` of the user's `cold_exception` decision in `decision_log`).

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Run the **Publish Checklist** of `skills/meta/youtube-policy-gate.md` and write it to `publish_log.metadata.youtube_policy_checklist`; show it at the approval gate. Upload as private or unlisted first. Captions go up as `.srt` / `.vtt`, never burned into the video.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/meta/technical-qc-gate.md` — run `technical_qc` on every render shown to the user and on the final master; `block` stops delivery, every `warn` is opened and resolved. Declare planned silences/holds in `edit_decisions.metadata.intentional_ranges`.
- `skills/core/delivery-specs.md` — destination specs (YouTube, Shorts, Reels, TikTok), one complete version per language, SRT/VTT rules and chapters; never burn subtitles.
- `skills/creative/title-thumbnail-trailer.md` — three honest thumbnail variants, title options, credits and next-episode teaser.
