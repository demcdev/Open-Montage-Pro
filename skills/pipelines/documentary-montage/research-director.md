# Research Director - Documentary Montage Pipeline

## When To Use

You run after the brief is approved and before anything is written or searched for in the corpus. A montage makes claims even without narration: a title card says "1969", an end-tag states a thesis, a lower third names a place, and the juxtaposition itself implies a cause. Your job is to make every one of those true, and to scout where the footage that can carry the theme actually lives and under what licence.

You do NOT pick clips and you do NOT write the beats. You hand the script director verified facts and the asset director a map of sources.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/research_brief.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["idea"]["brief"]` | Thematic question, tone, era mix, sources allowed, end-tag plan |
| Tools | Web search, web fetch; `corpus_builder` provider menu from preflight | Fact checking and archive scouting |
| Meta | `skills/meta/guionista-documental.md` | Claims register, ethics for real people, archive licences |

## Process

### 1. List What Must Be True

Before searching, write down every statement the film will make or imply:

- the end-tag line in `brief.end_tag_plan.text` (a thesis can be arguable, but it must not rest on a false fact),
- dates, places, events and names that will appear on title cards or lower thirds,
- historical framing implied by `era_mix` ("the 1950s promised..."),
- any narration, if the brief approved it,
- juxtapositions that imply causation (factory smoke cut against a cough reads as a claim).

### 2. Verify Each Claim

For each item, find a primary source when one exists (archive catalogue, agency page, contemporary record), otherwise a reputable secondary one. Record it in `data_points[]`:

```json
{
  "claim": "The Prelinger Archives hold industrial films made between 1903 and 1987",
  "source_url": "https://archive.org/details/prelinger",
  "source_name": "Internet Archive — Prelinger Archives",
  "credibility": "primary_source",
  "usable_as": "script_anchor"
}
```

A claim you cannot source is cut or rewritten as an impression ("a city at night"), never kept as fact.

### 3. Scout The Footage Landscape

For the theme and era mix, check which collections actually have material and under what terms. Use the sources listed as `available` in the `corpus_builder` provider menu; do not plan around a source that is not configured.

| Source family | What to confirm |
|---|---|
| Archive.org (Prelinger and others) | Licence stated per item (many are public domain, some are not); whether people shown are identifiable |
| NASA, NARA, other government archives | Public-domain status and any logo or endorsement restrictions |
| Wikimedia Commons | Licence per file (CC BY / BY-SA need attribution in the credits) |
| Pexels, Pixabay, Coverr, Mixkit | Platform licence; no identifiable-person sensitive use |

Record the useful collections and search terms in `metadata.footage_sources[]` (`source`, `collection`, `search_terms`, `licence`, `attribution_required`, `notes`). The asset director turns these into corpus queries.

### 4. Real People And Sensitive Context

Archive footage shows real people. Note in `metadata.ethics_notes[]` anything the edit must respect: victims, children, private grief, people who could be ridiculed by an ironic cut (`wry` tone). `skills/meta/guionista-documental.md` sets the rule: no humor where there is pain, and no implying something about a real, identifiable person that the source does not support.

### 5. Precedents (Light)

Montage is a craft with a canon. Collect 3+ precedents for the tone and shape (essay films, tone poems, festival shorts) in `landscape.existing_content[]` and `visual_references[]`. Note what each does with holds, music and text — not to copy, to calibrate pacing.

### 6. Fill The Schema Honestly

`research_brief` was designed for explainers; map it like this:

| Field | For a montage |
|---|---|
| `topic` | The brief's topic |
| `research_date` | Today (ISO date) |
| `landscape.existing_content` | 3+ precedents (step 5) |
| `landscape.saturated_angles` / `underserved_gaps` | Overused images for this theme (the clichés to avoid) / what nobody shows |
| `data_points` | Verified claims (step 2), 3+ |
| `audience_insights` | What viewers already associate with the theme; `misconceptions` the montage must not reinforce |
| `angles_discovered` | 3+ ways to arrange the theme (motif, contrast, chronology), each `grounded_in` data points |
| `sources` | Every source used, 5+, with `reliability` |
| `metadata` | `footage_sources`, `ethics_notes`, `claims_to_cut` |

### 7. Quality Gate

- Every statement from step 1 is either backed by a `data_points[]` entry or listed in `metadata.claims_to_cut`.
- The end-tag line does not depend on an unverified fact.
- At least two available footage sources are mapped with licences.
- Ethics notes exist whenever identifiable people appear.
- Schema-valid `research_brief`.

## Common Pitfalls

- Treating a tone poem as "no facts, no research". A single wrong date on a title card is what commenters remember.
- Assuming everything on Archive.org is public domain.
- Planning around a source that preflight showed as unavailable.
- Letting a `wry` cut mock identifiable people in archive footage.

<!-- guionista-skill -->
## Guionista Skill (Binding)

Read `skills/meta/guionista-documental.md` (claims register, sources, ethics for real people and victims, archive and music licences) and `skills/meta/guionista-core.md` before verifying claims. The YouTube Policy Gate and this pipeline's contract win over them if they conflict.

<!-- youtube-policy-gate -->
## YouTube Policy Gate

Apply the **research** row of `skills/meta/youtube-policy-gate.md`: topic risk screen (kids, tragedies, violence, health claims with primary sources), and licences recorded for every archive collection you plan to use. Write it to `research_brief.metadata.policy_screen`.

---

## Gate Reminder (Binding)

This stage does not gate on human approval by default (`human_approval_default: false`). Checkpoint with `status="completed"` after review passes and continue to `script`. If you cut a claim the brief relied on (for example the end-tag), stop and ask the user before continuing.

---

<!-- transversal-skills-2026-10 -->
## Transversal Skills (Binding)

Read these before working in this stage. They are shared across pipelines; this file only says when they apply.

- `skills/meta/budget-and-model-routing.md` — confirm that the footage plan stays retrieval-first (tier 0–1 cost); any paid source or generated clip is a budget decision for the user.

---

## Research Dossier (Binding)

Before any searching in this stage, read `skills/meta/research-dossier.md` and run the research with the agent `research-dossier` (Opus, high effort). Fill the prompt's variables from the project and ask the user, with selectable buttons, for every one that is missing; never start with empty variables. Save the result as `projects/<project-id>/artifacts/research_dossier.md` and map it into the `research_brief` below. Everything in this director that conflicts with the dossier's honesty rules (open every source, no links from memory, mark unverified facts) yields to the dossier. Keep the No-Text Rule from `AGENT_GUIDE.md` in mind for any visual suggestion: numbers, symbols, flags and icons only.
