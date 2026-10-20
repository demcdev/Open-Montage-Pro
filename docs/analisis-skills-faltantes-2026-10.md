# Análisis consolidado de skills faltantes (octubre 2026)

Revisión de los cinco reportes que recomiendan skills nuevas para OpenMontage, verificada contra el código del repositorio. Cada propuesta queda con una decisión (sí, fusionada, parcial, más adelante o no) y su razón.

## 1. Fuentes y método

| Reporte | Propuestas de skills | Otras propuestas |
|---|---|---|
| Opus 5.5 (`Opus5.5_skills_faltantes.md`) | 32 (13 alta, 15 media, 4 baja) | 9 departamentos, 10 cambios de arquitectura, huecos por pipeline, 6 reglas de gobernanza, roadmap |
| Sonnet 5.5 (`Sonnet5.5_skills_faltantes.json`) | 12, más 1 pendiente de verificar | — |
| Qwen 3.7 Plus (`Qwen3.7plus_skills_faltantes.json`) | 17 | Roadmap en 4 fases |
| Gemini 3.1 Pro (`Gemini3.1Pro_skills_faltantes.md`, en formato JSON) | 7 | — |
| Gemini 3.8 Flash (`Gemini3.8flash_skills_faltantes.json`) | 10 | Plan en 3 fases |

En total son unas 78 propuestas de skills. Muchas se repiten con otro nombre, así que se agruparon por el problema que resuelven.

**Cómo se verificó:** se leyó cada afirmación sobre el repo y se comprobó con búsquedas en `skills/`, `tools/`, `pipeline_defs/` y `.agents/skills/`. Las cifras de mercado, precios y fechas de 2026 que cita el reporte de Opus (Kling 4.0, Luma Ray3.2, Runway Aleph 2.0, reglamento Digital Omnibus, cifras de TikTok) **no se pudieron verificar** y no se usaron como base de ninguna decisión.

## 2. Criterios de decisión

1. **Valor para lo que produces hoy:** series de ficción animada en vectores (HyperFrames), en inglés y español, para YouTube, con voces TTS, sin subtítulos incrustados y con la regla "un fotograma, luego 30 s, luego producción".
2. **Valor para la meta declarada:** videos de todo tipo, incluidos cinematográficos con video generado por IA.
3. **Que no exista ya** en el repo (se descartó lo duplicado).
4. **Licencias aptas para monetizar** en YouTube (uso comercial).
5. **Costo y esfuerzo** frente al beneficio.

## 3. Lo que la verificación encontró

| Afirmación de los reportes | Resultado en el repo |
|---|---|
| No hay QC técnico (negros, congelados, silencios, loudness) | **Cierto.** `visual_qa` solo revisa resolución, códec y frames; `composition_validator` revisa el JSON antes del render |
| El loudness no se mide ni se fuerza | **Parcial.** `audio_mixer` aplica `loudnorm` en una sola pasada (−16 LUFS por defecto, TP −1,5) y no emite reporte de medición |
| No hay presupuesto ni estimador de costos | **Falso.** Existe `tools/cost_tracker.py` (estima, reserva, concilia, con modos de presupuesto) y `video_selector.estimate_cost` |
| No hay reencuadre inteligente | **Falso.** Existe `tools/video/auto_reframe.py` (seguimiento de rostro, 16:9 → 9:16) |
| No hay deflicker, interpolación ni estabilización | **Cierto.** Ninguna herramienta usa `deflicker`, `minterpolate`, `vidstab` ni RIFE |
| No hay grano, halation ni LUTs | **Cierto.** `color_grade` tiene 7 perfiles de FFmpeg y no existe `assets/luts/` |
| No hay C2PA ni registro de consentimientos | **Cierto**, pero `youtube-policy-gate` ya exige licencias por asset, divulgación de IA y prohíbe clonar voces reales |
| No hay biblia de producción | **Parcial.** Solo `character-animation` tiene `character-design-director`; la biblia de tu serie se hizo a mano (`series_bible_v0.md`) |
| La retención no está cubierta | **Falso.** `long-form.md` tiene curva de retención y bucles abiertos; `guionista-core` tiene registro de bucles abiertos |
| `documentary-montage` no tiene guion, research ni publish | **Cierto.** Solo tiene asset, compose, edit, executive-producer, idea y scene |
| `lip-sync` usa Wav2Lip | **Cierto.** `tools/avatar/lip_sync.py` tiene `provider = "wav2lip"` |
| `heygen` está obsoleta | **Cierto.** Se declara DEPRECATED y ninguna herramienta la referencia |
| `gsap` genérica sin descripción | **Falso (corregido al implementar).** `.agents/skills/gsap/` solo tiene `README.md` a propósito: el propio archivo dice que es un mapa de navegación hacia las 8 skills `gsap-*`, no una skill cargable |
| Falta prompting de Kling, Runway y Luma en capa 2 | **Cierto para Kling y Runway** (tienen herramienta). Luma no tiene herramienta en el repo |
| HyperFrames debe vendorizarse con versión fija | **Ya está hecho** (v0.7.17 con `PROVENANCE.md`) |
| "252 habilidades actuales" (Gemini Flash) | **Aproximadamente correcto:** 162 archivos en `skills/` + 91 en `.agents/skills/` |

**Hallazgo adicional (no estaba en ningún reporte):** `.claude/skills/` expone solo 49 de las 91 skills de `.agents/skills/`. Faltan, entre otras, las de HyperFrames, Kling, Seedance y GSAP. `skills/INDEX.md` dice que se accede por enlaces simbólicos, pero no están todos.

**Advertencia sobre el reporte de Opus:** habla de "clientes retail de Tita (Nike Colombia, Mario Hernández, Juan Valdez)". No hay nada de eso en el proyecto ni en el contexto guardado. Las propuestas de retail se evaluaron como no aplicables a este proyecto; si esos clientes son reales, conviene revisarlas aparte.

## 4. Skills que sí se van a crear (16 consolidadas)

Cada fila agrupa varias propuestas de los reportes. Ninguna se clona en los 12 pipelines: se escribe una vez y la enlazan los directores que la necesitan (idea del reporte de Opus de "departamentos transversales").

### Fase 1: prioridad alta

| # | Skill | Qué hace | Por qué sí | Propuesta por | Dónde se implementa |
|---|---|---|---|---|---|
| 1 | `technical-qc-gate` | Revisa el render final con FFmpeg: frames negros, congelados, silencios, bloques, loudness y conformidad del archivo. Devuelve aprobar, advertir o bloquear. También bloquea si un asset no tiene licencia registrada | Es lo más barato y lo que más errores visibles evita. Hoy un video unido por partes puede salir con un silencio o un frame negro sin que nadie lo detecte | Opus (`technical-qc-gate`, `qc-delivery-manager`), Qwen (parte de `copyright-clearance-check`) | `skills/meta/technical-qc-gate.md` + herramienta nueva o extensión de `tools/analysis/visual_qa.py`. Lo invocan todos los `compose-director` y `publish-director` |
| 2 | `loudness-mastering` | Masterización de audio en dos pasadas con medición y reporte (LUFS integrado, true peak, rango). Incluye de-esser para voces TTS | El loudness hoy se aplica en una pasada sin verificar. Es la mejora de audio más barata | Opus, Qwen (`audio-mastering-lufs`), Gemini Flash (`audio-mastering-broadcast`), Sonnet (parte de `audio-post-cinema`) | `skills/core/loudness-mastering.md` + cambio en `tools/audio/audio_mixer.py` |
| 3 | `production-bible` | Biblia por proyecto o serie: hojas de personaje (frente, tres cuartos, perfil), vestuario, paleta, locaciones, utilería, mapa de luz por escena, y cómo pasar esas referencias a cada modelo (Kling Elements, Seedance multi-referencia, IP-Adapter en ComfyUI) | Tu serie tiene 8 capítulos con personajes recurrentes. Hoy la biblia se hace a mano y fuera de `character-animation` no existe. Es el principal problema del video IA (el personaje cambia entre planos) | Opus (`production-bible`, `reference-pack-consistency`, `continuity-supervisor`), Sonnet (`continuity-bible`), Gemini Flash (`character-consistency-bible`, `environment-and-lighting-continuity`) | `skills/meta/production-bible.md`. La enlazan `idea`, `proposal`, `scene` y `asset-director` de todos los pipelines con personajes; reutiliza `character-design-director` |
| 4 | `shot-list-storyboard` | Lista de planos con encuadre, movimiento, duración y audio; un fotograma clave por plano; animática con voz temporal; aprobación antes de producir. Visible en Backlot | Formaliza la regla que ya fijaste ("un fotograma, luego 30 s"). Ahorra dinero porque los errores se corrigen en imágenes fijas y no en video caro | Opus, Sonnet (`previs-storyboard`) | `skills/meta/shot-list-storyboard.md`. La enlazan los `scene-director` |
| 5 | `cinematography-director` | Cobertura de escena (plano máster, plano/contraplano, insertos), puesta en escena, regla de 180°, línea de mirada, esquemas de luz y lente. Sirve para prompts de video IA y para el encuadre en animación 2D | `video-gen-prompting` ya trae vocabulario de lentes, pero nada enseña a cubrir una escena. Además resuelve tu corrección "quien habla debe verse en pantalla" | Opus (`cinematography-director`, `dp-director`), Sonnet, Qwen, Gemini Flash (`camera-optics-and-blocking`) | `skills/creative/cinematography.md`. La enlazan los `scene-director` |
| 6 | `editing-craft` | Cortes J y L, corte sobre la acción, corte por coincidencia (forma, color, movimiento), ritmo de escena, cortes relámpago para humor y estructura de tráiler | El `edit-director` cinematic tiene solo 2 KB. Incluye tu preferencia de cortes rápidos a otra escena | Sonnet (`cinematic-editing-craft`), Qwen (`seamless-transition-engine`), Gemini Flash (`match-cut-and-seamless-flow`) | `skills/creative/editing-craft.md`. La enlazan todos los `edit-director` |
| 7 | `audio-post-cinema` | Arquitectura de sonido por capas: ambiente o room tone, foley, efectos puntuales, música y voz. Incluye mapa de dónde entra y sale la música y silencios intencionales | `sound-design.md` está pensada para explicativos. Tus capítulos usan una capa ambiental sintética provisional | Sonnet, Gemini Flash (`foley-and-micro-sfx-layering`), Opus (`sound-supervisor`) | `skills/creative/audio-post-cinema.md`. La enlazan `asset-director` y `edit-director` |

### Fase 2: prioridad media

| # | Skill | Qué hace | Por qué sí | Propuesta por | Dónde se implementa |
|---|---|---|---|---|---|
| 8 | `film-look-finishing` | Grano, halation, bloom, viñeta, LUTs, empate de color entre planos de modelos distintos y etiquetas de color BT.709 correctas. Con intensidad según el estilo (casi nula en vector plano) | Es lo que más separa "video IA" de "filmado". Se ajusta al estilo para no ensuciar la animación plana | Sonnet, Gemini Flash (`film-emulation-and-texture`), Opus (grano de `temporal-finishing`, `color-management`, `colorist`) | `skills/creative/film-look-finishing.md` + herramienta `tools/enhancement/film_look.py` + `assets/luts/` |
| 9 | `clip-conform` | Igualar fps (24 o 30), deflicker, interpolación RIFE solo para conformar o cámara lenta, estabilización, reescalado de video y restauración de archivo | Los clips de distintos modelos llegan con fps y calidad distintos y hoy no hay cómo igualarlos | Sonnet (`ai-clip-finishing`), Opus (`temporal-finishing`), Gemini Pro (`frame-interpolation`), Gemini Flash (deflicker de `ai-defect-cleanup`, `archive-restoration-upscale`) | `skills/creative/clip-conform.md` + herramienta nueva en `tools/video/`; reutiliza `upscale` y `face_restore` |
| 10 | `ai-shot-qa` | Revisión de planos generados: manos, morphing, parpadeo, cambio de rostro. Umbral de aceptar o regenerar y registro de rechazos | Evita montar planos defectuosos. Solo aplica a video generado (no a tu animación vectorial) | Sonnet, Qwen (`ai-artifact-detector`), Gemini Flash (detección de `ai-defect-cleanup-and-deflicker`) | `skills/meta/ai-shot-qa.md`; usa `video_understand` y `frame_sampler` |
| 11 | `delivery-specs` | Especificaciones por destino (YouTube 16:9, Shorts, Reels, TikTok), máster, versiones EN y ES, normas de SRT/VTT (velocidad de lectura, largo de línea), capítulos | Publicas en dos idiomas con subtítulos aparte. Hoy cada pipeline lo resuelve por su cuenta | Opus (`delivery-spec-registry`, parte de `accessibility-standards`), Sonnet (`delivery-mastering`), Qwen (parte de `accessibility-compliance`) | `skills/core/delivery-specs.md`; lo usan `compose-director`, `publish-director` y `export_bundle` |
| 12 | `title-thumbnail-trailer` | Miniaturas (3 variantes para la prueba A/B de YouTube), títulos de serie, créditos, avance de capítulo | En una serie la miniatura decide el clic. Hoy los `publish-director` solo la mencionan | Opus (`thumbnail-cover-design`), Sonnet (`title-trailer-design`) | `skills/creative/title-thumbnail-trailer.md`; la enlazan los `publish-director` |
| 13 | `budget-and-model-routing` | Decide qué modelo usar por tipo de plano (caro solo en planos clave, borrador barato para el resto) y cómo usar `cost_tracker` con tope | `cost_tracker` existe pero ninguna skill enseña a enrutar por importancia del plano | Opus (`cost-estimator`, `line-producer`), Qwen (`cost-optimizer-router`), Sonnet (pendiente de verificar) | `skills/meta/budget-and-model-routing.md`; la enlazan los `proposal-director` |
| 14 | Directores faltantes de `documentary-montage` | Agregar `script-director`, `research-director` y `publish-director` | Verificado que faltan. Un documental sin guion ni verificación de hechos es el hueco más grande entre pipelines | Opus | `skills/pipelines/documentary-montage/` + `pipeline_defs/documentary-montage.yaml` |

### Fase 3: cuando se use o según demanda

| # | Skill | Qué hace | Por qué sí, pero después | Propuesta por |
|---|---|---|---|---|
| 15 | `performance-analytics-loop` | Lee retención, CTR y tasa de gancho de lo publicado y alimenta el guion siguiente | Vale cuando la serie ya esté publicada. Se puede apoyar en el conector de vidIQ que tienes en Claude en vez de programar las APIs | Opus |
| 16 | `genre-playbooks` | Recetas de terror, comedia, thriller, ciencia ficción y acción (luz, ritmo, paleta, sonido) | Útil para series de distintos géneros. Es la de menor impacto inmediato | Sonnet |
| — | `vfx-compositing` (condicional) | Rotoscopia con SAM, segmentación, composición por capas, efectos por profundidad | Solo si produces video IA cinematográfico o metraje real. En animación vectorial ya trabajas por capas. Revisar la licencia de SAM antes | Sonnet, Qwen, Opus (`roto-matting-composite`), Gemini Pro (`video-segmentation`) |
| — | Guías de prompting de Kling y Runway (condicional) | Equivalentes a `seedance-prompting` para esos proveedores | Solo para los proveedores cuya clave tengas activa | Opus |

## 5. Lo que no se va a crear y por qué

| Propuesta | Reporte | Por qué no |
|---|---|---|
| `product-fidelity-pipeline`, `feed-to-video-variants`, `virtual-try-on` | Opus | Son para clientes retail (catálogos, packshots, ropa). No hay nada de eso en el proyecto |
| `brand-kit-guardian` / `brand-guideline-enforcer` / `brand-guardian` | Opus, Qwen | Sin clientes de marca no aporta. El kit de tu canal (paleta, fuentes) va dentro de `production-bible`. Reactivar si llegan clientes |
| `ai-disclosure-provenance` (parte C2PA) / `c2pa-watermarking` | Opus, Qwen | La divulgación de YouTube ya está en `youtube-policy-gate`. La animación no realista no exige etiqueta. C2PA requiere certificado de firma y aplica sobre todo a contenido realista o anuncios. Reconsiderar si haces video IA fotorrealista |
| `rights-consent-registry` / `copyright-clearance-check` / `clearance-legal` | Opus, Qwen | Tus personajes son inventados y el policy gate prohíbe clonar voces reales. La parte útil (bloquear assets sin licencia) se integra en `technical-qc-gate` |
| `smart-reframe` | Opus | Ya existe `auto_reframe` con seguimiento de rostro |
| `cost-estimator` como skill aparte | Opus | Ya existe `cost_tracker`. Lo que faltaba (enrutamiento) va en la #13 |
| `aces-color-workflow` / `aces-color-pipeline` / `color-management` completo | Qwen, Gemini Pro, Opus | ACES y OpenColorIO sirven con fuentes log, RAW o EXR. Tus fuentes son MP4 de 8 bits en Rec.709 y YouTube entrega SDR. Solo se toma la parte útil (etiquetas BT.709 y empate de color) en la #8 |
| `luma-ray-hdr` / `luma-prompting` | Opus | No hay herramienta de Luma en el repo y el HDR no aporta a tu contenido |
| `v2v-edit-relight` (Runway Aleph) | Opus | Pensado para corregir metraje existente; caro por segundo. `runway_video` ya existe si hace falta |
| `stem-separation-mix` / `stem-separation-advanced` / Demucs | Opus, Qwen, Sonnet, Gemini Pro | No remezclas pistas. Los pesos de Demucs tienen restricciones de uso y separar una canción con derechos no te da derecho a usarla (riesgo legal en el razonamiento de Qwen) |
| `foley-v2a` (MMAudio, HunyuanVideo-Foley, ThinkSound) | Opus | Licencias no comerciales o con exclusiones; no sirven para monetizar. El foley va con librerías o ElevenLabs SFX dentro de la #7 |
| `spatial-audio` | Gemini Pro | YouTube se escucha en estéreo, sobre todo en móvil y audífonos. Mucho esfuerzo para poca diferencia |
| `advanced-local-tts` (XTTS) | Gemini Pro | Ya hay Piper local y muchas TTS en `tts_selector`. XTTS se publicó con licencia no comercial y su empresa cerró. La clonación de voz va contra tu política |
| `lip-sync-scorer` | Qwen | Tu animación sincroniza la boca por envolvente de audio. El puntaje tipo SyncNet aplica a avatares fotorrealistas, y el umbral "95 %" del reporte no tiene base. Reconsiderar si usas `avatar-spokesperson` |
| `proxy-workflow-manager` | Qwen | No hay metraje 4K de cámara. HyperFrames y Remotion renderizan desde la fuente y ya hay borradores |
| `render-versioning-ab` / `asset-versioning-dam` | Qwen, Opus | Ya hay checkpoints, `decision_log` y versiones de render (v1, v2, v3). Solo se agregarán campos de procedencia (modelo, prompt, semilla) al `asset_manifest` |
| `edit-decision-list-generator` | Qwen | Ya trabajas por escena y por parte, y unes con FFmpeg sin re-renderizar todo |
| `nle-handoff-otio` | Opus | No usas DaVinci ni Premiere; todo lo hace el agente. Reconsiderar si se suma un editor humano |
| `camera-tracking` / `camera-tracking-3d` | Gemini Pro, Opus | Requiere metraje real con movimiento de cámara y mucho trabajo. Bajo retorno para tu contenido |
| `dialogue-cleanup` / `audio-restoration` (ahora) | Opus, Gemini Pro | `audio_enhance` ya hace reducción de ruido, puerta y compresión, y tus voces TTS salen limpias. Solo haría falta con voz grabada (talking-head, podcast) |
| `neuro-pacing-and-retention` | Gemini Flash | Ya cubierto en `long-form.md` y `guionista-core`. Solo se agregará una nota sobre la caída de energía entre los minutos 5 y 12 |
| `frame-accurate-feedback` | Qwen | Es una función de producto para Backlot, no una skill. Hoy das las notas por parte en el chat y funciona |
| Parte de "estandarizar todo a 60 fps" | Gemini Pro | Contradice el estándar cinematográfico de 24 fps. Se interpola solo para conformar o para cámara lenta |
| Parte de "saturación de cinta / calidez analógica" | Gemini Flash | Es subjetivo y puede degradar la voz. Se toman solo el de-esser y la normalización |
| Parte de "inpainting temporal" y "colorización" | Gemini Flash | Costosos, poco fiables y fuera de tu tipo de contenido |
| Parte de ProRes y HDR en la entrega | Sonnet | YouTube no lo necesita para tu contenido. Se entrega un máster H.264 o H.265 de alta calidad |
| Routers de TTS, STT y música; registro de modelos | Opus | `tts_selector`, `video_selector`, `image_selector`, `provider-model-refresh` y `provider_contracts` ya cubren casi todo. Usas Google TTS y música propia |
| Consolidar ffmpeg, remotion y hyperframes duplicados | Opus | La separación en capas 2 y 3 es intencional (está documentada en `INDEX.md`). Refactorizar no mejora los videos |

## 6. Arquitectura y gobernanza (reporte de Opus)

| Propuesta | Decisión | Por qué |
|---|---|---|
| Borrar `heygen` (obsoleta) | **Sí** | Ninguna herramienta la usa; confunde al agente |
| Arreglar `gsap` (carpeta sin `SKILL.md`) | **No** | Al implementar se vio que es un mapa de navegación intencional; no hay nada que arreglar |
| Wav2Lip como respaldo, no por defecto | **Sí** | Cambio de texto en `lip-sync-usage.md`; el lip-sync nativo de los modelos es mejor |
| Separar QC creativo (`reviewer`) de QC técnico | **Sí** | Queda resuelto con la #1 |
| Skills transversales en vez de copias por pipeline | **Sí** | Se escriben en `skills/core`, `creative` o `meta` y las enlaza cada `executive-producer`. No hace falta una carpeta `departments/` nueva |
| Agregar `research` y `proposal` a otros pipelines (hybrid, avatar, clip-factory) | **Más adelante** | No los usas hoy |
| Sincronizar `.claude/skills/` con `.agents/skills/` | **Sí** (hallazgo propio) | Faltan 42 skills como accesos de Claude Code |
| No publicar sin aprobación humana | **Ya existe** | Checkpoints y `export_bundle` no sube nada |
| Consentimiento antes de generar | **Ya existe** | El policy gate prohíbe clonar voces reales |
| Tope de gasto por proyecto | **Ya existe** | `cost_tracker` con modos de presupuesto |
| Fijar versiones de skills de terceros | **Ya existe** | HyperFrames fijado en v0.7.17 |
| Manifiesto de auditoría por asset | **Parcial** | Agregar modelo, prompt y semilla al `asset_manifest` |

## 7. Orden recomendado

1. **Higiene (horas):** borrar `heygen`, nota de Wav2Lip, sincronizar `.claude/skills/` (`scripts/sync_claude_skills.py`). **Hecho el 2026-10-20.**
2. **Fase 1:** `technical-qc-gate`, `loudness-mastering`, `production-bible`, `shot-list-storyboard`, `cinematography-director` (archivo `skills/creative/cinematography.md`), `editing-craft`, `audio-post-cinema`. **Hecho el 2026-10-20**, con dos herramientas nuevas: `technical_qc` y `audio_master` (en vez de modificar `audio_mixer`).
3. **Fase 2:** `film-look-finishing`, `clip-conform`, `ai-shot-qa`, `delivery-specs`, `title-thumbnail-trailer`, `budget-and-model-routing`, directores de `documentary-montage`.
4. **Fase 3:** `performance-analytics-loop`, `genre-playbooks` y, si aplica, `vfx-compositing` y guías de Kling y Runway.

Las skills 1, 2, 8, 9 y 10 necesitan herramientas nuevas en Python además del texto. Las demás son solo instrucciones.

## 8. Advertencias

- Los datos de mercado del reporte de Opus son posteriores a lo que puedo verificar y vienen en parte de fuentes secundarias.
- Las licencias citadas (Demucs, MMAudio, SAM, XTTS) deben confirmarse en la fuente oficial antes de usar cualquier modelo.
- La mejora real solo se puede medir con una rúbrica antes y después sobre los mismos guiones.
