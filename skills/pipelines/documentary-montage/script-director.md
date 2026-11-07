# Script Director - Documentary Montage Pipeline

## When To Use

You turn the approved brief and the verified research into the montage's script: the beat map the scene director will turn into slots, every word that will appear on screen (title cards, lower thirds, the end-tag), and narration only if the brief approved it. In a tone poem the script is mostly **structure and silence**; the words are few, so each one must be exact and true.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["idea"]["brief"]`, `state.artifacts["research"]["research_brief"]` | Theme, tone, shape, duration, end-tag; verified claims and footage map |
| Meta | `skills/meta/guionista-core.md`, `skills/meta/guionista-documental.md` | Hook, open loops, claims register, ethics |
| Reference | `skills/pipelines/documentary-montage/executive-producer.md` | No narration and no generated clips unless approved |

## Process

### 1. Build The Beat Map

Use the brief's `shape` and duration table (idea director §3) to set the number of movements and their length. For each movement write:

- the **motif** (the recurring image idea: hands, windows, roads),
- the **emotional move** (establish → accumulate → turn → release),
- the **hold register** (short cuts vs. long holds),
- the **music turn** at its boundary (swell, drop, cut to silence).

The opening 5–10 seconds is the hook even without words: the strangest or most beautiful image of the set, not the establishing shot.

### 2. Decide The Words

Default is image only. Every word on screen competes with the image, so:

| Element | Rule |
|---|---|
| Title card | 0–1 at the start. 2–6 words |
| Movement cards | Only for a `three-act` shape, 1–3 words each |
| Lower thirds | Only where the viewer would otherwise misread place or date; each one backed by a `research_brief.data_points[]` entry |
| End-tag | The approved `brief.metadata.end_tag_plan.text`. You may confirm it is true and well-placed; **you may not change it here**. A better line goes back to the idea stage as a send-back |
| Narration | Only if the brief says so. Otherwise none, and the edit must not lean on it later |

### 3. Write The `script` Artifact

The schema is built for narration; map it like this:

- `title`: the working title. `total_duration_seconds`: `brief` duration.
- `sections[]`: one per movement (or per beat in pieces under 60 s). `id` (`m1`, `m2`, ...), `label` (movement name), `start_seconds` / `end_seconds`.
- `sections[].text`: the on-screen words of that section (title card, lower thirds joined by ` / `), the narration if approved, or `""` for an image-only section.
- `sections[].speaker_directions`: `"image only"` or the narration direction.
- `sections[].source_ref`: the `data_points[]` claim or URL behind any factual word in the section.

Beat truth goes in `metadata` (open object):

```json
{
  "narration": "none",
  "beat_map": [
    {"section_id": "m1", "motif": "windows in rain", "emotion": "solitude", "hold": "long", "music_turn": "drone enters"},
    {"section_id": "m2", "motif": "hands and umbrellas", "emotion": "small kindness", "hold": "medium", "music_turn": "pulse joins"}
  ],
  "on_screen_text": [
    {"section_id": "m1", "kind": "title_card", "en": "A MINUTE IN THE RAIN", "es": "UN MINUTO BAJO LA LLUVIA"},
    {"section_id": "m3", "kind": "lower_third", "en": "Tokyo, 1964", "es": "Tokio, 1964", "source_ref": "https://example.org/catalogue/item"}
  ],
  "end_tag": {"text": "THE CITY KEEPS ITS OWN VIGIL.", "verified": true},
  "music_turns": [{"at_seconds": 0.0, "event": "drone in"}, {"at_seconds": 58.0, "event": "cut to silence"}],
  "silence_windows": [{"start": 58.0, "end": 60.5, "reason": "breath before the end-tag"}],
  "claims_register": [{"claim": "Tokyo, 1964", "source_ref": "https://example.org/catalogue/item", "status": "verified"}],
  "policy_notes": []
}
```

- `on_screen_text` carries **both languages** for every element: the English and Spanish versions differ in their text, never in their images (`skills/core/delivery-specs.md`).
- `silence_windows` are copied by the edit director into `edit_decisions.metadata.intentional_ranges`, so `technical_qc` treats them as planned (`skills/meta/technical-qc-gate.md`).

### 4. Quality Gate

- The beat map matches the brief's shape and duration (sum of sections within 5 % of `total_duration_seconds`).
- Every factual word on screen has a `source_ref` that resolves to the research brief.
- The end-tag is the approved one, verified.
- No narration unless the brief approved it.
- Both languages are present for every on-screen element.
- Schema-valid `script`.

## Common Pitfalls

- Writing narration "to guide the viewer" in an image-only brief.
- A lower third for every clip: it turns the montage into a slideshow with captions.
- Dates or places on screen that research could not verify.
- Rewriting the end-tag here instead of sending it back to the idea stage.

<!-- guionista-skill -->
## Guionista Skill (Binding)

Before writing or rewriting the script, read `skills/meta/guionista-core.md` and `skills/meta/guionista-documental.md`. They set the hook, the claims register with sources, ethics for real people and victims (no humor where there is pain) and the licences for archive footage and music. The YouTube Policy Gate and this pipeline's contract win over them if they conflict.

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Before checkpointing the script, apply the **script** row of `skills/meta/youtube-policy-gate.md`: a source for every factual claim, an honest hook, sensitive context inside the visuals or text, no real-person likeness used to imply something the source does not support. Add `metadata.policy_notes`.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.

---

<!-- pre-render-review -->
## Pre-Render Review (Binding)

Before generating any voice, write at least three different openings and a retention map, then run the `script` moment of `skills/meta/pre-render-review.md`. Show the user the openings and the one the reviewer chose. Fix the script here: after the voice exists, every change costs another approval.

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/creative/title-thumbnail-trailer.md` — write the title and the thumbnail idea together with the hook; title cards and credits follow its timing rules.
- `skills/core/delivery-specs.md` — every on-screen text exists in English and Spanish; subtitles are never burned in.
