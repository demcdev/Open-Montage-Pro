# Compose Director - Avatar Spokesperson Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

Render the final spokesperson outputs. The bar is simple: the presenter must look stable, speech must be clear, and subtitles or support cards must not crowd the frame.

## Runtime Routing (HARD CONSTRAINT — Remotion only)

Phase 1 deferred from HyperFrames. `edit_decisions.render_runtime` must be `"remotion"`. This pipeline depends on the Remotion `TalkingHead` composition and `remotion_caption_burn` — both have no HyperFrames parity in Phase 1.

- If `edit_decisions.render_runtime == "hyperframes"`, stop. Re-open the idea stage and surface the constraint. Silent rewrite is a governance violation.
- Per AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)": the lock to remotion is NOT an excuse to skip the conversation. The user deserves to know that HyperFrames exists as a runtime and why it isn't viable for avatar-spokesperson. Log a `render_runtime_selection` decision with hyperframes `rejected_because: "TalkingHead + caption parity deferred on avatar-spokesperson"`.
- Pass `proposal_packet`/`brief` to `video_compose.execute()` for in-tool runtime-swap detection.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | What to render |
| Tools | `video_compose`, `audio_mixer`, `video_stitch`, `audio_enhance` | Render and audio finishing |
| Playbook | Active style playbook | Typography and layout rules |
| Creative skill | `skills/creative/video-stitching.md` | How to assemble clips and chain generated ones |

## Process

### 1. Render The Hero Cut First

Prefer one strong master before derivatives. Compose:

- presenter video,
- subtitles,
- lower-thirds,
- CTA cards,
- mixed narration.

### 2. Keep The Frame Clean

Subtitle and CTA placement matter more here than flashy transitions. Leave the face and mouth region unobstructed.

### 3. Verify Mouth Timing And Audio

If the avatar path used lip sync or audio-driven talking head, check:

- mouth timing,
- face artifacts,
- drift on long sections,
- audio clarity.

### 4. Verify Every Output

Record important findings in:

- `render_report.verification_notes`
- `render_report.warnings`
- `render_report.metadata.variant_notes`

### 5. Quality Gate

- the output file is valid,
- speech is clear,
- subtitles stay readable,
- the presenter remains visually stable.

## Common Pitfalls

- Letting subtitles cover the chin or mouth area.
- Shipping a long lip-sync render without spot-checking drift.
- Making derivative crops that cut off the presenter or CTA.

---

<!-- layout-audit-gate -->
## Layout Audit Gate (Binding)

`video_compose` and `hyperframes_compose` audit the composition before rendering and stop on lasting layout problems: text off canvas, cut off, on top of other text, or hidden by a graphic. Fix the composition, or declare an intentional case per `skills/meta/layout-audit.md`. `skip_layout_audit` is for drafts only, and the report `<render>.layout.json` must exist for delivery.

<!-- cold-review-gate -->
## Cold Review Gate (Binding)

After `audio_master` and `technical_qc`, run `skills/meta/cold-review.md` on the final master: `cold_review` `prepare`, the `cold-viewer` agent with only the packet path, then `cold_review` `record`. `revise` means fix and review once more; `escalate` means stop and let the user decide. Any change to the master voids the review.

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/core/loudness-mastering.md` — master the final mix with `audio_master` (two-pass, linear) to the delivery preset; never ship a single-pass draft level.
- `skills/meta/technical-qc-gate.md` — run `technical_qc` on every render shown to the user and on the final master; `block` stops delivery, every `warn` is opened and resolved. Declare planned silences/holds in `edit_decisions.metadata.intentional_ranges`.
- `skills/core/delivery-specs.md` — destination specs (YouTube, Shorts, Reels, TikTok), one complete version per language, SRT/VTT rules and chapters; never burn subtitles.
- `skills/creative/film-look-finishing.md` — finish with `film_look` (preview one frame first); intensity follows the style (`flat_vector` is almost untouched), match color between models before adding texture, and always write BT.709 tags.
