# HyperFrames Skills — Provenance

The HyperFrames skills under `.agents/skills/` (mirrored in `.claude/skills/`) are
vendored from the upstream HyperFrames monorepo:

- **Source**: https://github.com/heygen-com/hyperframes
- **Vendored commit**: `0c6c7fc` (`chore: release v0.9.26 (#7421)`, 2026-11-08)
- **Vendored tag**: `v0.9.26`
- **Vendor date**: 2026-11-09

`hyperframes_compose` reads the tag above and reports a `skills_version_note`
when the CLI that `npx hyperframes` resolves is a different release, because
upstream ships the skills to match the CLI that runs them.

## What's vendored

The published core set, plus the Remotion port skill, copied unmodified from
`skills/` at the tag:

| Skill | Use |
|---|---|
| `hyperframes` | Read first: the render contract, the work loop, and `references/` by kind of video (launch, explainer, music, data, vertical, 3D, character; film, motion, format, runtimes, captions, sound, story, spec, review). |
| `hyperframes-cli` | The CLI by job: init, capture, lint, `check`, snapshot, timeline edits, preview, render, doctor. |
| `hyperframes-registry` | About 450 blocks and components installed with `hyperframes add`. |
| `media-use` | Music, SFX (19 bundled Pixabay-licence files), images, voice, transcripts, cutouts, `media-treatment` grades. |
| `remotion-to-hyperframes` | Porting Remotion source, only on an explicit request. |

## Retired at this re-vendor (v0.7.17 → v0.9.26)

- Folded upstream into `hyperframes` / `media-use`: `hyperframes-core`,
  `hyperframes-animation`, `hyperframes-creative`, `hyperframes-media`.
- No longer published upstream, removed here: `music-to-video` (now
  `references/types/music.md` + `hyperframes beats`), `website-to-video` (now
  `hyperframes capture` + `references/film.md`), `motion-graphics` (now
  registry blocks + `references/overlays.md`).
- The only OpenMontage edit to the old copies, the expressive narration
  contract in `hyperframes-media/references/tts.md`, already lives in
  `skills/meta/voice-performance-director.md`.

## Intentionally NOT vendored

`figma`, `slideshow`, `reverse-any-video` and `style-sampling` (the last two
need HyperFrames Pro), and the repo-internal skills under upstream's
`.agents/skills/`.

## OpenMontage rules on top

See `skills/core/hyperframes.md`: no usage beacon (telemetry stays off), no
HeyGen sign-in or paid features without approval, gate with `check`.

## Re-sync instructions

```bash
TAG=v0.9.26   # the release to vendor; match the CLI npx resolves
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$TAG" --filter=blob:none --sparse \
  https://github.com/heygen-com/hyperframes.git /tmp/hf
git -C /tmp/hf sparse-checkout set skills
# For each vendored skill: `git rm -r` the old copy in .agents/skills and
# .claude/skills, copy /tmp/hf/skills/<skill> into both, keep this file, and
# update the commit, tag and date above.
```
