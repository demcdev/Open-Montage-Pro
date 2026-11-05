# Proposal Director - Character Animation Pipeline

## Goal

Present character-animation concepts that are honest about local rigged motion,
reuse, cost, and runtime choice.

## Required Proposal Elements

Each option must include:

- characters and roles,
- visual style,
- action complexity,
- rig reuse strategy,
- sample plan,
- audio architecture,
- music plan,
- render runtime options,
- cost estimate,
- honest limitation note.

## Runtime Selection

Read `skills/meta/animation-runtime-selector.md` before recommending a runtime.

When both Remotion and HyperFrames are available:

- Remotion: best when the final composition needs deterministic React-rendered
  video, captions, audio, scene JSON, and final MP4 governance.
- HyperFrames: best when the character scene is HTML/SVG/GSAP-heavy and benefits
  from web-native authoring, lint, validate, and registry blocks.
- FFmpeg: post-processing only. Do not pick FFmpeg as the primary runtime for
  character acting.

Present both Remotion and HyperFrames to the user before recommending one.
Record the alternatives considered in the decision log as
`render_runtime_selection`, including why `hyperframes` was accepted or rejected.
Wait for user approval before locking `render_runtime`.

## Sample-First Rule

Before full production, propose a 10-15 second sample containing:

- one main character,
- one expression change,
- one body action,
- one camera/background treatment,
- one audio/music cue if relevant.

Do not batch-generate all assets until this sample is approved.

## Cost Honesty

Local rigging is cheap at render time but expensive in authoring complexity.
Report the difference:

- asset generation cost,
- TTS/music cost,
- local render cost,
- manual complexity risk.

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Before any concept is shown to the user, read `skills/meta/youtube-policy-gate.md` and run its **Proposal Policy Review** for every concept: made for kids, originality, AI disclosure, music plan, sensitive topics and health claims, advertiser-friendliness. Record the result in `proposal_packet.metadata.youtube_policy_review` (or in the brief's `metadata` when this pipeline has no proposal packet). Never present a concept with a `blocker`. Channel standards: no burned-in subtitles; English and Spanish audio.

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

- `skills/meta/budget-and-model-routing.md` — classify shots by tier (premium models only on hero shots), estimate with real `estimate_cost`, fill `cost_estimate` and agree the cap; run paid calls through `cost_tracker` (estimate → reserve → reconcile).

---

<!-- brief-creativo -->
## Creative Brief (Binding)

Before closing this stage, read `skills/meta/creative-intake.md` and fill `proposal_packet.metadata.brief_creativo` for the selected concept: logline, type, audience, emotional goal, what is at stake, conflict, transformation, tone, format, target duration, narrator, references, constraints and which answers were inferred. Show at least the logline, what is at stake and the transformation with the concept; the approval of this stage's gate approves the brief. The script stage does not start without it.

---

<!-- technique-selector -->
## Technique Selection (Binding)

Once the concept is chosen, and before locking the composition mode or the render runtime, read `skills/meta/technique-selector.md` and fill `proposal_packet.production_plan.technique_stack`: the techniques from `skills/creative/technique-catalog.md` this piece will use, each with its purpose, how it runs here and its fallback. Show the stack with the production plan and log a `technique_selection` decision with the options you discarded. The approval of this stage's gate approves the stack.
