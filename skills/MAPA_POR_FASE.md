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
4. **Una herramienta** lo nombra en `agent_skills[]`. Hoy esta vía solo apunta a la capa 3 (`.agents/skills/`), nunca a un skill de esta carpeta.

## Leyenda

| Marca | Significa |
|---|---|
| ✅ todos | En `required_skills` de los 12 pipelines de producción |
| ✅ *lista* | En `required_skills` solo de esos pipelines |
| 🔗 | No está en ningún manifiesto, pero la guía o un director lo cita: se lee si el agente sigue el enlace |
| ⚪ | No lo carga nada (solo aparece en `INDEX.md` u otro skill). **Hoy el agente no lo lee** |

Abreviaturas de pipelines: **ae** animated-explainer · **anim** animation · **avatar** avatar-spokesperson · **char** character-animation · **cine** cinematic · **doc** documentary-montage · **hyb** hybrid · **clip** clip-factory · **loc** localization-dub · **pod** podcast-repurpose · **screen** screen-demo · **th** talking-head. Los siete primeros son los **narrativos** (crean una historia); los cinco últimos trabajan sobre **material fuente**.

---

## Transversales (todas las fases)

| Skill | Para qué | Estado |
|---|---|---|
| `meta/reviewer.md` | Autorrevisión al cerrar cada etapa | ✅ todos |
| `meta/checkpoint-protocol.md` | Cuándo parar y pedir aprobación humana | ✅ todos |
| `meta/youtube-policy-gate.md` | Políticas de YouTube en propuesta, guion, assets y publicación | ✅ todos |
| `meta/skill-creator.md` | Crear un skill nuevo durante una producción | ✅ ae |
| `meta/capability-extension.md` | Extender el sistema cuando ninguna herramienta cubre la necesidad | ⚪ |

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

| Skill | Para qué | Estado |
|---|---|---|
| `meta/creative-intake.md` | Brief creativo (ver fase 0) | ✅ ae, anim, avatar, char, cine, doc, hyb |
| `meta/research-dossier.md` | Dossier de investigación con prompt de variables dinámicas, agente `research-dossier` (Opus, esfuerzo alto) y fuentes verificadas por niveles | 🔗 guía y `research-director` de ae, anim, char, cine y doc |
| `meta/taste-direction.md` | Diales de gusto, antipatrones y estrategia de referencias | 🔗 guía y 2 directores |
| `creative/storytelling.md` | Arco de explicativo: gancho, tensión, conceptos en capas | 🔗 `idea-director` de anim (obsoleto), avatar, cine y hyb, y `script-director` de avatar y loc; **ningún director de explainer lo cita** |
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
| `creative/data-visualization.md` | Tipo de gráfico y su animación | ⚪ |
| `creative/broll-planning.md` | Stock o generado, búsquedas, evaluar material | ⚪ |

**Voz y sonido**

| Skill | Para qué | Estado |
|---|---|---|
| `meta/voice-performance-director.md` | Actuación de voz y casting | ✅ ae, anim |
| `creative/audio-post-cinema.md` | Cinco capas de sonido y mapa sonoro por escena | ✅ anim, char, cine, doc, hyb |
| `creative/sound-design.md` | Ducking, LUFS, tiempos de SFX, mezcla con TTS | ⚪ (se solapa con `audio-post-cinema`; falta comparar) |

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
| `creative/enhancement-strategy.md` | Mejoras y overlays de talking-head | ⚪ |
| `core/whisperx.md` | Transcripción con tiempos por palabra | ⚪ |

**Manuales por herramienta.** Ninguno se carga solo al llamar la herramienta, porque su `agent_skills[]` apunta únicamente a la capa 3:

| Herramienta (`tools/`) | Skill de esta carpeta | Estado |
|---|---|---|
| `seedance_video`, `seedance_ark`, `seedance_replicate`, `higgsfield_video` | `creative/prompting/seedance-prompting.md` | ⚪ |
| `veo_video` | `creative/prompting/veo-prompting.md` | ⚪ |
| `sora_video` | `creative/prompting/sora-prompting.md` | ⚪ |
| `ltx_video_local`, `ltx_video_modal` | `creative/prompting/ltx-prompting.md` | ⚪ |
| `hunyuan_video`, `hunyuan_cloud_video` | `creative/prompting/hunyuan-prompting.md` | ⚪ |
| `grok_video`, `grok_image` | `creative/prompting/grok-prompting.md` | ⚪ |
| `image_selector`, `image_gen`, `flux_image` | `creative/image-gen-usage.md`, `creative/image-provider-usage.md` | ⚪ |
| `pexels_video`, `pixabay_video`, `pexels_image`, `pixabay_image` | `creative/stock-sourcing-usage.md` | ⚪ |
| `music_gen` y demás de `tools/audio/*music*` | `creative/music-gen-usage.md` | ⚪ |
| `diagram_gen` | `creative/diagram-gen-usage.md` | ⚪ |
| `math_animate` | `creative/manim-usage.md` | ⚪ |
| `lip_sync` | `creative/lip-sync-usage.md` | ⚪ |
| `talking_head` | `creative/talking-head-gen-usage.md` | ⚪ |
| `bg_remove` | `creative/bg-remove-usage.md` | ⚪ |
| `upscale` | `creative/upscale-usage.md` | ⚪ |
| `face_restore` | `creative/face-restore-usage.md` | ⚪ |
| `scene_detect` | `creative/scene-detect-usage.md` | ⚪ |
| `video_understand` | `creative/video-understand-usage.md` | ⚪ |

## Fase 5 — Acabado: ¿está listo para publicar?

Etapas: `edit`, `compose`, `publish`. Directores: `edit-director`, `compose-director`, `publish-director`.

Sale: máster EN/ES, SRT/VTT, miniaturas y metadatos.

| Skill | Para qué | Estado |
|---|---|---|
| `creative/editing-craft.md` | Cortes J/L, corte en acción, ritmo, cortes relámpago | ✅ todos |
| `creative/video-editing.md` | Decisiones de corte en talking-head | 🔗 3 directores |
| `creative/video-stitching.md` | Unir varios clips y encadenar clips de IA | ⚪ |
| `creative/film-look-finishing.md` | Grano, halación, LUTs, igualar color entre modelos | ✅ ae, anim, avatar, char, cine, doc, hyb, th |
| `core/color-grading.md` | Perfiles de color y LUTs en FFmpeg | ⚪ |
| `core/ffmpeg.md` | Operaciones de video y audio | ⚪ |
| `core/subtitle-sync.md` | Tiempos de subtítulos | ⚪ |
| `core/loudness-mastering.md` | Volumen final por plataforma | ✅ todos |
| `meta/technical-qc-gate.md` | Negros, congelados, silencios, picos, licencias | ✅ todos |
| `core/delivery-specs.md` | Másteres por destino, SRT/VTT, capítulos | ✅ todos |
| `creative/title-thumbnail-trailer.md` | Miniaturas, títulos, avance del siguiente capítulo | ✅ todos |

---

## Lo que el mapa deja a la vista

- **29 skills con ⚪.** Existen, pero el agente no los lee: casi todos los manuales por herramienta, `data-visualization`, `broll-planning` y `sound-design`.
- **Resuelto: brief creativo único.** `creative-intake` ya es obligatorio en los siete pipelines narrativos y deja `metadata.brief_creativo` aprobado antes del guion. Los pipelines de material fuente (clip-factory, localization-dub, podcast-repurpose, screen-demo, talking-head) no lo exigen: parten de un material que ya existe.
- **`storytelling.md` no llega al pipeline explainer**, para el que fue escrito.
- **Resuelto: el análisis de referencia ya extrae el ADN narrativo** (gancho, beats, bucles, cadencia, narrador, ritmo, humor, cierre), medido y no adivinado, y `guionista-core` lo lee como patrón estructural.
- **Solapes por confirmar:** `sound-design` ↔ `audio-post-cinema` y `storytelling` ↔ `guionista-core`. `video-editing` y `enhancement-strategy` **no** son duplicados: son específicos de talking-head.

Mantén este mapa al día: si añades, mueves o borras un skill de `core/`, `creative/` o `meta/`, actualiza su fila. `tests/contracts/test_skill_phase_map_contract.py` falla si falta alguno.
