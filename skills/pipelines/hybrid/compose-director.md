# Compose Director - Hybrid Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

Render the hybrid project so source media, support graphics, and audio all remain coherent across outputs.

## Runtime Routing (MANDATORY first step)

Read `edit_decisions.render_runtime`. Hybrid work typically sticks with Remotion because source footage + React support overlays compose cleanly in one pass:

- **`render_runtime="remotion"`** — default. Source footage via `<OffthreadVideo>`, support graphics as React components, one render.
- **`render_runtime="hyperframes"`** — pick only when the support layer is HTML/GSAP-native (e.g., animated text callouts, registry blocks). Source footage is still possible via `<video class="clip">` but lose some of the Remotion component stack. See `skills/core/hyperframes.md`.
- **`render_runtime="ffmpeg"`** — rare on this pipeline; implies no generated support layer.

Silent runtime swap is a CRITICAL governance violation. Escalate blockers per AGENT_GUIDE.md before substituting.

**Pass `proposal_packet` to `video_compose.execute()`** so the tool's in-tool swap-detection check runs against the proposal directly instead of being `skipped`.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | Edit logic and support assets |
| Tools | `video_compose`, `audio_mixer`, `video_stitch`, `video_trimmer`, `color_grade`, `audio_enhance` | Final assembly and polish |
| Playbook | Active style playbook | Output consistency |
| Creative skill | `skills/creative/video-stitching.md` | How to assemble clips and chain generated ones |
| Core skill | `skills/core/color-grading.md` | Color profiles, LUTs and contrast rules |

## Process

### 1. Verify Source And Support Balance

The final render should still look like a source-led video with support, not a collage of unrelated systems.

### 2. Check Variant Integrity

For each output variant, verify:

- crop safety,
- text safety,
- subtitle legibility,
- audio consistency.

### 3. Keep Audio Coherent

Source dialogue, narration, music, and effects should feel like one mix, not separate layers fighting for space.

### 4. Use Render Metadata

Recommended metadata keys:

- `variant_outputs`
- `balance_checks`
- `subtitle_checks`
- `audio_notes`

## Common Pitfalls

- Good master cut, broken platform variants.
- Support graphics clipping in vertical exports.
- Audio loudness shifting between source and generated sections.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/core/loudness-mastering.md` — master the final mix with `audio_master` (two-pass, linear) to the delivery preset; never ship a single-pass draft level.
- `skills/meta/technical-qc-gate.md` — run `technical_qc` on every render shown to the user and on the final master; `block` stops delivery, every `warn` is opened and resolved. Declare planned silences/holds in `edit_decisions.metadata.intentional_ranges`.
- `skills/core/delivery-specs.md` — destination specs (YouTube, Shorts, Reels, TikTok), one complete version per language, SRT/VTT rules and chapters; never burn subtitles.
- `skills/creative/film-look-finishing.md` — finish with `film_look` (preview one frame first); intensity follows the style (`flat_vector` is almost untouched), match color between models before adding texture, and always write BT.709 tags.
