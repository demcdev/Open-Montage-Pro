# Asset Director - Character Animation Pipeline

## Goal

Produce `asset_manifest` with character parts, backgrounds, props, audio, music,
and preview artifacts.

## Layer 3 Gate

Before authoring or generating animation assets, read the relevant Layer 3 skills:

- `character-rigging`
- `svg-character-animation`
- `pose-library-design`
- `canvas-procedural-animation` when p5/canvas effects are used
- `character-animation-qa` before review
- `gsap-core`, `gsap-timeline`, and `gsap-react` for GSAP/Remotion work
- `remotion` and `remotion-best-practices` for Remotion render work
- `hyperframes` and `hyperframes-cli` for HyperFrames work

Before image/TTS/music generation, read the tool's `agent_skills` from the
registry.

## Asset Organization

Write character assets under:

```text
projects/<project-name>/assets/characters/<character-id>/
```

Use subfolders:

```text
parts/
poses/
previews/
```

Generated backgrounds go under:

```text
projects/<project-name>/assets/backgrounds/
```

## Process

1. Produce or source only the parts required by `rig_plan`.
2. Keep each moving part separate.
3. Preserve transparent backgrounds for parts.
4. Record prompts, seeds, providers, and model names.
5. Build a small preview before full asset expansion.

## Lessons From Production (2026-10)

- **`character_rig_renderer` only draws a generic placeholder body** (round head,
  simple limbs). Use it for quick rig smoke tests, never as the character in a
  delivered video. For an approved or existing character, build the SVG by parts
  from its source artwork (one `<g>` per joint with an explicit `data-pivot`) and
  drive it with the poses in `pose_library`. Say so in the asset notes.
- **Two-segment limbs show a seam at the elbow/knee** (the child's outline is drawn
  over the parent's fill). Repaint the last ~35 % of the parent fill after the
  child group. See `.agents/skills/character-rigging/SKILL.md`.
- **Write the rotation sign convention down.** If pose data uses mirrored
  "anatomical" values (raise = positive on both sides), store the per-joint sign
  table next to the renderer and in `pose_library.metadata`; one wrong sign turns a
  selfie arm into an arm across the head.
- **Props follow the bone they hang from.** Draw hand props along the forearm
  direction in rest pose, not in the pose where they were first drawn.
- **Look for music in more than one place.** Users drop tracks in `music_library/`
  or straight into `projects/<id>/assets/music/`. Check both before saying a track
  is missing, and record its license in `assets/music/LICENSES.md`.
- **Keep the generators with the project.** Hand-authored (atelier) compositions
  are produced by scripts; save them in `projects/<id>/scripts/`, never only in a
  temporary scratchpad, or the video cannot be regenerated or edited later.
  `projects/` is gitignored: back it up with the rest of the production history.
- **Climb the ladder:** risky-pose sheet → one test frame per risky scene → 30 s
  validation → remaining scenes. Each rung is a human review.

## Quality Bar

All parts referenced by `rig_plan` must exist before compose. Missing parts are a
blocker unless the action timeline removes the action requiring them.

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Apply the **assets** row of `skills/meta/youtube-policy-gate.md`: record `license` and `source_tool` for every asset; music only from the YouTube Audio Library, our own music, or a source licensed for monetizing on YouTube (keep the evidence); no realistic AI imagery presented as real; no real-person likeness.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.

---

<!-- narration-qc-gate -->
## Narration QC Gate (Binding)

Follow `skills/meta/narration-qc.md`. Pass `language_code` to `tts_selector`, so a voice named for another language is refused unless the user approved it. The voice sample includes the riskiest lines: one or two words, foreign names, brands and figures. Run `narration_qc` on every narration track before mixing, and resolve each flagged sentence with the user, who listens to it.

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/meta/production-bible.md` — characters, wardrobe states, locations, light map and references come from the project bible; run its continuity check on sampled frames.
- `skills/creative/audio-post-cinema.md` — five sound layers, per-scene sound map in `edit_decisions.metadata.sound_map`, licensed sources only.
