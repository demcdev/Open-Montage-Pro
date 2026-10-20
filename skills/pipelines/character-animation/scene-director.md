# Scene Director - Character Animation Pipeline

## Goal

Produce a `scene_plan` where each scene is feasible for rigged character
animation.

## Scene Planning Fields

For each scene, include:

- character IDs,
- emotional beat,
- action sequence,
- camera/framing,
- background,
- props,
- effects,
- required assets,
- transition notes.

Use `type: "character_scene"` for rigged character acting scenes. Store
character-specific detail in `character_actions`; do not put per-scene acting
data in arbitrary metadata because the shared `scene_plan` schema rejects
unknown per-scene fields.

## Complexity Budget

Prefer fewer, stronger shots:

- one establish,
- one action beat,
- one reaction beat,
- one resolution beat.

Avoid scenes that require many unique views or complex physical contact unless
the user approved that complexity.

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

- `skills/meta/production-bible.md` — characters, wardrobe states, locations, light map and references come from the project bible; run its continuity check on sampled frames.
- `skills/meta/shot-list-storyboard.md` — one entry per shot with `shot_language` filled, one keyframe per shot, and the one-frame → board → 30 s approval ladder before producing.
- `skills/creative/cinematography.md` — scene coverage, 180° rule and eyelines, lens and light decisions; the speaking character is on screen.
