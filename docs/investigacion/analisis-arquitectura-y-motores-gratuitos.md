# OpenMontage: arquitectura, flujo y panorama de motores gratuitos (oct-2026)

> Informe de análisis. No modifica código. Fuentes al final.

## 1. Qué es OpenMontage, en una frase

Un sistema de producción de video **dirigido por el agente**: no hay orquestador en Python. El LLM del IDE (Claude Code, Codex, Cursor…) lee manifiestos YAML y skills en Markdown, llama a herramientas Python y guarda checkpoints. Python solo aporta **herramientas + persistencia**.

```
Usuario ─► AGENT_GUIDE.md (enrutado) ─► pipeline_defs/<pipeline>.yaml
                                             │
             ┌───────────────────────────────┘
             ▼  por cada etapa
   skills/pipelines/<p>/<etapa>-director.md   (Capa 2: cómo lo hace OpenMontage)
             │
             ├─► .agents/skills/<tecnología>/   (Capa 3: cómo funciona la API/motor)
             ├─► tools/** (BaseTool) vía tools/tool_registry.py   (Capa 1: qué existe)
             ├─► schemas/artifacts/*.json  (valida el artefacto)
             ├─► lib/checkpoint.py  (projects/<p>/pipeline/*.json)
             ├─► skills/meta/reviewer.md  (autorrevisión, máx. 2 rondas)
             └─► aprobación humana (human_approval_default)
```

### Las 3 capas de conocimiento
| Capa | Ubicación | Rol |
|---|---|---|
| 1 | `tools/` + `pipeline_defs/` | Qué herramientas existen, su estado (`available`/`unavailable`), coste, dependencias |
| 2 | `skills/` (core, meta, creative, pipelines) | Convenciones del proyecto: directores de etapa, QC, guionistas, política YouTube |
| 3 | `.agents/skills/` (~90) | Conocimiento técnico de cada motor: Remotion, HyperFrames, GSAP, FLUX, Seedance, ACE-Step, FFmpeg… |

El puente entre capas es el campo `agent_skills[]` de cada herramienta.

### Piezas clave de infraestructura
- `tools/base_tool.py`: contrato común (tier, capability, provider, runtime LOCAL/LOCAL_GPU/API, dependencias `cmd:`/`env:`/`python:`, fallbacks, cost).
- `tools/tool_registry.py`: autodescubrimiento (`pkgutil.walk_packages`), `support_envelope()` y `provider_menu()` para el preflight.
- Patrón **selector + proveedores**: `tts_selector`, `image_selector`, `video_selector` puntúan proveedores disponibles; nunca hay proveedor hardcodeado.
- `tools/cost_tracker.py`: presupuesto estimate → reserve → reconcile, modos observe/warn/cap, umbral de aprobación por acción ($0.50).
- `lib/checkpoint.py`: reanudación por etapa; políticas `guided` / `manual_all` / `auto_noncreative`.
- `lib/media_profiles.py`: perfiles YouTube/Shorts/Reels/TikTok/cinemático → flags FFmpeg.
- `styles/*.yaml`: playbooks visuales (clean-professional, flat-motion-graphics, minimalist-diagram, premium-minimalist, anime-ghibli).
- `backlot/`: servidor FastAPI de "storyboard vivo" (tablero de decisiones).

## 2. Flujo de principio a fin

Etapas canónicas (varían por pipeline):

```
research → proposal → script → scene_plan → assets → edit → compose → publish
```

| Etapa | Artefacto | Herramientas típicas | Aprobación |
|---|---|---|---|
| research | `research_brief` | búsqueda web del propio agente | no |
| proposal | `proposal_packet`, `decision_log` | preflight del registro, cost_tracker | **sí** (elige concepto, runtime, coste) |
| script | `script` (con cues y plan de voz) | — (LLM) | **sí** |
| scene_plan | `scene_plan` | — | **sí** |
| assets | `asset_manifest` | tts_selector, image_selector, video_selector, diagram_gen, math_animate, music_gen/pixabay_music | **sí** |
| edit | `edit_decisions` (fija `render_runtime`) | — | no |
| compose | `render_report`, `final_review` | video_compose → Remotion / HyperFrames / FFmpeg, audio_mixer, audio_master, film_look, technical_qc | no |
| publish | `publish_log` | export_bundle, technical_qc | **sí** |

Pipelines disponibles: animated-explainer, animation, character-animation, cinematic, documentary-montage, hybrid, avatar-spokesperson, talking-head, screen-demo, clip-factory, podcast-repurpose, localization-dub (+ framework-smoke).

Reglas de gobierno importantes:
- **Rule Zero**: toda producción pasa por un pipeline; nada de scripts ad-hoc.
- **No hay cambios de runtime silenciosos**: si el runtime aprobado falla, `video_compose` devuelve un bloqueo, no sustituye.
- Antes de cada llamada de pago se anuncia herramienta, proveedor, modelo y motivo.

### Motores de composición (el corazón del "look profesional")
| Runtime | Base | Úsalo para |
|---|---|---|
| **Remotion** (`remotion-composer/`) | React 18 + Remotion 4 | Escenas con componentes (TextCard, StatCard, charts), subtítulos palabra a palabra, TalkingHead |
| **HyperFrames** (`npx hyperframes`) | HTML/CSS/GSAP, de HeyGen | Tipografía cinética, promos, website-to-video, rigs SVG de personajes, mundos Three.js |
| **FFmpeg** | — | Cortes/concat simples, quemado de subtítulos, encode |

## 3. Herramientas: qué hay y qué tienes activo

Inventario: ~160 archivos de herramienta en `tools/`, con >30 proveedores de video, >20 de imagen y >20 de TTS. Casi todo lo de "alta gama" (Veo, Kling, Seedance, Sora, Runway, MiniMax, FLUX, GPT Image, ElevenLabs, Suno, Lyria…) es **API de pago**.

Las rutas **locales/gratuitas** que ya existen en el código:
| Capacidad | Herramientas locales en el repo | Requisito |
|---|---|---|
| Video IA | `wan_video`, `ltx_video_local`, `hunyuan_video`, `cogvideo_video`, `comfyui_video` | GPU NVIDIA (8–24 GB+) |
| Imagen IA | `local_diffusion`, `qwen_image_21`, `comfyui_image` | GPU |
| TTS | `piper_tts` (CPU); Kokoro solo vía HyperFrames (`hyperframes tts`) | CPU |
| Música | `comfyui_music` (ACE-Step vía ComfyUI), `music_library` | GPU / local |
| STT | `transcriber` (faster-whisper/WhisperX) | CPU sirve |
| Avatar | `talking_head` (SadTalker), `lip_sync` (Wav2Lip) | GPU |
| Mejora | `upscale` (Real-ESRGAN), `face_restore` (CodeFormer), `bg_remove` | GPU recomendable |
| Stock | `pixabay_*`, `pexels_*`, `corpus_builder`, `direct_clip_search`, `bmts_lite` | API key gratuita |
| Gráficos | `diagram_gen`, `math_animate` (Manim), `threejs_world`, `character_*` (rigs SVG) | CPU |

**Tu máquina**: Intel Iris Xe (sin GPU dedicada), 32 GB RAM, Node 24, FFmpeg 9.0.2 recién instalado.
→ Todas las rutas `LOCAL_GPU` quedan fuera. Lo que funciona hoy: Google TTS/Polly (tienes credenciales), Pixabay (imagen, video, música), análisis/QC/mezcla/masterizado con FFmpeg, Remotion/HyperFrames, rigs de personaje, Three.js, diagramas.

## 4. Qué hacen proyectos similares (GitHub, Reddit, X)

| Proyecto | Tipo | Cómo genera lo visual | Voz / música | Coste "gratis" |
|---|---|---|---|---|
| **MoneyPrinterTurbo** (harry0703, MIT, 20k+★) | Plataforma 1-clic (WebUI + API) | **Stock** (Pexels/Pixabay/Coverr) + MoviePy/FFmpeg; no genera píxeles | Edge-TTS / Azure, música de fondo local | LLM local (Ollama) + stock gratis = $0, sin GPU |
| **Pixelle-Video** (AIDC-AI, Apache-2.0) | Motor automático de shorts | Imágenes/vídeo IA vía **workflows ComfyUI** (o RunningHub en nube) | **Edge-TTS / Index-TTS** | "Completamente gratis" con Ollama + ComfyUI local (GPU 6 GB+) |
| **ViMax** (HKUDS, MIT) | Multi-agente (director, guionista, productor) | Backends Gemini / MiniMax / Veo | — | Depende de APIs |
| **NarratoAI** | Narración automática sobre metraje | Recorte/edición de vídeo existente | TTS | Bajo |
| **video-use** (browser-use) | Skills para agente | Edición de metraje desde transcript | — | Skills gratis, APIs propias |
| **video-shotcraft**, **claude-remotion-skill** | Skills para Claude Code | **Remotion** (springs, Ken Burns, grano, captions) | — | Gratis (solo render local) |
| **varg.ai SDK** | SDK declarativo (open source) | IA + composición FFmpeg | TTS, lipsync, música | Según proveedor |
| **HyperFrames** (HeyGen, open source) | Motor de render HTML→vídeo | HTML/CSS/GSAP + Lottie/Three.js | Kokoro local para TTS | **Gratis** |
| **ComfyUI** | Lienzo de nodos | Wan 2.2, LTX-2.x, Hunyuan… | ACE-Step, Stable Audio | Gratis con GPU |
| **LTX Desktop** | App de escritorio | LTX-2.5 (22B), audio nativo | integrado | Gratis con NVIDIA ≥15 GB |

Conclusiones del ecosistema (Pixo, sept-2026, 50+ repos revisados):
1. Ya casi nadie compite en el **modelo**: Seedance/Kling/Veo/Sora se usan como backends intercambiables. La competencia está en la **orquestación**, que es justo la apuesta de OpenMontage.
2. Las skills (como OpenMontage) carecen de estado visual; las plataformas carecen de control fino; los lienzos carecen de profundidad de pipeline. Todos convergen en **agente director + storyboard visual + multi-modelo**. `backlot/` es el intento de OpenMontage de cubrir el storyboard.
3. En X, los hilos más virales de "motion design con Claude" hacen lo mismo: agente con shell + **Remotion/HyperFrames + GSAP**, con un bucle de crítica (extraer frames con ffmpeg y revisarlos) y el pipeline empaquetado como skill. El vídeo IA se usa solo para el movimiento difícil de programar.

## 5. Mejores motores gratuitos por capa (oct-2026)

### Vídeo generativo (open weights)
| Modelo | VRAM mínima | Máx. | Audio nativo | Licencia | Nota |
|---|---|---|---|---|---|
| **Wan 2.2** TI2V-5B GGUF | 8 GB | 720p | No | Apache 2.0 | Default más seguro y comercial |
| Wan 2.2 A14B MoE GGUF | 12 GB | 720p | No | Apache 2.0 | Mejor calidad Wan |
| **LTX-2.3** distilled | 16 GB (NVFP4) / 32 GB (FP8) | 4K@50fps | **Sí** | LTX Community (gratis <$10M) | Único open con audio sincronizado |
| HunyuanVideo 1.5 FP8 | ~14 GB | 1080p | No | Tencent Community | Movimiento cinematográfico |
| CogVideoX 2B/5B | 16/24 GB | 720p | No | Apache / propia | Mejor adherencia al prompt |
| Mochi 1 FP8 | 20 GB | 480p | No | Apache 2.0 | Base para LoRA |

**Sin GPU**: la comunidad usa **Google Colab (T4, ~15 GB)** y **Kaggle** con *Wan2GP* o notebooks de LTX-2.3; también Spaces de Hugging Face (ZeroGPU, con colas). Funciona, pero es lento y con cuotas.

### Imagen
- Open weights: **FLUX.1 Schnell** (Apache 2.0), Qwen-Image, Krea 2. Requieren GPU.
- APIs con capa gratuita: **Cloudflare Workers AI** (10 000 neurons/día, FLUX schnell), **Pollinations.ai** (sin key; con marca de agua y rate limit si es anónimo), **Hugging Face Inference Providers** (crédito mensual pequeño). Sobre la cuota gratis de Gemini para imágenes las fuentes se contradicen (~500/día frente a "sin free tier"): hay que verificarlo en la propia consola de AI Studio.

### Voz (TTS)
| Modelo | Licencia comercial | Idiomas | Clonado | Hardware |
|---|---|---|---|---|
| **Kokoro-82M** | Apache 2.0 ✅ | 8 (ES incluido, 54 voces) | No | **CPU** (≈2× tiempo real) |
| **Chatterbox / Multilingual v3 / Turbo** | MIT ✅ (con marca de agua PerTh) | 23–25 | Sí, 5 s | GPU 4 GB+ |
| **Qwen3-TTS** 1.7B | Apache 2.0 ✅ | 10 | Sí, 3 s, dirección por texto | GPU 6 GB+ |
| CosyVoice2 0.5B | Apache 2.0 ✅ | 9+ | Sí | GPU |
| Piper | MIT / GPL (depende de la voz) | 40+ | No | CPU (calidad modesta) |
| Fish S2 Pro, Breeze TTS 2, Voxtral, F5, XTTS | ❌ no comercial | — | Sí | GPU |
| **Edge-TTS** (endpoint no oficial de Microsoft) | Zona gris | 100+ (muy buen español neural) | No | **Ninguno**, es online |

MoneyPrinterTurbo y Pixelle usan **Edge-TTS** por calidad/coste. Es gratis, pero depende de un endpoint no oficial que puede romperse.

### Música
- **ACE-Step 1.5** (MIT, uso comercial explícito): ~8 GB VRAM, casi al nivel de Suno v4.5 en métricas, editable (cover, repaint, stems). Ya tiene skill en `.agents/skills/acestep`.
- YuE 7B (Apache 2.0, 16 GB): canciones completas con voz.
- Stable Audio Open 1.5: texturas y SFX (gratis por debajo de $1M de ingresos).
- MusicGen: no comercial (CC BY-NC).
- Sin GPU: bibliotecas (Pixabay Music, Freesound CC0), o ACE-Step en Colab/Kaggle.

### Composición, post y QC (todo gratis y en CPU)
Remotion, **HyperFrames**, GSAP, Lottie, Three.js, Manim, FFmpeg (loudnorm, LUTs, grano), faster-whisper/WhisperX (subtítulos), Real-ESRGAN (mejor con GPU, pero tolera CPU en clips cortos).

## 6. Lectura para tu caso (sin GPU)

Lo que da aspecto **profesional** gratis no viene del vídeo generativo, sino de:
1. **Motion design programático** (HyperFrames/Remotion + GSAP): tipografía cinética, charts y transiciones. Es determinista, nítido a 1080p/4K y no tiene coste.
2. **Buen audio**: voz natural más **masterizado** (`audio_master`, loudness -14 LUFS) y ducking de música. Es lo que más separa lo amateur de lo pro.
3. **Stock real bien editado** (Pixabay/Pexels más `corpus_builder` y `bmts_lite`), con color grading y `film_look` para unificar.
4. **Bucle de QC visual** (`frame_sampler`, `visual_qa`, `technical_qc`), igual que en los hilos virales de X.
5. Vídeo IA **solo para planos puntuales**, generado en Colab o Kaggle (Wan 2.2 5B o LTX-2.3) e importado como asset.

### Huecos de OpenMontage frente al ecosistema (posibles mejoras)
| Hueco | Qué usan otros | Esfuerzo |
|---|---|---|
| No hay TTS neural de calidad en CPU dentro de `tts_selector` (Kokoro solo existe vía HyperFrames) | Kokoro (kokoro-onnx), Edge-TTS | Bajo: nueva herramienta `kokoro_tts` y/o `edge_tts` |
| No hay generación de imagen con capa gratuita en la nube | Cloudflare Workers AI (FLUX schnell), Pollinations, HF Inference | Bajo-medio: proveedor en `image_selector` |
| Vídeo IA local imposible sin GPU | Wan2GP/LTX en Colab o Kaggle | Medio: herramienta "remote notebook" o flujo manual de importación |
| Música generativa gratis solo vía ComfyUI local | ACE-Step 1.5 en Colab, YuE | Medio |
| `music_gen` es solo ElevenLabs | ACE-Step (MIT) | Medio |

## Fuentes
- Pixo, *Open-Source AI Video on GitHub: 50+ Pipelines Reviewed (2026)*: https://pixo.video/blog/open-source-ai-video-pipelines
- *Best Open Source AI Video Generators in 2026: 8 Compared*: https://www.opensourcealternatives.to/blog/open-source-ai-video-generators
- Thunder Compute, *Best Open-Source AI Video Generation Models (2026)*: https://www.thundercompute.com/blog/best-open-source-ai-video-generation-models
- MoneyPrinterTurbo: https://github.com/harry0703/moneyprinterturbo (+ issue #1183 sobre stock vs. generativo)
- Pixelle-Video: https://github.com/aidc-ai/pixelle-video
- awesome-video-generation (ViMax, Pixelle): https://github.com/backblaze-b2-samples/awesome-video-generation
- Cartesia, *Best open-source TTS models, compared by license* (oct-2026): https://www.cartesia.ai/learn/open-source-tts
- Pinggy, *Best Open Source Self-Hosted TTS Models in 2026*: https://pinggy.io/blog/best_open_source_self_hosted_text_to_speech_models/
- TextToLab, *Best Open-Source TTS 2026*: https://texttolab.com/blog/open-source-text-to-speech
- ACE-Step 1.5 (paper y repo): https://arxiv.org/html/2602.00744v1 · https://github.com/ace-step/ACE-Step-1.5
- IT-JIM, *Best Open-Source AI Music Generators 2026*: https://www.it-jim.com/blog/best-open-source-ai-music-generator/
- Spheron, despliegue de YuE/ACE-Step/MusicGen: https://www.spheron.network/blog/deploy-open-source-ai-music-generation-gpu-cloud-2026/
- Eden AI, APIs de imagen gratuitas 2026: https://www.edenai.co/post/top-free-image-generation-tools-apis-and-open-source-models
- edge-tts: https://github.com/rany2/edge-tts
- Reddit r/StableDiffusion, r/comfyui, r/LocalLLM (hilos 2026 sobre Wan 2.2, LTX y TTS); X: @0xMovez, @ridark_eth (motion design con Claude Code + HyperFrames)
