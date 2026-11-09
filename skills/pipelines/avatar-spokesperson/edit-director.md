# Edit Director - Avatar Spokesperson Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## When To Use

Turn the planned presenter scenes and produced assets into a coherent spokesperson timeline. The quality bar is steady delivery, readable support layers, and a clear CTA landing.

## Process

### 1. Cut The Presenter Track First

Assemble the core spokesperson performance before adding support layers. If the presenter cut is weak, extra graphics will not rescue it.

### 2. Add Support Layers Sparingly

Use overlays only where they help:

- short proof points,
- product names,
- pricing or feature cards,
- CTA reinforcement,
- subtitles.

### 3. Respect Spoken Rhythm

Keep pauses where they help emphasis. Do not trim so tightly that the avatar feels rushed or robotic.

### 4. Plan Deliverables Clearly

Recommended metadata keys:

- `hero_cut_order`
- `cta_frame_range`
- `overlay_timing_map`
- `variant_decisions`

### 5. Quality Gate

- the presenter remains the anchor,
- overlays are timed cleanly,
- scene transitions are calm and intentional,
- the CTA lands once and clearly.

## Common Pitfalls

- Overcutting to simulate energy.
- Letting captions, side panels, and lower thirds compete for the same area.
- Ending without a clean CTA hold.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/creative/editing-craft.md` — cut types (J/L, on action, match, reaction), rhythm, humor cuts; use `cut` for every straight cut (other strings render as fades).

---

<!-- technique-stack -->
## Technique Stack (Binding)

Build `edit_decisions` from the approved `brief.metadata.technique_stack`: cuts, transitions, camera and sound follow it, and an `accent` technique appears only where the stack places it. If a tool fails, apply that technique's `fallback`; any other change needs a new `technique_selection` decision.

---

<!-- reference-skills -->
## Reference Skills

- `skills/creative/sound-design.md` — Ducking, music choice and SFX timing for voice-led pieces

<!-- sound-plan -->
## Sound Plan (Binding)

Follow `skills/creative/sound-design.md` and write `artifacts/sound_plan.json`: what sounds when, by narration word or by second. Pick effects with `sound_library`, then call it with `operation: "resolve"` and pass the tracks to `audio_mixer`. `export_bundle` refuses a narrative project with no plan, unless a `sound_exception` decision records why this video goes without one.
