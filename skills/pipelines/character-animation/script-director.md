# Script Director - Character Animation Pipeline

## Goal

Write scripts as performable animation beats, not just narration.

## Process

1. Lock audio architecture:
   - music-only,
   - narrator,
   - character dialogue,
   - narrator plus character sounds/dialogue.
2. Break the story into beats that can be acted with poses.
3. For each beat, state what changes visually:
   - emotion,
   - gaze,
   - body pose,
   - prop interaction,
   - camera,
   - environment.

## Writing Rules

- Prefer short visual beats with readable holds.
- Avoid action that needs many unique hand-drawn poses unless approved.
- Dialogue should be short enough for mouth-shape approximation.
- Silent/music-led scenes need stronger physical acting notes.

## Output Notes

In the `script` artifact metadata, include:

- `audio_architecture`,
- `character_beats`,
- `required_emotions`,
- `required_actions`.

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
