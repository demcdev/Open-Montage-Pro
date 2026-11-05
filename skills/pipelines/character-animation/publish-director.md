# Publish Director - Character Animation Pipeline

## Goal

Package the final character-animation deliverable with honest metadata and a
strong character-forward thumbnail concept.

## Requirements

- Mention the actual visual treatment: local rigged character animation,
  procedural effects, Remotion/HyperFrames render, or mixed.
- Pick a poster frame where the main character's emotion is readable.
- If the output is a sample, label it as a sample.
- If the final is inspired by a reference, describe the inspiration without
  claiming duplication.

## Output

Produce `publish_log` with:

- final video path,
- thumbnail/poster-frame notes,
- title ideas,
- description,
- platform-specific export notes,
- limitations or follow-up recommendations.

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
