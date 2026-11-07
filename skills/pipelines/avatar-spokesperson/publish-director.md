# Publish Director - Avatar Spokesperson Pipeline

## When To Use

Package the finished spokesperson outputs for delivery. This stage should make it obvious which file is the hero cut, which are derivatives, and what message or audience each version serves.

## Process

### 1. Label Deliverables Clearly

Distinguish:

- hero cut,
- vertical cutdown,
- square cutdown,
- language variants,
- watermark or review versions.

### 2. Keep Metadata Message-Led

Recommended metadata keys:

- `audience_segment`
- `cta_copy`
- `offer_name`
- `locale`
- `thumbnail_concept`

### 3. Package Review Notes

If the avatar path has limitations such as visible lip-sync risk, retain that note in the package instead of hiding it.

### 4. Quality Gate

- exports are clearly named,
- metadata matches the intended message,
- poster frame or thumbnail concept features the presenter cleanly,
- review notes stay attached to the package.

## Common Pitfalls

- Mixing hero and derivative exports without clear naming.
- Reusing generic metadata that ignores the spokesperson offer.
- Dropping risk notes that matter for downstream publishing teams.

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
