# Publish Director - Documentary Montage Pipeline

## When To Use

The montage is rendered and reviewed. You package it for delivery: one complete version per language, the technical check on each master, honest metadata and thumbnails, archive credits and attributions, and the `publish_log`. Nothing is uploaded from here; `export_bundle` writes a local package and the user publishes.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/publish_log.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["compose"]["render_report"]` (required); `brief`, `script`, `research_brief`, `asset_manifest` (optional) | Final masters, on-screen text, claims, licences |
| Tools | `technical_qc`, `export_bundle`, `subtitle_gen` (only with narration) | Final check, packaging, captions |
| Core skill | `skills/core/subtitle-sync.md` | Subtitle timing and readability |

## Process

### 1. Check Every Master

Run `technical_qc` on each master that will ship (`profile: "youtube"` or `"social"`, `expected` from `skills/core/delivery-specs.md`, `asset_manifest_path` so unlicensed assets block). Montages hold images on purpose: pass the planned holds and silences from `script.metadata.silence_windows` as `intentional_ranges`, and raise `freeze_min_seconds` for long static archival holds. `block` stops this stage.

### 2. One Package Per Language

The English and Spanish versions differ in on-screen text (and narration, if any). Each has its own render, its own `technical_qc` pass and its own `export_bundle` call. If only one language was rendered, say so at the gate; do not label it bilingual.

### 3. Credits And Attribution

Archive footage often requires attribution (Wikimedia CC BY / BY-SA, some Archive.org items, music). Build the credits from `asset_manifest.assets[]` (`provider`, `license`, `original_url`):

- in the description: a "Footage" and a "Music" section listing every source that needs attribution, with links,
- in the end credits if the licence requires on-screen credit,
- public-domain sources listed as a courtesy.

An asset without a licence is a blocker (it should have been caught by `technical_qc`; if not, stop here).

### 4. Metadata, Thumbnails, Chapters

- Title and three thumbnail variants per `skills/creative/title-thumbnail-trailer.md`. For a montage the thumbnail is a real frame from the film (the hero image), never a generated image that is not in it.
- Description: one paragraph that states the theme without explaining the film, then credits, then the AI disclosure line if any generated material was used (normally none in this pipeline).
- Chapters only for pieces over 2 minutes with a `three-act` shape (YouTube needs 3+ chapters of 10 s+).
- Captions: with narration, `subtitle_gen` from the narration per language (`.srt`, never burned in). Image-only montages need no caption file; on-screen text is part of the picture.

### 5. Write The Bundle

`export_bundle` per language with `video_path`, `title`, `description`, `tags`, `chapters` (if any), `subtitles_path` (if any), `thumbnail_path`, `platform` and `visibility` (`private` or `unlisted` first). It writes the `publish_log` entry with `status: "exported"`.

Store in `publish_log.metadata`:

- `hero_output` and `language_versions` (`en`, `es` paths),
- `credits` (the attribution list),
- `qc_reports` (path and verdict per master),
- `youtube_policy_checklist`.

### 6. Quality Gate

- Every shipped master has `technical_qc` `pass` (or every `warn` resolved).
- Credits cover every asset whose licence requires attribution.
- One complete package per language that was rendered.
- No burned-in subtitles; thumbnails are real frames.
- Schema-valid `publish_log`.

## Common Pitfalls

- Forgetting attribution for CC BY archive clips.
- Shipping the Spanish title over the English on-screen text.
- Treating long intentional holds as freeze errors instead of declaring them.
- Uploading directly instead of handing the user a private/unlisted package.

<!-- export-bundle-gate -->
## Export Bundle Gate (Binding)

Package every shipped master with `export_bundle`, after its last `technical_qc` run; never hand-write the export folder or the `publish_log` entry. The tool reads `<master>.qc.json` (or `qc_report_path`) and refuses a master with no report, a report of different bytes, or a `block` verdict. A `warn` verdict ships only with `qc_exception` (`reason` plus the `decision_id` of the `qc_exception` entry in `decision_log`). Any change to the master after the check, `audio_master` included, voids the report: run `technical_qc` again. One `export_bundle` call per master.

<!-- cold-review-export -->
## Cold Review At Export (Binding)

Pass `pipeline` with this manifest's name to `export_bundle`. The tool refuses a master with no `<master>.cold.json`, a review of different bytes, or a `revise` verdict. An `escalate` verdict ships only with `cold_exception` (`reason` plus the `decision_id` of the user's `cold_exception` decision in `decision_log`).

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
