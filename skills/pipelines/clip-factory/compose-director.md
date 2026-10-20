# Compose Director - Clip Factory Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

Render each clip and platform variant independently. The important behaviors here are consistency, batch resilience, and clear reporting of partial failures.

## Runtime Routing (HARD CONSTRAINT — Remotion or FFmpeg only)

This pipeline is Phase 1 deferred from the HyperFrames adoption schedule. `edit_decisions.render_runtime` must be `"remotion"` (default) or `"ffmpeg"` (pure-concat clip jobs with no composition). HyperFrames is NOT a valid runtime here — clip-factory depends on Remotion word-level caption burn, and HyperFrames caption parity is deferred work.

- If `edit_decisions.render_runtime == "hyperframes"`, stop. Re-open the idea stage so the user can be presented the real constraint and lock `remotion` with a `render_runtime_selection` decision that records `hyperframes` as `rejected_because: "caption-burn parity deferred on clip-factory"`.
- Per AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)": the constraint is NOT an excuse to skip the conversation. The user still gets to see that HyperFrames exists and why it isn't viable here.
- Pass `proposal_packet`/`brief` to `video_compose.execute()` so the in-tool runtime-swap check runs end-to-end.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | Clip edits and assets |
| Tools | `video_trimmer`, `video_compose`, `audio_mixer`, `color_grade` | Render pipeline |
| Media profiles | `lib/media_profiles.py` | Platform targets |

## Process

### 1. Treat Each Output As Its Own Job

One clip across three platforms is three render jobs. Name and track them explicitly.

### 2. Reuse What Can Be Shared

- shared audio mix where possible,
- shared subtitle styling,
- shared overlay assets,
- shared grading if the source needs it.

### 3. Fail Softly

If one clip or one platform variant fails:

- log it clearly,
- continue the rest of the batch,
- do not block successful exports.

### 4. Verify Every Output

Per render:

- correct duration,
- correct resolution/aspect ratio,
- no black opening frame,
- hook appears on time,
- subtitles render correctly,
- audio is present and consistent.

### 5. Use Render Report Metadata

Recommended metadata keys:

- `job_index`
- `failed_jobs`
- `shared_intermediates`
- `platform_groupings`

## Common Pitfalls

- Rendering sequentially without reason when jobs are independent.
- Treating a failed clip as a reason to stop the batch.
- Letting one platform variant quietly use the wrong framing or subtitle zone.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/core/loudness-mastering.md` — master the final mix with `audio_master` (two-pass, linear) to the delivery preset; never ship a single-pass draft level.
- `skills/meta/technical-qc-gate.md` — run `technical_qc` on every render shown to the user and on the final master; `block` stops delivery, every `warn` is opened and resolved. Declare planned silences/holds in `edit_decisions.metadata.intentional_ranges`.
- `skills/core/delivery-specs.md` — destination specs (YouTube, Shorts, Reels, TikTok), one complete version per language, SRT/VTT rules and chapters; never burn subtitles.
