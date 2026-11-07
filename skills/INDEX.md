# OpenMontage â€" Skill Index

> For the full agent onboarding guide, see [`AGENT_GUIDE.md`](../AGENT_GUIDE.md) in the project root.

This file lists all available Layer 2 skills and documents the 3-layer knowledge architecture.

For *when* each skill is read during a production (input → concept → script → audiovisual direction → production → finishing) and which ones nothing loads today, see [`MAPA_POR_FASE.md`](MAPA_POR_FASE.md).

## Knowledge Architecture

```
Layer 1: tools/tool_registry.py          "What tools exist and what they can do"
         tools/base_tool.py               Each tool declares: capabilities, tier, status,
                                          dependencies, cost, and agent_skills[]

         â†" agent_skills[] points to â†"

Layer 2: skills/                          "How OpenMontage uses these tools"
         Project-specific conventions:     Pipeline integration, artifact mappings,
         {core,creative,meta,pipelines}/   enhancement chain order, quality checklists

         â†" references underlying tech in â†"

Layer 3: .agents/skills/                  "How the technology itself works"
         Generic API knowledge from        Correct import paths, code patterns,
         skills.sh (47 installed skills)   constraints, parameters â€" tech-agnostic
```

**How the agent uses this:**
1. The orchestrator queries Layer 1 (`tool_registry.support_envelope()`) to see what's available
2. Each tool's `agent_skills[]` field names the Layer 3 skills it relies on
3. Layer 2 skills (this directory) teach the agent OpenMontage-specific conventions
4. Layer 3 skills (`.agents/skills/`) provide generic API knowledge, loaded on-demand

## Capability Families & Tool Discovery

Every tool declares a `capability` (what it does) and a `provider` (who/what powers it). The registry groups tools by capability so agents can discover all options for a given task.

### Selector / Provider Pattern

For capability families with multiple providers (TTS, video generation), the architecture uses:
- **Selector tool** (`tts_selector`, `video_selector`, `image_selector`) — routes to the best available provider based on requirements, API key availability, and cost. Selectors auto-discover providers from the registry. Agents should default to selectors when the user hasn't specified a provider.
- **Provider tools** — call a specific provider directly. Agents use these when the user explicitly requests a provider or when the selector's routing isn't appropriate.

### Capability Family Reference

**Do not maintain a hardcoded tool list.** The registry is the single source of truth. Query it at runtime:

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"
```

Key capability families to look for in the output:

| Capability | Selector | Discovery |
|---|---|---|
| `tts` | `tts_selector` | Auto-discovers all `capability="tts"` tools |
| `video_generation` | `video_selector` | Auto-discovers all `capability="video_generation"` tools |
| `image_generation` | `image_selector` | Auto-discovers all `capability="image_generation"` tools |
| `audio_processing` | — | FFmpeg-based local tools |
| `enhancement` | — | Mixed providers |
| `analysis` | — | Mixed providers |
| `character_animation` | — | Local character specs, SVG rigs, pose libraries, action timelines, previews, and QA |
| `3d_world_generation` | — | Local semantic terrain, procedural scattering, explicit landmarks, diagnostics, and HyperFrames/Three.js fly-through workspaces |
| `3d_asset_acquisition` | — | Rights-safe local GLTF/GLB catalogs and provenance |
| `3d_asset_generation` | — | Atlas/fal textured mesh generation and reconstruction for unique scene assets |
| `3d_world_rendering` | — | Blender assembly and production rendering of detailed worlds |
| `graphics` | — | Local rendering tools |
| `music_library` | — | Discovers user-provided local tracks |
| `music_search` | — | Discovers royalty-free search/download providers |
| `music_generation` | — | Discovers paid/local generation providers |
| `subtitle` | — | Pure Python |
| `avatar` | — | Local GPU models |
| `video_post` | — | FFmpeg-based local tools |

### Adding New Tools

1. Place the tool in the correct capability folder (or create a new one under `tools/`)
2. Set `capability` and `provider` in the class definition
3. If joining a multi-provider family, the existing selector discovers it automatically
4. Attach Layer 3 skills via `agent_skills[]` and Layer 2 manuals via `usage_skills[]`
5. The registry discovers tools automatically — no manual registration needed
6. **No other files need updating** — selectors, manifests, and instructions all derive from the registry

## Core Skills

| Skill | File | Trigger | Agent Skills (Layer 3) |
|-------|------|---------|----------------------|
| FFmpeg | `core/ffmpeg.md` | Video encoding, filtering, composition | `ffmpeg`, `video-toolkit` |
| Remotion | `core/remotion.md` | React-based composition, Phase 3+ | `remotion-best-practices`, `remotion` |
| HyperFrames | `core/hyperframes.md` | HTML/CSS/GSAP composition runtime — kinetic typography, music-to-video, product promos, website capture. Vendored at v0.7.17 (2026-06-27). | `hyperframes` (router) → `hyperframes-core` (contract), `hyperframes-creative` (palette/type/narration), `hyperframes-media` (TTS/BGM/SFX/captions), `hyperframes-animation` (all motion), `hyperframes-cli`, `hyperframes-registry`, `media-use`, `motion-graphics`, `music-to-video` (beats-driven), `website-to-video`, `remotion-to-hyperframes` (migration), `gsap-core`, `gsap-timeline` |
| WhisperX | `core/whisperx.md` | Transcription with word-level timestamps — default STT (offline, free) | `speech-to-text` |
| Azure STT | (tool: `azure_stt`) | Optional cloud speech-to-text, word-level timestamps — preferred when `AZURE_SPEECH_KEY` is set | `azure-speech-to-text` |
| Azure TTS | (tool: `azure_tts`) | Optional cloud neural narration (SSML prosody, express-as styles) — same Speech key as `azure_stt` | `azure-text-to-speech` |
| Subtitle Sync | `core/subtitle-sync.md` | Subtitle timing and alignment | `remotion-best-practices` |
| Color Grading | `core/color-grading.md` | FFmpeg color profiles, LUT workflow, accessibility | `ffmpeg` |
| Loudness Mastering | `core/loudness-mastering.md` | Final audio level per platform: two-pass linear master with `audio_master`, measured and verified (YouTube −14 LUFS / −1 dBTP, podcast, broadcast); de-esser for TTS | `ffmpeg` |
| Delivery Specs | `core/delivery-specs.md` | Per-destination masters (YouTube 16:9, Shorts, Reels, TikTok), one complete EN/ES version each, SRT/VTT rules (42 chars, 17 cps), chapters; never burn subtitles | — |

## Creative Skills

| Skill | File | Trigger | Agent Skills (Layer 3) |
|-------|------|---------|----------------------|
| Video Editing | `creative/video-editing.md` | Cut decisions, pacing, rhythm | `ffmpeg`, `video-toolkit` |
| Camera & Motion Library | `creative/camera-motion-library.md` | Remotion camera moves, transitions, fx, kinetic text, split screen — anything that would otherwise sit still. Index: `docs/MOTION_CATALOG.md` | `remotion-best-practices`, `framer-motion` |
| Enhancement Strategy | `creative/enhancement-strategy.md` | Overlay placement and density | `ffmpeg` |
| Data Visualization | `creative/data-visualization.md` | Chart type selection, animation, label placement | `d3-viz`, `remotion-best-practices` |
| Video Stitching | `creative/video-stitching.md` | Multi-clip assembly, AI clip chaining, spatial composition | `ffmpeg`, `video-toolkit` |
| Video Gen Prompting | `creative/video-gen-prompting.md` | Universal video generation prompt vocabulary; **canonical 5-aspect spec** (Subject / Motion / Scene / Spatial / Camera); ~200 cinematography primitives | `ai-video-gen`, `ltx2`, `create-video` |
| â†³ Seedance Prompting | `creative/prompting/seedance-prompting.md` | **Preferred premium default.** Seedance 2.0 8-component structure, multi-shot, lip-sync, reference-to-video | `seedance-2-0`, `ai-video-gen` |
| â†³ Grok Prompting | `creative/prompting/grok-prompting.md` | Grok image/video prompting, edit flows, reference-image video | `grok-media` |
| â†³ Sora Prompting | `creative/prompting/sora-prompting.md` | Sora 2 structured template, advanced fields | `ai-video-gen` |
| â†³ VEO Prompting | `creative/prompting/veo-prompting.md` | VEO 3.1 14-component structure, art movements | `ai-video-gen` |
| â†³ LTX Prompting | `creative/prompting/ltx-prompting.md` | LTX-2 6-element structure, audio prompting | `ltx2` |
| â†³ HunyuanVideo Prompting | `creative/prompting/hunyuan-prompting.md` | HunyuanVideo formula, I2V best practices | â€" |
| Storytelling | `creative/storytelling.md` | Narrative structure, hooks, pacing, Mayer's principles | â€" |
| Sound Design | `creative/sound-design.md` | Audio ducking, LUFS targets, SFX timing, AI TTS mixing | `elevenlabs` |
| Technique Catalog | `creative/technique-catalog.md` | Video techniques by family: when to use them, when not, what runs them here and what replaces them without a GPU | — |
| Typography | `creative/typography.md` | Font selection, text sizing, safe zones, caption styling | â€" |
| ManimCE Usage | `creative/manim-usage.md` | Scene composition, animation timing, color usage | `manimce-best-practices` |
| Image Gen Usage | `creative/image-gen-usage.md` | Prompt consistency, hero reference, batch strategy | `flux-best-practices`, `bfl-api` |
| Image Provider Usage | `creative/image-provider-usage.md` | Provider selection (FLUX/Grok/OpenAI/Recraft/stock), cost-quality tradeoffs | `flux-best-practices`, `bfl-api`, `grok-media` |
| 3D World Generation | `creative/3d-world-generation.md` | Semantic world planning, asset sourcing/generation, Blender assembly, and fidelity review | `3d-asset-generation`, `threejs-world-generation` |
| B-Roll Planning | `creative/broll-planning.md` | Stock vs. generated decision, query construction, footage evaluation | — |
| Stock Sourcing Usage | `creative/stock-sourcing-usage.md` | Pexels/Pixabay usage, parameters, licensing, integration | — |
| Scene Detect Usage | `creative/scene-detect-usage.md` | Threshold tuning, algorithm selection, content presets | â€" |
| Diagram Gen Usage | `creative/diagram-gen-usage.md` | Complexity limits, progressive building, themes | `beautiful-mermaid` |
| Music Gen Usage | `creative/music-gen-usage.md` | BPM selection, prompt engineering, duration matching | `music`, `elevenlabs` |
| Background Removal | `creative/bg-remove-usage.md` | Model selection, alpha matting, compositing workflows | â€" |
| Upscaling | `creative/upscale-usage.md` | Scale factor, model selection, face-aware upscaling | â€" |
| Face Restoration | `creative/face-restore-usage.md` | CodeFormer/GFPGAN selection, fidelity tuning, vs face_enhance | â€" |
| Lip Sync | `creative/lip-sync-usage.md` | Wav2Lip model selection, dubbing workflows, input requirements | `faceswap` |
| Talking Head Gen | `creative/talking-head-gen-usage.md` | SadTalker/MuseTalk, photo-to-video, expression tuning | `avatar-video` |
| Video Understanding | `creative/video-understand-usage.md` | Visual QA, quality gating, scene classification | `video-understand` |
| Cinematography | `creative/cinematography.md` | Scene coverage, 180° rule and eyelines, staging, lens and light decisions; fills `scene_plan.shot_language`. Speaking character stays on screen | — |
| Editing Craft | `creative/editing-craft.md` | J/L cuts, cut on action, match cuts, reaction cuts, rhythm, humor flash cuts, trailer structure; `cut` is the only straight-cut value renderers honor | — |
| Audio Post (Cinema) | `creative/audio-post-cinema.md` | Five sound layers (dialogue, ambience, foley, spot FX, music), per-scene sound map, licensed sources, dialogue space and dubbing | `sound-effects`, `media-use`, `hyperframes-media` |
| Film Look Finishing | `creative/film-look-finishing.md` | Grain, halation, bloom, vignette, `.cube` LUTs (`assets/luts/`), shot color match across models, BT.709 tags with `film_look`; intensity by style (almost none on flat vector) | `ffmpeg` |
| Clip Conform | `creative/clip-conform.md` | Conform clips with `clip_conform`: fps to 24/30, deflicker, interpolation only to fill frames or slow motion, vidstab stabilization, resize; delegates heavy upscaling to `upscale` | `ffmpeg` |
| Title, Thumbnail & Trailer | `creative/title-thumbnail-trailer.md` | Three honest thumbnail variants for YouTube Test & Compare, title options, series title cards, credits, next-episode teaser | — |

## Pipeline Type Skills

Pipeline type skills provide production guidance for specific video formats, independent of the animated-explainer or talking-head pipeline.

| Skill | File | When to Use |
|-------|------|-------------|
| Short-Form | `creative/short-form.md` | TikTok, Reels, Shorts â€" vertical 9:16, under 60s |
| Long-Form | `creative/long-form.md` | YouTube 10+ min â€" chapters, retention, end screens |
| Screen Recording | `creative/screen-recording.md` | Code walkthroughs, tutorials, software demos |
| Animation Pipeline | `creative/animation-pipeline.md` | Motion graphics, easing, transitions, composition |
| 3D World Generation | `creative/3d-world-generation.md` | Continuous Three.js terrain worlds with semantic regions, explicit blockout/production tiers, licensed GLTF/PBR assets, diagnostics, and deterministic camera paths |
| Character Animation Pipeline | `pipelines/character-animation/` | Rigged local cartoon characters, pose libraries, action timelines, SVG/Canvas/Remotion/HyperFrames rendering |
| Cinematic | `creative/cinematic.md` | Letterbox, film pacing, layered audio, color grading |

## Pipeline Stage Director Skills

Stage director skills teach the agent HOW to execute each pipeline stage. Each skill is a detailed markdown file with process steps, quality rubrics, and self-evaluation criteria.

### Animated Explainer Pipeline (`pipelines/explainer/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/explainer/executive-producer.md` | `all` | **8-stage serial orchestration, quality gates, cross-stage checks, send-back** |
| **Research Director** | `pipelines/explainer/research-director.md` | `research` | **Web research methodology, 5 search batches, landscape/trending/data/audience/expert analysis** |
| **Proposal Director** | `pipelines/explainer/proposal-director.md` | `proposal` | **Concept options from research, production plan, cost estimate, approval gate** |
| Script Director | `pipelines/explainer/script-director.md` | `script` | Narrative architecture, timing, enhancement cues, research integration |
| Scene Director | `pipelines/explainer/scene-director.md` | `scene_plan` | Visual planning, technique library, feasibility |
| Asset Director | `pipelines/explainer/asset-director.md` | `assets` | TTS, image gen, diagram gen, music, budget |
| Edit Director | `pipelines/explainer/edit-director.md` | `edit` | Timeline assembly, subtitles, audio ducking |
| Compose Director | `pipelines/explainer/compose-director.md` | `compose` | FFmpeg/Remotion render, audio mixing |
| Publish Director | `pipelines/explainer/publish-director.md` | `publish` | SEO metadata, chapters, export packaging |

> **Note:** The old `idea-director.md` still exists for reference but is superseded by the research + proposal two-stage flow in v2.0. The talking-head pipeline continues to use its own `idea-director`.

### Talking Head Pipeline (`pipelines/talking-head/`)

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| Idea Director | `pipelines/talking-head/idea-director.md` | `idea` | Footage inspection, content assessment |
| Script Director | `pipelines/talking-head/script-director.md` | `script` | Transcription, section segmentation |
| Scene Director | `pipelines/talking-head/scene-director.md` | `scene_plan` | Enhancement planning, overlay placement |
| Asset Director | `pipelines/talking-head/asset-director.md` | `assets` | Subtitle gen, audio extraction |
| Edit Director | `pipelines/talking-head/edit-director.md` | `edit` | Cut assembly, subtitle config |
| Compose Director | `pipelines/talking-head/compose-director.md` | `compose` | Enhancement chain, render |
| Publish Director | `pipelines/talking-head/publish-director.md` | `publish` | Metadata, export packaging |

### Screen Demo Pipeline (`pipelines/screen-demo/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/screen-demo/executive-producer.md` | `all` | **7-stage serial orchestration, legibility gates, audio clarity, pacing checks** |
| Idea Director | `pipelines/screen-demo/idea-director.md` | `idea` | Workflow scoping, UI density assessment, output-shape choice |
| Script Director | `pipelines/screen-demo/script-director.md` | `script` | Action mapping, procedural narration, speed planning |
| Scene Director | `pipelines/screen-demo/scene-director.md` | `scene_plan` | Crop planning, callout restraint, aspect-ratio viability |
| Asset Director | `pipelines/screen-demo/asset-director.md` | `assets` | Subtitle-first asset kit, audio cleanup, reusable overlays |
| Edit Director | `pipelines/screen-demo/edit-director.md` | `edit` | Tight timeline planning, speed notes, subtitle zone control |
| Compose Director | `pipelines/screen-demo/compose-director.md` | `compose` | Legibility-first render, crisp screen output, verification |
| Publish Director | `pipelines/screen-demo/publish-director.md` | `publish` | Searchable metadata, chapter packaging, thumbnail concepts |

### Clip Factory Pipeline (`pipelines/clip-factory/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/clip-factory/executive-producer.md` | `all` | **7-stage serial orchestration, clip selection gates, batch consistency, hook placement** |
| Idea Director | `pipelines/clip-factory/idea-director.md` | `idea` | Batch strategy, clip families, yield planning |
| Script Director | `pipelines/clip-factory/script-director.md` | `script` | Transcript mining, ranking, standalone validation |
| Scene Director | `pipelines/clip-factory/scene-director.md` | `scene_plan` | Platform framing, safe zones, crop-viability planning |
| Asset Director | `pipelines/clip-factory/asset-director.md` | `assets` | Shared brand kit, rebased subtitles, batch audio consistency |
| Edit Director | `pipelines/clip-factory/edit-director.md` | `edit` | Hook-first mini-edits, series consistency |
| Compose Director | `pipelines/clip-factory/compose-director.md` | `compose` | Multi-job rendering, batch resilience, per-output verification |
| Publish Director | `pipelines/clip-factory/publish-director.md` | `publish` | Posting order, platform copy, batch cataloging |

### Podcast Repurpose Pipeline (`pipelines/podcast-repurpose/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/podcast-repurpose/executive-producer.md` | `all` | **7-stage serial orchestration, audio preservation gates, clip quality, multi-deliverable** |
| Idea Director | `pipelines/podcast-repurpose/idea-director.md` | `idea` | Deliverable mix by source mode, realistic long-form planning |
| Script Director | `pipelines/podcast-repurpose/script-director.md` | `script` | Diarized transcript truth, highlight ranking, chapter mapping |
| Scene Director | `pipelines/podcast-repurpose/scene-director.md` | `scene_plan` | Source-faithful treatments, audiogram vs quote vs companion planning |
| Asset Director | `pipelines/podcast-repurpose/asset-director.md` | `assets` | Subtitle-first packaging, speaker assets, optional topic art |
| Edit Director | `pipelines/podcast-repurpose/edit-director.md` | `edit` | Hook-led podcast clips, quote hold time, companion simplicity |
| Compose Director | `pipelines/podcast-repurpose/compose-director.md` | `compose` | Audio-first rendering, deliverable prioritization |
| Publish Director | `pipelines/podcast-repurpose/publish-director.md` | `publish` | Episode cross-linking, guest attribution, staggered release logic |

### Cinematic Pipeline (`pipelines/cinematic/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/cinematic/executive-producer.md` | `all` | **7-stage serial orchestration, emotional pacing gates, color consistency, audio dynamics** |
| Idea Director | `pipelines/cinematic/idea-director.md` | `idea` | Emotional arc selection, source truth, delivery-shape planning |
| Script Director | `pipelines/cinematic/script-director.md` | `script` | Beat mapping, dialogue selects, title-card restraint |
| Scene Director | `pipelines/cinematic/scene-director.md` | `scene_plan` | Hero-frame planning, reveal structure, transition limits |
| Asset Director | `pipelines/cinematic/asset-director.md` | `assets` | Source selects, support-insert discipline, music/ambience planning |
| Edit Director | `pipelines/cinematic/edit-director.md` | `edit` | Emotion-first pacing, reveal timing, audio-driven rhythm |
| Compose Director | `pipelines/cinematic/compose-director.md` | `compose` | Grade and mix finishing, frame-treatment judgment |
| Publish Director | `pipelines/cinematic/publish-director.md` | `publish` | Hero vs teaser packaging, poster-frame concepts |

### Animation Pipeline (`pipelines/animation/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/animation/executive-producer.md` | `all` | **8-stage serial orchestration, quality gates, motion consistency, math accuracy checks** |
| **Research Director** | `pipelines/animation/research-director.md` | `research` | **Topic + animation technique research, visual reference scan, mode-informed angles** |
| **Proposal Director** | `pipelines/animation/proposal-director.md` | `proposal` | **Animation mode selection (Manim/Remotion/AI/diagram), reuse strategy, cost estimate, approval gate** |
| Script Director | `pipelines/animation/script-director.md` | `script` | Animation-ready beats, text restraint, research integration, mode-aware writing |
| Scene Director | `pipelines/animation/scene-director.md` | `scene_plan` | Animatic planning, transition systems, tool-path mapping |
| Asset Director | `pipelines/animation/asset-director.md` | `assets` | Deterministic asset choice, reusable motifs, feasibility truth |
| Edit Director | `pipelines/animation/edit-director.md` | `edit` | Hold timing, stagger rules, readable motion planning |
| Compose Director | `pipelines/animation/compose-director.md` | `compose` | Sharp render output, timing integrity, safe-zone checks |
| Publish Director | `pipelines/animation/publish-director.md` | `publish` | Animation-mode packaging, thumbnail-system alignment |

> **Note:** The old `idea-director.md` still exists for reference but is superseded by the research + proposal two-stage flow in v2.0.

### Hybrid Pipeline (`pipelines/hybrid/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/hybrid/executive-producer.md` | `all` | **7-stage serial orchestration, source/support balance gates, overlay density, coherence** |
| Idea Director | `pipelines/hybrid/idea-director.md` | `idea` | Anchor-medium selection, support-layer planning, fallback visibility |
| Script Director | `pipelines/hybrid/script-director.md` | `script` | Source-vs-support beat mapping, dialogue retention, support justification |
| Scene Director | `pipelines/hybrid/scene-director.md` | `scene_plan` | Source-primary layout rules, overlay density control, variant-safe planning |
| Asset Director | `pipelines/hybrid/asset-director.md` | `assets` | Shared support kits, source-vs-generated asset tracking |
| Edit Director | `pipelines/hybrid/edit-director.md` | `edit` | Anchor-cut-first workflow, layered support timing, readable variants |
| Compose Director | `pipelines/hybrid/compose-director.md` | `compose` | Source/support balance checks, variant verification, coherent mix |
| Publish Director | `pipelines/hybrid/publish-director.md` | `publish` | Master-vs-derivative packaging, source-mix metadata |

### Avatar Spokesperson Pipeline (`pipelines/avatar-spokesperson/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/avatar-spokesperson/executive-producer.md` | `all` | **7-stage serial orchestration, lip-sync quality gates, presenter framing, CTA landing** |
| Idea Director | `pipelines/avatar-spokesperson/idea-director.md` | `idea` | Avatar-path classification, CTA scoping, capability truth |
| Script Director | `pipelines/avatar-spokesperson/script-director.md` | `script` | Spoken-copy shaping, scene-safe pacing, text restraint |
| Scene Director | `pipelines/avatar-spokesperson/scene-director.md` | `scene_plan` | Presenter layout, background discipline, variant realism |
| Asset Director | `pipelines/avatar-spokesperson/asset-director.md` | `assets` | Avatar-path locking, narration resolution, minimal support kits |
| Edit Director | `pipelines/avatar-spokesperson/edit-director.md` | `edit` | Presenter-first cut planning, overlay timing, CTA landing |
| Compose Director | `pipelines/avatar-spokesperson/compose-director.md` | `compose` | Lip-sync verification, subtitle-safe framing, clean render checks |
| Publish Director | `pipelines/avatar-spokesperson/publish-director.md` | `publish` | Audience-led packaging, presenter-first thumbnail concepts |

### Localization Dub Pipeline (`pipelines/localization-dub/`) — v2.0

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/localization-dub/executive-producer.md` | `all` | **7-stage serial orchestration, translation accuracy gates, timing preservation, per-locale QA** |
| Idea Director | `pipelines/localization-dub/idea-director.md` | `idea` | Scope definition, locale planning, glossary and review capture |
| Script Director | `pipelines/localization-dub/script-director.md` | `script` | Transcript truth, translated script packaging, term preservation |
| Scene Director | `pipelines/localization-dub/scene-director.md` | `scene_plan` | Dub-mode selection, timing-risk mapping, on-screen text planning |
| Asset Director | `pipelines/localization-dub/asset-director.md` | `assets` | Subtitle-first localization kit, dubbed audio generation, optional lip sync |
| Edit Director | `pipelines/localization-dub/edit-director.md` | `edit` | Locale-specific timelines, coverage planning, timing adjustments |
| Compose Director | `pipelines/localization-dub/compose-director.md` | `compose` | Per-locale rendering, subtitle-fit checks, output labeling |
| Publish Director | `pipelines/localization-dub/publish-director.md` | `publish` | Locale packaging, metadata precision, QA-note retention |

### Documentary Montage Pipeline (`pipelines/documentary-montage/`)

| Skill | File | Stage | Key Capabilities |
|-------|------|-------|-----------------|
| **Executive Producer** | `pipelines/documentary-montage/executive-producer.md` | `all` | **Retrieval-first orchestration, juxtaposition over narration, no generated clips by default** |
| Idea Director | `pipelines/documentary-montage/idea-director.md` | `idea` | Thematic question, tone register, shape, mandatory music and end-tag plans |
| Research Director | `pipelines/documentary-montage/research-director.md` | `research` | Verify every on-screen fact and the end-tag thesis, map archive sources and licences, ethics notes for real people |
| Script Director | `pipelines/documentary-montage/script-director.md` | `script` | Beat map, sparse sourced on-screen text in EN/ES, verified end-tag, narration only if approved |
| Scene Director | `pipelines/documentary-montage/scene-director.md` | `scene_plan` | CLIP-searchable slot descriptions and queries per movement |
| Asset Director | `pipelines/documentary-montage/asset-director.md` | `assets` | Corpus build, per-slot retrieval, provenance and licences |
| Edit Director | `pipelines/documentary-montage/edit-director.md` | `edit` | Beat-driven arrangement, holds, music sync, end-tag timing |
| Compose Director | `pipelines/documentary-montage/compose-director.md` | `compose` | Remotion CinematicRenderer, uniform grade, end-tag overlay |
| Publish Director | `pipelines/documentary-montage/publish-director.md` | `publish` | Per-language packages, archive credits and attribution, QC per master |

## Meta Skills

Cross-cutting skills that apply to all pipelines:

| Skill | File | Purpose |
|-------|------|---------|
| Onboarding | `meta/onboarding.md` | First-interaction greeting, capability discovery, starter prompts |
| Reviewer | `meta/reviewer.md` | Self-review protocol after every stage |
| Checkpoint Protocol | `meta/checkpoint-protocol.md` | When/how to checkpoint and request human approval |
| Skill Creator | `meta/skill-creator.md` | Dynamically create new skills during pipeline runs |
| Animation Runtime Selector | `meta/animation-runtime-selector.md` | Choose render runtime + animation library per scene |
| Taste Direction | `meta/taste-direction.md` | Convert a brief into taste dials, anti-patterns, and reference strategy for proposal/playbook/atelier work |
| Bespoke Composition (Atelier) | `meta/bespoke-composition.md` | Hand-author a composition from scratch (hero work) — no stock scene-types; routes art-direction → motion principles → engine mechanics → atelier render |
| YouTube Policy Gate | `meta/youtube-policy-gate.md` | Binding policy gate at proposal, script, assets and publish: made-for-kids call, originality, AI disclosure, music licensing, health claims, no burned-in subtitles |
| Guionista Core | `meta/guionista-core.md` | Any script | Shared rules: priority order, hook, open-loop ledger, humor, single CTA, words per minute by format, localization/dubbing, delivery as `script` artifact plus production table |
| Guionista Ficción Animada | `meta/guionista-ficcion-animada.md` | `script` (fiction) | Series bible, desire/need/flaw/lie, rule book, setup/payoff, dramatic irony, chapter structure for YouTube, flash-cut inserts, animation production limits |
| Guionista Documental | `meta/guionista-documental.md` | `script` (non-fiction) | Truth first, claims register with sources, ethics (real people, victims), documentary structures, licenses |
| Research Dossier | `meta/research-dossier.md` | Research stage of every project: the user's research prompt with dynamic variables (topic, niche, length, audience, market, three topic-specific layers), asks for any missing variable, runs on the `research-dossier` agent (Opus, high effort), saves `research_dossier.md` and feeds the `research_brief` |
| Creative Intake & Brief | `meta/creative-intake.md` | Phases 0–1: intake questions and the mandatory `brief_creativo` (logline, stakes, conflict, transformation, narrator) in `proposal_packet.metadata` or `brief.metadata`; approved at the same gate, required before any script |
| Production Bible | `meta/production-bible.md` | Visual/sound contract per project or series: character sheets, wardrobe states, locations, light map, reference injection per model, continuity check |
| Shot List & Storyboard | `meta/shot-list-storyboard.md` | One `scene_plan` entry per shot, one keyframe per shot, approval ladder one frame → board → 30 s before producing |
| Technique Selector | `meta/technique-selector.md` | Proposal or idea stage of narrative pipelines: goal → 3–8 justified techniques → tools → no-GPU fallback, in `technique_stack`, before locking the runtime |
| Speed Ramp | `core/speed-ramp.md` | Edit stage: `speed_ramp` changes speed gradually inside one shot, with an exact output length |
| Beat Sync | `core/beat-sync.md` | Edit stage: `beat_grid` finds tempo, beats and bars of a track and snaps cuts to them, refusing music with no clear pulse |
| Pre-Render Review | `meta/pre-render-review.md` | Scene plan, assets and compose: `cold_review` `preview` and `cold-viewer` review the plan, the clips and stills, so problems are fixed before the render |
| Cold Review | `meta/cold-review.md` | Final master of narrative pipelines: `cold_review` and the `cold-viewer` agent score 8 criteria, with 3 rounds at most → pass / revise / escalate, enforced by `export_bundle` |
| Layout Audit | `meta/layout-audit.md` | Before each render: `layout_audit` measures real boxes and stops on text off canvas, cut off, overlapping or covered |
| Narration QC | `meta/narration-qc.md` | Assets stage: refuses voices of another language and flags sentences that slip out of the script's language with `narration_qc` |
| Technical QC Gate | `meta/technical-qc-gate.md` | Binding technical gate with `technical_qc`: black, freeze, silence, loudness, true peak, conformity, licenses → pass / warn / block |
| AI Shot QA | `meta/ai-shot-qa.md` | Frame-by-frame review of every generated clip (hands, morphing, flicker, face drift) with `frame_sampler` + `video_understand`; accept / trim / regenerate threshold and rejection log |
| Budget & Model Routing | `meta/budget-and-model-routing.md` | Shot tiers (premium models only on hero shots), real `estimate_cost` estimates into `proposal_packet.cost_estimate`, spend control with `cost_tracker` (estimate → reserve → reconcile) |

## Style Playbooks

Style playbooks (`styles/*.yaml`) define visual language, typography, motion, audio, and asset generation constraints. They are validated against `schemas/styles/playbook.schema.json`.

| Playbook | Category | Mood | Best For |
|----------|----------|------|----------|
| `clean-professional` | motion-graphics | polished, trustworthy | Corporate, educational, SaaS |
| `premium-minimalist` | minimalist | calm, editorial | Investor updates, expert explainers, product narratives |
| `flat-motion-graphics` | motion-graphics | energetic, bold | Social media, TikTok, startups |
| `minimalist-diagram` | whiteboard | focused, technical | Technical deep-dives, architecture |

Load via `styles/playbook_loader.py`: `load_playbook("clean-professional")`

## Installed Agent Skills (Layer 3)

All agent skills live in `.agents/skills/` and are managed via `npx skills add`.
Claude Code accesses them via symlinks in `.claude/skills/`.

| Category | Installed Skills | Source |
|----------|-----------------|--------|
| **Video Composition** | `remotion-best-practices`, `remotion`, `hyperframes` (router), `hyperframes-core`, `hyperframes-creative`, `hyperframes-media`, `hyperframes-animation`, `hyperframes-cli`, `hyperframes-registry`, `media-use`, `motion-graphics`, `music-to-video`, `remotion-to-hyperframes`, `website-to-video` | `remotion-dev/skills`, `digitalsamba/claude-code-video-toolkit`, `heygen-com/hyperframes` (vendored v0.7.17, see `.agents/skills/hyperframes/PROVENANCE.md`) |
| **Video Processing** | `ffmpeg`, `video-toolkit` | `digitalsamba/claude-code-video-toolkit` |
| **TTS & Audio** | `text-to-speech`, `speech-to-text` (whisper, default STT), `azure-speech-to-text` (optional cloud STT), `music`, `sound-effects`, `elevenlabs`, `fish-audio-tts`, `agents`, `setup-api-key` | `elevenlabs/skills`, `digitalsamba/claude-code-video-toolkit`, local OpenMontage skill |
| **Image Generation** | `flux-best-practices`, `bfl-api`, `grok-media` | `black-forest-labs/skills`, local OpenMontage skill |
| **Math Animation** | `manimce-best-practices`, `manimgl-best-practices`, `manim-composer` | `adithya-s-k/manim_skill` |
| **3D Graphics** | `threejs-world-generation` (OpenMontage semantic-world workflow), `threejs-animation`, `threejs-fundamentals`, `threejs-geometry`, `threejs-interaction`, `threejs-lighting`, `threejs-loaders`, `threejs-materials`, `threejs-postprocessing`, `threejs-shaders`, `threejs-textures` | Local OpenMontage skill + `cloudai-x/threejs-skills` |
| **Diagrams** | `beautiful-mermaid`, `d3-viz` | `intellectronica/agent-skills`, `davila7/claude-code-templates` |
| **Animation** | `framer-motion`, `lottie-bodymovin` | `pproenca/dot-skills`, `dylantarre/animation-principles` |
| **Design** | `tailwind-design-system`, `web-design-guidelines`, `vercel-react-best-practices`, `vercel-composition-patterns` | `wshobson/agents`, `vercel-labs/agent-skills` |
| **AI Video (HeyGen)** | `avatar-video`, `create-video`, `faceswap`, `ai-video-gen`, `video-download`, `video-edit`, `video-translate`, `video-understand`, `visual-style` | `heygen-com/skills` |
| **AI Video/Image/TTS/Avatar (Kling Official)** | `kling-official` - official direct API auth, Classic/Turbo/Omni task protocols, multi-reference Omni syntax, internal Elements/Account Usage helpers, callback notes, TTS voice parameters, avatar/lip-sync face selection, error handling, and cost governance for `kling_official_video` / `kling_official_image` / `kling_tts` / `kling_avatar` / `kling_lip_sync` | Local OpenMontage skill |
| **AI Video (Premium)** | `seedance-2-0` — preferred premium default (cinematic, trailer, multi-shot, lip-sync, synced audio); accessed via `seedance_video` (fal.ai) or `heygen_video` Avatar Shots; `seedance-2-5` — 4–30 s clips, 50 multimodal references, prompt contract (section order, `Hard cut` breakdown, continuity locks, asset method) | Local OpenMontage skill |
| **Infrastructure** | `acestep`, `ltx2`, `playwright-recording` | `digitalsamba/claude-code-video-toolkit` |
