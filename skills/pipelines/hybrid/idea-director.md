# Idea Director - Hybrid Pipeline

## When To Use

Use this pipeline when the project combines real source media with support visuals: interviews plus diagrams, footage plus overlays, screen recording plus branded graphics, or source-led edits with generated inserts.

Hybrid is not a catch-all. Your first job is to define what stays primary.

## Runtime Selection (MANDATORY — present both runtimes)

Before locking the production plan, decide `render_runtime` with the user. Hybrid supports BOTH Remotion and HyperFrames; neither is an auto-default. Follow the contract in AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)":

1. Query `video_compose.get_info()["render_engines"]`. If both `remotion` and `hyperframes` are `True`, present both to the user with brief-specific analysis:
   - **Remotion** — fits when source footage dominates and support layers are React scene components (chart, callout, text card). Remotion composes video clips + React overlays in one pass via `<OffthreadVideo>`.
   - **HyperFrames** — fits when support layers are HTML/GSAP-native (kinetic callouts, registry blocks, typographic overlays) and source footage is embedded as `<video class="clip">`.
2. Recommend one with rationale tied to the anchor medium and the shape of the support layer.
3. Wait for explicit user approval.
4. Log the choice in `decision_log` as a `render_runtime_selection` decision with BOTH runtimes in `options_considered`.

A `render_runtime_selection` decision with only one runtime in `options_considered` when both were available is a CRITICAL reviewer finding.

## Reference Inputs

- `docs/hybrid-video-best-practices.md`
- `skills/creative/storytelling.md`
- `skills/creative/video-editing.md`

## Process

### 1. Choose The Anchor Medium

Pick the storytelling anchor:

- `talking_head`
- `broll_footage`
- `screen_recording`
- `still_sequence`
- `narration_led_graphics`

### 2. Define Support Layers

Possible support layers:

- subtitles,
- diagrams,
- code visuals,
- stat cards,
- generated inserts,
- narration,
- music.

Each support layer should solve a specific problem, not just decorate the timeline.

### 3. Decide The Deliverable Mix

Common outputs:

- hero cut,
- vertical cutdown,
- square cutdown,
- chaptered version,
- ad variant.

### 4. Build The Brief

Recommended metadata keys:

- `anchor_medium`
- `source_inventory`
- `support_layers`
- `deliverable_mix`
- `missing_capabilities`
- `fallback_policy`

### 5. Quality Gate

- the anchor medium is explicit,
- support layers are justified,
- the deliverable mix fits the source inventory,
- missing capabilities are surfaced early.

## Common Pitfalls

- Calling everything hybrid without defining a primary medium.
- Planning support layers before understanding the source.
- Treating optional generated inserts as guaranteed.

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

Before closing this stage, read `skills/meta/creative-intake.md` and fill `brief.metadata.brief_creativo` for the selected concept: logline, type, audience, emotional goal, what is at stake, conflict, transformation, tone, format, target duration, narrator, references, constraints and which answers were inferred. Show at least the logline, what is at stake and the transformation with the concept; the approval of this stage's gate approves the brief. The script stage does not start without it.
