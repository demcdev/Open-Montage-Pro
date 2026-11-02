# YouTube Policy Gate — Meta Skill

## When to Use

Every production that could be published on YouTube. Treat **every** video as YouTube-bound unless the user says otherwise. The goal is simple: nothing we make should get a channel demonetized, limited, struck or terminated.

This gate is binding in every pipeline. It runs at the **first creative stage (idea / proposal)**, again at **script** and **assets**, a last time at **publish**, and it is part of **every self-review** (see `skills/meta/reviewer.md` → "YouTube Policy Review").

## Authority and Freshness

- Reference: `docs/youtube-policy-reference.md` — a Spanish synthesis of YouTube's official help pages, checked on **2026-10-11**. When it and the official English page disagree, the official page wins.
- If today is more than **90 days** after the reference date, say so to the user before relying on it, and re-check the official pages that matter for the brief (`support.google.com/youtube/answer/1311392` monetization policies, `…/6162278` advertiser-friendly, `…/2801964` dangerous content, `…/9528076` made for kids).
- Not covered by the reference (look up the official page before relying on anything): automatic dubbing and multi-language audio eligibility, comments / live / community posts policies, and the Google Ads policies for branded content. Facts verified on 2026-10-19: automatic dubbing is skipped when the video has little or no speech, speech that is too fast, copyright claims, or an unsupported or undetected language; a video can only have one dub per language, and an automatic dub must be deleted before uploading your own.

## What We Check, Stage by Stage

| Stage | Check | Record in |
|---|---|---|
| research | Topic risk screen: kids, health / safety / medical claims, violence, crime, hate, tragedies, regulated goods. Health and safety claims need **primary sources** (government health or food-safety authorities), and the source must match the **audience's country**. | `research_brief.metadata.policy_screen` |
| idea / proposal | Run the **Proposal Policy Review** below for every concept before the user chooses. | `proposal_packet.metadata.youtube_policy_review` |
| script | Every factual claim has a source. The hook does not promise what the video does not deliver. No fake urgency or fear. Sensitive context lives **inside the narration or visuals**, not only in the title. No real person's name, face or voice. No "expert" persona giving health, legal or finance advice. | `script.metadata.policy_notes` |
| scene_plan / assets | Every asset has a license and a source (`asset_manifest.assets[].license`, `source_tool`). Music only from the YouTube Audio Library, our own music, or a licensed source whose terms cover monetizing on YouTube. Keep the evidence. No realistic AI imagery presented as real. Thumbnails are honest. | `asset_manifest` |
| edit / compose | **Burned-in subtitles are off** (`edit_decisions.subtitles.enabled = false`, no caption-burn overlays). Subtitles are exported as separate `.srt` / `.vtt` files per language. No mirrored, sped-up or pitch-shifted third-party material. | `edit_decisions`, `render_report` |
| publish | Run the **Publish Checklist** below. | `publish_log.metadata.youtube_policy_checklist` |

## Proposal Policy Review (idea / proposal stage)

For each concept, answer in the proposal and write the result to `metadata.youtube_policy_review`:

1. **Made for kids?** Animated characters, stories or songs that appeal to children can make a video "made for kids" even if it is "family" content. The creator is legally responsible for the call (COPPA). Record `yes`, `no` or `undecided` with a reason, and **ask the user** if it is undecided. Concepts with adult themes (death, crime, violence) must not target kids.
2. **Originality.** Could this video be swapped for another one in the same series without the viewer noticing? If yes, rework the concept. A series is fine only if each video has its own story, angle and concept. Plan a human-looking release cadence, not mass production.
3. **Pattern, not copy.** We may model another channel's structure and pacing, but never copy its scripts, titles, thumbnails, characters, name or branding.
4. **AI disclosure.** Realistic content generated or altered with AI must be declared. Non-realistic animation does not need it. A generic synthetic narration voice is not explicitly covered by the reference: when in doubt, declare, which does not limit monetization. Cloning a real person's voice is never allowed.
5. **Music plan.** Source and license evidence (see Assets row). A copyright claim also blocks automatic dubbing.
6. **Sensitive topics and health claims.** List them, with the primary source and the jurisdiction they come from. Localize them for each audio language / country.
7. **Advertiser-friendliness.** Violence, crime, tragedies, medical claims, strong language in title or thumbnail.

`status` is `pass`, `warn` or `blocker`. A `blocker` cannot be approved; propose a compliant alternative instead.

## Publish Checklist

Write the answers to `publish_log.metadata.youtube_policy_checklist` and show them to the user at the gate:

- [ ] Upload as **private or unlisted first**, wait for the checks, then publish.
- [ ] "Made for kids": answered and consistent with the proposal.
- [ ] "Altered or synthetic content" disclosure: decided and recorded.
- [ ] Paid promotion, sponsorship or affiliate links: declared if present.
- [ ] Title and thumbnail match what the video delivers. No gore, vulgar text or impersonation.
- [ ] Description: safe links only, chapters, sources for factual claims.
- [ ] Captions uploaded as `.srt` / `.vtt` per language. Nothing burned into the video.
- [ ] Audio languages: custom tracks (needs the Languages tab / advanced features) or automatic dubbing, never both for the same language. If neither is available, a separate upload.
- [ ] Music and asset licenses stored with the project.
- [ ] Production history (research, script drafts, decisions, assets) is kept as proof of authorship. `projects/` is gitignored, so back it up.
- [ ] Release cadence is reasonable and the series is not templated.

## Channel Standards (set by the user)

- **No burned-in subtitles in any video.** Captions are configured in YouTube from `.srt` / `.vtt` files. (Rule set 2026-10-19.) Several pipeline directors still say subtitles are mandatory or burned in; this standard overrides them (each edit and compose director carries an override note). The only exception is a specific video for which the user explicitly asks for burned-in captions.
- **No words on screen in any video (No-Text Rule, set 2026-11-01).** Only numbers, units, symbols, flags, icons and arrows; the full rule and exception are in `AGENT_GUIDE.md` → "No-Text Rule". It replaces the earlier "almost language-neutral text" standard. Check it at `scene_plan`, `assets` (no generated image may contain words), `edit` and `compose`; a violation is a **Warning** in review and a **Blocker** at publish.
- **Audio languages:** the user records in Spanish; YouTube dubs automatically into English, Portuguese and Arabic. One video, several audio tracks, which is why the picture carries no words.
- Health and food-safety facts are checked against the authority of the audience's country, not only the US.

## When a Request Conflicts

If a user idea or a provider default clashes with this gate, **warn before executing**, explain the rule in one or two sentences, and propose a compliant alternative. Do not silently drop the idea and do not silently ship it.

## Review Severity

- **Blocker:** unlicensed music, undisclosed realistic AI, real-person likeness, misleading thumbnail or title, made-for-kids unresolved, graphic violence or hate, unverified health claims, copied scripts or thumbnails.
- **Warning:** templated series, thin sources, one-country sources for a multi-country audience, aggressive cadence, borderline sensitive themes.
