# Scene Director - Hybrid Pipeline

## When To Use

You are translating the hybrid structure into a visual system that keeps the source visible and the support layers under control.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["script"]["script"]`, `state.artifacts["idea"]["brief"]` | Hybrid structure and source truth |
| Tools | `frame_sampler`, `scene_detect` | Optional source inspection |
| Playbook | Active style playbook | Layout consistency |
| Creative skill | `skills/creative/data-visualization.md` | Chart type, animation and label placement |

## Process

### 1. Keep The Anchor Medium Visible

If the piece is source-led, the source must remain visually primary in the scene plan. Do not hide the anchor behind constant overlays.

### 2. Reserve Support For Clear Jobs

Use support scenes for:

- chapter transitions,
- clarifying diagrams,
- stat emphasis,
- CTA or summary moments,
- gap-filling inserts.

### 3. Plan Variant Safety

If the project needs multiple aspect ratios, define where:

- subtitles live,
- speaker labels live,
- chart or code safe zones live,
- crop-sensitive source media becomes unsafe.

### 4. Use Metadata For Balance Rules

Recommended metadata keys:

- `anchor_rules`
- `support_rules`
- `safe_zones`
- `variant_rules`
- `overlay_density_limits`

### 5. Quality Gate

- the anchor medium stays primary where intended,
- support layers are limited and purposeful,
- aspect-ratio planning is explicit,
- no scene relies on invisible future magic.

## Common Pitfalls

- Turning source-led scenes into overlay soup.
- Forgetting variant-safe zones until compose.
- Using generated inserts for every transition.

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

---

<!-- technique-stack -->
## Technique Stack (Binding)

Plan from the approved `brief.metadata.technique_stack`. Every `primary` and `accent` technique lands in a named scene of `scene_plan`. A technique outside the stack needs a new `technique_selection` decision first; if it changes what the user approved, ask them.
