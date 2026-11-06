# Mapa de skills por fase

Responde dos preguntas: **¿qué skill se lee en cada momento del flujo?** y **¿cuáles no los carga nadie hoy?** Las rutas son relativas a `skills/`. El detalle de cada skill está en [`INDEX.md`](INDEX.md); este mapa solo dice *cuándo* se usa.

```
ENTRADA ──► 1. CONCEPTO ──► 2. GUION ──► 3. DIRECCIÓN AV ──► 4. PRODUCCIÓN ──► 5. ACABADO
idea o       idea / research   script       scene_plan            assets             edit · compose · publish
video ref    · proposal
```

## Cómo se carga un skill

Un skill solo se lee si algo lo carga. Hay cuatro vías:

1. **`AGENT_GUIDE.md`** manda a un skill o a un pipeline.
2. **El manifiesto** (`pipeline_defs/<pipeline>.yaml`) lo lista en `required_skills`.
3. **Un director de etapa** (`pipelines/<pipeline>/<etapa>-director.md`) lo cita en su texto.
4. **Una herramienta** lo nombra: `usage_skills[]` apunta a los manuales de esta carpeta y `agent_skills[]` a la capa 3 (`.agents/skills/`). Se lee al usar la herramienta, así que no carga contexto en cada pipeline.

## Leyenda

| Marca | Significa |
|---|---|
| ✅ todos | En `required_skills` de los 12 pipelines de producción |
| ✅ *lista* | En `required_skills` solo de esos pipelines |
| 🔗 | No está en ningún manifiesto, pero la guía o un director lo cita: se lee si el agente sigue el enlace |
| 🔧 | Lo nombra una herramienta en `usage_skills`: se lee al usarla |
| ⚪ | No lo carga nada; solo se admite con el motivo entre paréntesis. Hoy no queda ninguno |

Abreviaturas de pipelines: **ae** animated-explainer · **anim** animation · **avatar** avatar-spokesperson · **char** character-animation · **cine** cinematic · **doc** documentary-montage · **hyb** hybrid · **clip** clip-factory · **loc** localization-dub · **pod** podcast-repurpose · **screen** screen-demo · **th** talking-head. Los siete primeros son los **narrativos** (crean una historia); los cinco últimos trabajan sobre **material fuente**.

---

## Transversales (todas las fases)

| Skill | Para qué | Estado |
|---|---|---|
| `meta/reviewer.md` | Autorrevisión al cerrar cada etapa | ✅ todos |
| `meta/checkpoint-protocol.md` | Cuándo parar y pedir aprobación humana | ✅ todos |
| `meta/youtube-policy-gate.md` | Políticas de YouTube en propuesta, guion, assets y publicación | ✅ todos |
| `meta/skill-creator.md` | Crear un skill nuevo durante una producción | ✅ ae |
| `meta/capability-extension.md` | Extender el sistema cuando ninguna herramienta cubre la necesidad | 🔗 guía |

## Fase 0 — Entrada: ¿qué quieres y en qué te inspiras?

Sale: respuestas del usuario y, si hay video de referencia, su análisis.

| Skill | Para qué | Estado |
|---|---|---|
| `meta/onboarding.md` | Primer contacto vago («¿qué puedes hacer?») | 🔗 guía |
| `meta/video-reference-analyst.md` | Analizar un video de referencia: cinco aspectos visuales por plano y **ADN narrativo** (gancho, beats, bucles, cadencia, narrador, ritmo, humor, cierre) en `replication_guidance.narrative_dna`, que lee el guionista | 🔗 guía |
| `meta/creative-intake.md` | Preguntas de propósito, audiencia, tono, objetivo y restricciones (fase 0) y **brief creativo obligatorio** (fase 1: logline, qué está en juego, conflicto, transformación, narrador) | ✅ ae, anim, avatar, char, cine, doc, hyb |

## Fase 1 — Concepto: ¿qué historia, para quién y por qué importa?

Etapas: `research` + `proposal` (ae, anim, char, cine) o `idea` (los demás; doc tiene `idea` + `research`). Directores: `executive-producer`, `research-director`, `proposal-director` o `idea-director`. En los pipelines con `research` + `proposal`, el manifiesto ya no usa `idea-director` aunque el archivo siga existiendo.

Sale: `proposal_packet` (o el brief de la etapa `idea`) con el **brief creativo** en `metadata.brief_creativo`, aprobado en la misma puerta. Sin él no arranca el guion.

En los pipelines narrativos también sale `technique_stack`: las técnicas de la pieza, con su motivo. Se elige antes de fijar el motor.

| Skill | Para qué | Estado |
|---|---|---|
| `meta/creative-intake.md` | Brief creativo (ver fase 0) | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `meta/research-dossier.md` | Dossier de investigación con prompt de variables dinámicas, agente `research-dossier` (Opus, esfuerzo alto) y fuentes verificadas por niveles | 🔗 guía y `research-director` de ae, anim, char, cine y doc |
| `meta/taste-direction.md` | Diales de gusto, antipatrones y estrategia de referencias | 🔗 guía y 2 directores |
| `meta/technique-selector.md` | Elegir técnicas con motivo y dejar `technique_stack` antes de fijar el motor | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `creative/technique-catalog.md` | Menú de técnicas por familias: cuándo usarlas, cuándo no, con qué se hacen y qué las sustituye sin GPU | 🔗 `technique-selector` |
| `creative/storytelling.md` | Arco de explicativo: gancho, tensión, conceptos en capas | 🔗 `idea-director` de anim (obsoleto), avatar, cine y hyb, y `script-director` de ae, avatar y loc |
| `meta/budget-and-model-routing.md` | Costo real y modelos premium solo en planos héroe | ✅ ae, anim, avatar, char, cine, hyb |

## Fase 2 — Guion: ¿cómo se cuenta, segundo a segundo?

Etapa: `script`. Director: `script-director` (en doc el guion vive en `scene-director`).

Sale: escaleta aprobada → artefacto `script` + tabla de producción. Entra con el brief creativo de la fase 1.

| Skill | Para qué | Estado |
|---|---|---|
| `meta/guionista-core.md` | Reglas comunes: gancho, bucles, humor, CTA, ritmo de voz, doblaje | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `meta/guionista-ficcion-animada.md` | Series de ficción: personajes, libro de reglas, capítulo, cliffhanger | ✅ anim, char, cine |
| `meta/guionista-documental.md` | No ficción: verdad primero, registro de fuentes, estructuras | ✅ ae, anim, avatar, doc, hyb |
| `creative/long-form.md` | YouTube de 10+ min: capítulos, retención, pantallas finales | 🔗 2 directores |
| `creative/short-form.md` | Shorts, Reels y TikTok verticales | 🔗 4 directores |

## Fase 3 — Dirección audiovisual: ¿cómo se ve y cómo suena?

Etapa: `scene_plan` (en char, además `character-design` y `rig-plan`). Director: `scene-director`.

Sale: `scene_plan`, biblia de producción y lista de planos.

**Motor y estilo de animación**

| Skill | Para qué | Estado |
|---|---|---|
| `meta/animation-runtime-selector.md` | Elegir runtime (Remotion, HyperFrames…) y librería por escena | ✅ ae, anim, char, cine, screen |
| `meta/bespoke-composition.md` | Composición hecha a mano para trabajo héroe (modo atelier) | 🔗 guía |
| `core/hyperframes.md` | Runtime HTML/GSAP | 🔗 guía y directores |
| `core/remotion.md` | Runtime React | 🔗 2 directores |
| `creative/3d-world-generation.md` | Mundos 3D en Three.js con recorridos de cámara | 🔗 guía y 2 directores |
| `creative/ink-theater.md` | Estilo de dibujo a tinta y títeres con mocap | 🔗 guía y 2 directores |
| `creative/animated-drawing.md` | Animar un dibujo entregado por el usuario | 🔗 guía |

**Imagen y puesta en escena**

| Skill | Para qué | Estado |
|---|---|---|
| `meta/production-bible.md` | Contrato visual y sonoro: personajes, locaciones, luz, continuidad | ✅ ae, anim, avatar, char, cine, hyb |
| `meta/shot-list-storyboard.md` | Un plano por entrada, un fotograma clave, escalera de aprobación | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `creative/cinematography.md` | Cobertura, regla de 180°, lente y luz; quien habla se ve | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `creative/camera-motion-library.md` | Movimientos de cámara, transiciones, texto cinético | 🔗 guía y 2 directores |
| `creative/typography.md` | Fuentes, tamaños, zonas seguras | 🔗 1 director |
| `creative/data-visualization.md` | Tipo de gráfico y su animación | 🔗 3 directores |
| `creative/broll-planning.md` | Stock o generado, búsquedas, evaluar material | 🔗 4 directores |

**Voz y sonido**

| Skill | Para qué | Estado |
|---|---|---|
| `meta/voice-performance-director.md` | Actuación de voz y casting | ✅ ae, anim |
| `creative/audio-post-cinema.md` | Cinco capas de sonido y mapa sonoro en escenas con personajes y lugares | ✅ anim, char, cine, doc, hyb |
| `creative/sound-design.md` | Ducking, elección de música y tiempos de SFX en piezas con locución | 🔗 7 directores |

**Guías de formato** (repiten en parte lo que ya dicen los directores del pipeline)

| Skill | Para qué | Estado |
|---|---|---|
| `creative/cinematic.md` | Letterbox, ritmo de cine, color | 🔗 1 director |
| `creative/animation-pipeline.md` | Principios de motion graphics y easing | 🔗 1 director |
| `creative/screen-recording.md` | Tutoriales y demos de software | 🔗 1 director |

## Fase 4 — Producción: ¿con qué herramienta y cómo se le pide?

Etapa: `assets`. Director: `asset-director`.

Sale: assets por plano, revisados.

| Skill | Para qué | Estado |
|---|---|---|
| `meta/ai-shot-qa.md` | Revisar cada clip generado (manos, deformaciones, parpadeo) | ✅ ae, anim, avatar, cine, hyb |
| `creative/clip-conform.md` | Ajustar fps, estabilizar, interpolar | ✅ cine, doc, hyb, screen, th |
| `creative/video-gen-prompting.md` | Vocabulario universal de prompts de video (cinco aspectos) | 🔗 3 directores |
| `creative/enhancement-strategy.md` | Mejoras y overlays de talking-head | 🔧 `face_enhance` · 🔗 1 director |
| `core/whisperx.md` | Transcripción con tiempos por palabra | 🔧 `transcriber` |

**Manuales por herramienta.** Cada una los declara en `usage_skills`, y `image_selector` y `video_selector` pasan los del proveedor elegido en `required_usage_skills`:

| Herramienta (`tools/`) | Skill de esta carpeta | Estado |
|---|---|---|
| `seedance_video`, `seedance_ark`, `seedance_replicate`, `higgsfield_video` | `creative/prompting/seedance-prompting.md` | 🔧 |
| `veo_video` | `creative/prompting/veo-prompting.md` | 🔧 |
| `sora_video` | `creative/prompting/sora-prompting.md` | 🔧 |
| `ltx_video_local`, `ltx_video_modal`, `ltx_api_video` | `creative/prompting/ltx-prompting.md` | 🔧 |
| `hunyuan_video`, `hunyuan_cloud_video` | `creative/prompting/hunyuan-prompting.md` | 🔧 |
| `grok_video`, `grok_image` | `creative/prompting/grok-prompting.md` | 🔧 |
| `image_selector`, `image_gen`, `flux_image` | `creative/image-gen-usage.md`, `creative/image-provider-usage.md` | 🔧 |
| `pexels_video`, `pixabay_video`, `pexels_image`, `pixabay_image` | `creative/stock-sourcing-usage.md` | 🔧 |
| `music_gen`, `fal_elevenlabs_music`, `suno_music`, `google_music`, `comfyui_music` | `creative/music-gen-usage.md` | 🔧 |
| `diagram_gen` | `creative/diagram-gen-usage.md` | 🔧 |
| `math_animate` | `creative/manim-usage.md` | 🔧 |
| `lip_sync` | `creative/lip-sync-usage.md` | 🔧 |
| `talking_head` | `creative/talking-head-gen-usage.md` | 🔧 |
| `bg_remove` | `creative/bg-remove-usage.md` | 🔧 |
| `upscale` | `creative/upscale-usage.md` | 🔧 |
| `face_restore` | `creative/face-restore-usage.md` | 🔧 |
| `scene_detect` | `creative/scene-detect-usage.md` | 🔧 |
| `video_understand` | `creative/video-understand-usage.md` | 🔧 |

## Fase 5 — Acabado: ¿está listo para publicar?

Etapas: `edit`, `compose`, `publish`. Directores: `edit-director`, `compose-director`, `publish-director`.

Sale: máster EN/ES, SRT/VTT, miniaturas y metadatos.

| Skill | Para qué | Estado |
|---|---|---|
| `creative/editing-craft.md` | Cortes J/L, corte en acción, ritmo, cortes relámpago | ✅ todos |
| `creative/video-editing.md` | Decisiones de corte en talking-head | 🔗 3 directores |
| `creative/video-stitching.md` | Unir varios clips y encadenar clips de IA | 🔧 `video_stitch` · 🔗 7 directores |
| `creative/film-look-finishing.md` | Grano, halación, LUTs, igualar color entre modelos | ✅ ae, anim, avatar, char, cine, doc, hyb, th |
| `core/color-grading.md` | Perfiles de color y LUTs en FFmpeg | 🔧 `color_grade` · 🔗 5 directores |
| `core/ffmpeg.md` | Operaciones de video y audio | 🔧 `video_compose`, `video_trimmer`, `video_stitch` |
| `core/subtitle-sync.md` | Tiempos de subtítulos | 🔧 `subtitle_gen` · 🔗 9 directores |
| `core/loudness-mastering.md` | Volumen final por plataforma | ✅ todos |
| `meta/technical-qc-gate.md` | Negros, congelados, silencios, picos, licencias | ✅ todos |
| `meta/layout-audit.md` | Textos y gráficos desbordados, encimados o tapados, antes de renderizar | ✅ todos |
| `meta/cold-review.md` | Revisión del máster por alguien que no lo hizo, con 8 criterios | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `meta/narration-qc.md` | Voz de otro idioma y frases que se salen del idioma del guion | ✅ ae, anim, avatar, char, hyb, loc, demo |
| `core/delivery-specs.md` | Másteres por destino, SRT/VTT, capítulos | ✅ todos |
| `creative/title-thumbnail-trailer.md` | Miniaturas, títulos, avance del siguiente capítulo | ✅ todos |

---

## Lo que el mapa deja a la vista

- **Resuelto: ningún skill sin conectar.** Los manuales llegan por `usage_skills` al usar la herramienta, y el resto por sus directores o la guía. `tests/contracts/test_usage_skill_pointers.py` falla si reaparece un ⚪ sin motivo.
- **Resuelto: brief creativo único.** `creative-intake` ya es obligatorio en los siete pipelines narrativos y deja `metadata.brief_creativo` aprobado antes del guion. Los pipelines de material fuente (clip-factory, localization-dub, podcast-repurpose, screen-demo, talking-head) no lo exigen: parten de un material que ya existe.
- **Resuelto: `storytelling.md` ya llega al pipeline explainer**, por su `script-director`.
- **Resuelto: el análisis de referencia ya extrae el ADN narrativo** (gancho, beats, bucles, cadencia, narrador, ritmo, humor, cierre), medido y no adivinado, y `guionista-core` lo lee como patrón estructural.
- **Resuelto: las técnicas se eligen con motivo.** `technique-selector` deja `technique_stack` aprobado en los siete pipelines narrativos, y escena y montaje trabajan desde él.
- **Resuelto: `sound-design` y `audio-post-cinema` no son duplicados.** El primero sirve a piezas con locución y el segundo a escenas con personajes y lugares; el nivel final lo fija `loudness-mastering`.
- **Solape por confirmar:** `storytelling` ↔ `guionista-core`. `video-editing` y `enhancement-strategy` **no** son duplicados: son específicos de talking-head.

Mantén este mapa al día: si añades, mueves o borras un skill de `core/`, `creative/` o `meta/`, actualiza su fila. `tests/contracts/test_skill_phase_map_contract.py` falla si falta alguno.
