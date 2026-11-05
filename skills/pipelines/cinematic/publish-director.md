# Publish Director - Cinematic Pipeline

## When To Use

Package the cinematic piece and any cutdowns so the hero version stays clear and the distribution intent is obvious.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/publish_log.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["compose"]["render_report"]`, `state.artifacts["proposal"]["proposal_packet"]`, `state.artifacts["research"]["research_brief"]`, `state.artifacts["script"]["script"]` | Final outputs and beat map |
| Playbook | Active style playbook | Tone and naming consistency |

## Process

### 1. Separate Hero And Derivatives

Typical deliverables:

- hero trailer or brand film,
- teaser cut,
- social cutdown,
- poster-frame or thumbnail concept.

### 2. Match Metadata To Tone

Packaging should reflect the actual mood:

- dramatic,
- premium,
- mysterious,
- reflective,
- urgent.

### 3. Preserve Editorial Truth

Store in `publish_log.metadata`:

- `hero_output`
- `derivative_outputs`
- `poster_frame_notes`
- `distribution_notes`

### 4. Quality Gate

- hero export is clearly identified,
- derivative exports are labeled by purpose,
- metadata fits the tone,
- the package is usable without manual cleanup.

## Common Pitfalls

- Mixing teaser and hero outputs without clear naming.
- Writing generic metadata that ignores the mood.
- Treating all cutdowns as interchangeable.

<!-- export-bundle-gate -->
## Export Bundle Gate (Binding)

Package every shipped master with `export_bundle`, after its last `technical_qc` run; never hand-write the export folder or the `publish_log` entry. The tool reads `<master>.qc.json` (or `qc_report_path`) and refuses a master with no report, a report of different bytes, or a `block` verdict. A `warn` verdict ships only with `qc_exception` (`reason` plus the `decision_id` of the `qc_exception` entry in `decision_log`). Any change to the master after the check, `audio_master` included, voids the report: run `technical_qc` again. One `export_bundle` call per master.

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
