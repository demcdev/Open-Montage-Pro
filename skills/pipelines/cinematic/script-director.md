# Script Director - Cinematic Pipeline

## When To Use

This stage builds the beat map, selected lines, title-card copy, and reveal structure for the cinematic piece. You are shaping rhythm, not writing a dense explainer.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["proposal"]["proposal_packet"]` | Emotional arc and source truth |
| Tools | `transcriber`, `scene_detect` | Optional dialogue mining and source review |

## Process

### 1. Build A Beat Map First

Use a simple structure:

- hook,
- escalation,
- reveal,
- landing.

If the piece is longer, add one midpoint turn. Do not let it become essay-shaped.

### 2. Use Dialogue Sparingly

If source speech exists, use `transcriber` to find:

- strong standalone lines,
- emotional phrases,
- concise declarations,
- reveal phrases.

If there is no useful dialogue, keep the script title-led or narration-led and say so in metadata.

### 3. Keep Title Cards Short

Title-card copy should feel trailer-like:

- fewer words,
- more contrast,
- more whitespace,
- more timing precision.

### 4. Store Beat Truth In Metadata

Recommended metadata keys:

- `beat_map`
- `dialogue_selects`
- `title_card_copy`
- `music_turns`
- `silence_windows`

### 5. Quality Gate

- the beat map escalates cleanly,
- dialogue and title cards do not explain the same thing twice,
- the reveal lands distinctly,
- the landing gives the viewer a final feeling or action.

### Mid-Production Fact Verification

If you encounter uncertainty during script writing:
- Use `web_search` to verify factual claims before committing them to the script
- Use `web_search` to find reference images for visual accuracy
- Log verification in the decision log: `category="visual_accuracy_check"`

Every factual claim in the script should be traceable to the `research_brief`.
If you make a claim that isn't in the research, do additional research and
add the source. Do not invent statistics, dates, or attributions.

## Common Pitfalls

- Writing full explanatory paragraphs instead of beats.
- Using too many title cards.
- Revealing the best moment too early.

<!-- guionista-skill -->
## Guionista Skill (Binding)

Before writing or rewriting the script, read `skills/meta/guionista-core.md` and `skills/meta/guionista-ficcion-animada.md`. They set the hook, the open-loop ledger, humor, the cliffhanger, pacing (words per minute by format) and the delivery rules (valid `script` artifact plus production table). The YouTube Policy Gate and this pipeline's contract win over them if they conflict.

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Before checkpointing the script, apply the **script** row of `skills/meta/youtube-policy-gate.md`: a source for every factual claim, an honest hook, sensitive context inside the narration, no real-person likeness, no "expert" persona for health, legal or finance advice. Add `metadata.policy_notes`. Keep on-screen text language-neutral when the video has more than one audio language.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.

<!-- pre-render-review -->
## Pre-Render Review (Binding)

Before generating any voice, write at least three different openings and a retention map, then run the `script` moment of `skills/meta/pre-render-review.md`. Show the user the openings and the one the reviewer chose. Fix the script here: after the voice exists, every change costs another approval.

<!-- channel -->
## Channel (Binding)

This video belongs to the owner's channel unless the brief says otherwise. Read `channel/channel.yaml` before writing: narrate for its voice (`voice`), follow its `format` (the viewer is "tú", a detail planted in the opening pays off at the end, one drawing per line, the close asks for the next topic), and plan the viewer character into the opening and the payoff. Departing from the channel needs a `playbook_override` or `voice_selection` decision with the reason.
