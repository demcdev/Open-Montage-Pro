# Edit Director - Hybrid Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

This stage creates the layered edit logic for a source-led video with support elements. The order matters: anchor cut first, support layers second.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["assets"]["asset_manifest"]`, `state.artifacts["scene_plan"]["scene_plan"]`, `state.artifacts["script"]["script"]` | Source/support assets and timeline intent |
| Playbook | Active style playbook | Typography and motion consistency |

## Process

### 1. Lock The Anchor Cut First

The viewer should understand the story before support overlays are added. If the anchor cut is weak, support layers will not save it.

### 2. Add Support In Priority Order

Typical order:

1. subtitles,
2. speaker or context labels,
3. diagrams or stat cards,
4. optional inserts,
5. CTA elements.

### 3. Protect Readability

Never stack too many support layers in one moment. If subtitles, labels, charts, and overlays collide, simplify.

### 4. Use Metadata For Layering Logic

Recommended metadata keys:

- `anchor_cut_notes`
- `layer_order`
- `overlay_windows`
- `variant_edit_rules`

### 5. Quality Gate

- the anchor cut works on its own,
- support layers clarify instead of distract,
- mobile readability survives,
- variants remain consistent.

## Common Pitfalls

- Trying to fix a weak cut with extra graphics.
- Letting support layers compete with the source.
- Building each platform variant as a separate editorial philosophy.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/creative/editing-craft.md` — cut types (J/L, on action, match, reaction), rhythm, humor cuts; use `cut` for every straight cut (other strings render as fades).
- `skills/creative/audio-post-cinema.md` — five sound layers, per-scene sound map in `edit_decisions.metadata.sound_map`, licensed sources only.

---

<!-- technique-stack -->
## Technique Stack (Binding)

Build `edit_decisions` from the approved `brief.metadata.technique_stack`: cuts, transitions, camera and sound follow it, and an `accent` technique appears only where the stack places it. If a tool fails, apply that technique's `fallback`; any other change needs a new `technique_selection` decision.

<!-- sound-plan -->
## Sound Plan (Binding)

Follow `skills/creative/sound-design.md` and write `artifacts/sound_plan.json`: what sounds when, by narration word or by second. Pick effects with `sound_library`, then call it with `operation: "resolve"` and pass the tracks to `audio_mixer`. `export_bundle` refuses a narrative project with no plan, unless a `sound_exception` decision records why this video goes without one.
