# Edit Director - Cinematic Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

This stage turns the beat map into a paced cinematic timeline. Rhythm and restraint matter more than effect count.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["assets"]["asset_manifest"]`, `state.artifacts["scene_plan"]["scene_plan"]`, `state.artifacts["script"]["script"]` | Assets, hero frames, beat map |
| Playbook | Active style playbook | Typography and transition consistency |

## Process

### 1. Cut By Emotion First

Cuts should follow:

- emotional emphasis,
- reveal timing,
- musical turns,
- visual contrast.

Do not optimize only for information density.

### 2. Protect Strong Moments

If a look, line, or gesture is doing the work, let it live. Do not over-cover it with extra inserts.

### 3. Use Sound To Push The Edit

Ambience, impacts, dropouts, and music changes should help create momentum between scenes.

### 4. Use Metadata For Timing Logic

Recommended metadata keys:

- `beat_timing`
- `audio_turns`
- `title_card_windows`
- `reframe_notes`

### 5. Quality Gate

- the emotional arc is intact,
- reveals land clearly,
- title cards are sparse and timed with intent,
- strong moments are not buried under coverage.

## Common Pitfalls

- Overcutting emotional material.
- Using speed ramps or flashy transitions by default.
- Letting title cards replace editorial clarity.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/creative/editing-craft.md` — cut types (J/L, on action, match, reaction), rhythm, humor cuts; use `cut` for every straight cut (other strings render as fades).
- `skills/creative/audio-post-cinema.md` — five sound layers, per-scene sound map in `edit_decisions.metadata.sound_map`, licensed sources only.

---

<!-- technique-stack -->
## Technique Stack (Binding)

Build `edit_decisions` from the approved `proposal_packet.production_plan.technique_stack`: cuts, transitions, camera and sound follow it, and an `accent` technique appears only where the stack places it. If a tool fails, apply that technique's `fallback`; any other change needs a new `technique_selection` decision.
