# Edit Director - Character Animation Pipeline

<!-- channel-standard-no-burned-subtitles -->
> **Channel standard override: no burned-in subtitles.** This overrides any instruction in this skill that enables, requires or burns subtitles or captions into the video (Remotion caption props, FFmpeg burn, "subtitles are mandatory"). Set `edit_decisions.subtitles.enabled = false`, pass no captions to the composition, and export `.srt` / `.vtt` per language (for example with `subtitle_gen`) to upload to YouTube. See `skills/meta/youtube-policy-gate.md` → Channel Standards. Only exception: the user explicitly asks for burned-in captions for one specific video.

## Goal

Produce `edit_decisions` and `action_timeline`.

## Process

1. Carry `render_runtime` forward from the approved proposal.
2. Convert scene beats into timed character actions.
3. Add anticipation, hold, action, and follow-through where appropriate.
4. Align mouth/gesture beats to dialogue or music.
5. Keep action density readable.

## Timing Pattern

Most acting beats need:

```text
anticipation -> action -> hold/reaction -> settle
```

Do not animate everything continuously. Holds are part of acting.

## Tool Use

Use `action_timeline_compiler` for a first pass, then revise the timeline if the
acting or rhythm is weak.

## Quality Bar

Every scene has timed actions. Every action maps to a pose, action cycle, or
procedural effect that the renderer can understand.

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
