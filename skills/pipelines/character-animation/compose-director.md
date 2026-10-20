# Compose Director - Character Animation Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## Goal

Render the approved character animation and prove it was reviewed.

## Runtime Routing

First read `edit_decisions.render_runtime`. It must match the runtime locked in
proposal unless a `render_runtime_selection` decision explicitly changed it.

- `remotion`: stage assets into `remotion-composer/public`, build composition
  JSON, render via `video_compose`.
- `hyperframes`: materialize a HyperFrames workspace and let `video_compose`
  delegate to `hyperframes_compose`. `hyperframes lint` and `validate` must pass.
- `ffmpeg`: only for post-processing or simple video assembly; not enough for
  character acting by itself.

## Review Workflow

1. Run `character_rig_renderer` to produce or refresh the HyperFrames package.
   The browser preview is a QA/debug artifact only, not the render path.
2. Verify the renderer emitted a HyperFrames `workspace_path`, composition HTML,
   `asset_manifest`, and `edit_decisions.render_runtime: "hyperframes"` handoff.
3. Run `character_animation_reviewer` against rig, poses, timeline, and preview.
4. Render final video through `video_compose` using the renderer handoff or the
   approved Remotion/HyperFrames package. The deliverable path is
   `projects/<project-name>/renders/final.mp4`, matching the standard
   OpenMontage project convention.
5. Run standard `final_review`: ffprobe, frame sampling, visual spotcheck, audio
   spotcheck, promise preservation.

## Browser QA

When Playwright is available:

- open the preview,
- capture opening/middle/end frames,
- check for console errors,
- verify characters are visible,
- compare frame deltas to ensure motion exists.

When Playwright is unavailable, use static artifact checks and FFmpeg frame
sampling, and report the reduced confidence.

## Quality Bar

Do not present the output as complete when `character_qa_report.status` is
`revise` or `fail`.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/core/loudness-mastering.md` — master the final mix with `audio_master` (two-pass, linear) to the delivery preset; never ship a single-pass draft level.
- `skills/meta/technical-qc-gate.md` — run `technical_qc` on every render shown to the user and on the final master; `block` stops delivery, every `warn` is opened and resolved. Declare planned silences/holds in `edit_decisions.metadata.intentional_ranges`.
