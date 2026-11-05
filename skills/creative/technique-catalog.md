# Technique Catalog — Creative Skill

Las técnicas de video que OpenMontage sabe ejecutar, por familias, con cuándo usarlas, cuándo no y con qué se hacen aquí. Es el menú de `skills/meta/technique-selector.md`: el selector decide; este catálogo describe. No pretende ser exhaustivo del oficio, solo de lo que este proyecto puede entregar o tiene previsto.

## Cuándo usarla

- Al llenar `technique_stack` en la etapa de propuesta o idea.
- Cuando el usuario pregunta qué técnica conviene para algo.
- Al traducir un video de referencia a técnicas propias.

El detalle de cada técnica sigue en su skill. Este catálogo no lo repite.

## Cómo leer las tablas

**ID:** es el valor de `technique_id` en `technique_stack`. No inventes otros; si falta una técnica, añádela aquí.

**Se ejecuta con** usa referencias comprobables, y `tests/contracts/test_technique_selector_contract.py` falla si alguna no existe:

| Prefijo | Apunta a |
|---|---|
| `tool:` | Herramienta del registro (`tools/`) |
| `skill:` | Skill de `skills/` |
| `camera:` `transition:` `fx:` | Entrada de `remotion-composer/src/lib/motion-catalog.json` |
| `text:` | Modo de `kinetic_text` en `docs/MOTION_CATALOG.md` |
| `scene:` `overlay:` | Tipo de `remotion-composer/SCENE_TYPES.md` |

**Sin GPU** dice qué pasa en una máquina sin gráfica dedicada:

| Valor | Significa |
|---|---|
| `local` | Corre en CPU o gráfica integrada |
| `nube` | Corre en un proveedor externo: no pide GPU, pero suele costar y necesita clave |
| `→ id` | Necesita GPU local; usa esa técnica en su lugar |

Una referencia existente no significa disponible en esta máquina. El estado real lo da el registro en el momento de elegir (ver el selector).

**Parcial** y **Pendiente** avisan de que la técnica no está completa. Una pendiente no se promete en una propuesta.

## 1. Origen de la imagen

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `src_user_footage` | Material del usuario | El usuario ya tiene rodaje y su presencia es el valor | El material es pobre y el arreglo costaría más que rehacerlo | `tool:scene_detect`, `tool:video_trimmer` | `local` |
| `src_stock` | Stock | Hace falta mundo real genérico: ciudades, gente, naturaleza | El sujeto es específico, o el plano es el héroe de la pieza | `tool:pixabay_video`, `tool:pexels_video`, `skill:creative/broll-planning.md`, `skill:creative/stock-sourcing-usage.md` | `nube` |
| `src_archive` | Material de archivo | Hechos reales que piden prueba visual | La licencia no está clara | `tool:direct_clip_search`, `skill:meta/guionista-documental.md` | `nube` |
| `src_ai_video` | Video generado | Planos imposibles o caros de rodar, con movimiento real | Hay texto en pantalla, manos en primer plano o el presupuesto es cero | `tool:video_selector`, `skill:creative/video-gen-prompting.md`, `skill:meta/ai-shot-qa.md` | `nube` |
| `src_ai_stills` | Imagen generada animada | Se necesita un mundo propio con poco presupuesto | La promesa exige movimiento real (`motion_required`) | `tool:image_selector`, `camera:ken_burns`, `skill:creative/image-gen-usage.md` | `nube` |
| `src_motion_graphics` | Gráficos por código | Ideas abstractas, datos, marca, cero costo de generación | La emoción depende de personas o lugares reales | `tool:video_compose`, `scene:text_card`, `scene:stat_card`, `scene:callout`, `skill:creative/animation-pipeline.md` | `local` |
| `src_data_viz` | Datos animados | El argumento es un número o una tendencia | El dato no cambia la conclusión | `scene:bar_chart`, `scene:line_chart`, `scene:kpi_grid`, `skill:creative/data-visualization.md` | `local` |
| `src_diagram` | Diagramas | Sistemas, flujos o arquitectura | Una frase lo explica mejor | `tool:diagram_gen`, `skill:creative/diagram-gen-usage.md` | `local` |
| `src_math` | Animación matemática | Demostraciones paso a paso | El público no quiere ecuaciones | `tool:math_animate`, `skill:creative/manim-usage.md` | `local` |
| `src_3d_web` | Mundo 3D en navegador | Recorridos por un espacio inventado | Personajes con actuación fina, o la gráfica integrada no da fluidez | `tool:threejs_world`, `skill:creative/3d-world-generation.md` | `local` |
| `src_3d_blender` | Mundo 3D en Blender | Pieza héroe con materiales y luz de alto nivel | No hay GPU o el plazo es corto | `tool:blender_world`, `skill:creative/3d-world-generation.md` | `→ src_3d_web` |
| `src_character_rig` | Personajes con rig | Serie con personajes recurrentes y consistencia | Una sola aparición: el rig no se amortiza | `tool:character_rig_renderer`, `tool:svg_rig_builder` | `local` |
| `src_ink` | Dibujo a tinta | Humor seco o tono de cuaderno | Se pide realismo o marca corporativa | `skill:creative/ink-theater.md` | `local` |
| `src_animated_drawing` | Animar un dibujo entregado | El usuario trae su dibujo y el encanto es verlo moverse | Se necesita calidad final de vector; es humanoide y ráster | `skill:creative/animated-drawing.md` | `local` |
| `src_screen_capture` | Captura de pantalla | El producto real es el protagonista | La interfaz cambia pronto o hay datos sensibles a la vista | `tool:screen_capture_selector`, `skill:creative/screen-recording.md` | `local` |
| `src_synthetic_ui` | Interfaz simulada | Demo corta y repetible sin grabar | Debe demostrar que el software funciona de verdad | `scene:terminal_scene`, `scene:screenshot_scene` | `local` |
| `src_avatar` | Avatar presentador | Presentador sin rodaje, en varios idiomas | La confianza depende de una persona real | `tool:heygen_avatar`, `tool:kling_avatar` | `nube` |

## 2. Montaje

Detalle en `skills/creative/editing-craft.md`.

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `cut_hard` | Corte seco | Por defecto, casi todo el video | Nunca se evita; es la base | `transition:cut`, `skill:creative/editing-craft.md` | `local` |
| `cut_j` | Corte J | Anticipar un lugar o una voz antes de verla | No hay audio propio del plano siguiente | `tool:audio_mixer`, `skill:creative/editing-craft.md` | `local` |
| `cut_l` | Corte L | Ver la reacción mientras la línea termina | La línea necesita la cara de quien habla | `tool:audio_mixer`, `skill:creative/editing-craft.md` | `local` |
| `cut_action` | Corte en movimiento | Unir tamaños de plano sin salto | Los clips no tienen gesto continuo | `transition:cut`, `skill:creative/editing-craft.md` | `local` |
| `cut_match` | Corte por coincidencia | Saltar de lugar o tiempo con sentido | La forma no coincide de verdad; se planea desde la lista de planos | `transition:cut`, `skill:meta/shot-list-storyboard.md` | `local` |
| `cut_reaction` | Corte de reacción | Chistes, revelaciones, mentiras | Nadie en la escena tiene algo que sentir | `skill:creative/editing-craft.md` | `local` |
| `cut_smash` | Corte de contraste | Humor o susto por oposición brusca | El tono pide gravedad sostenida | `transition:cut`, `skill:creative/editing-craft.md` | `local` |
| `cut_flash` | Corte relámpago | Contradecir en un segundo lo que se acaba de decir | Se repite: pierde la sorpresa | `transition:flash_cut`, `skill:creative/editing-craft.md` | `local` |
| `cut_jump` | Salto en la misma toma | Quitar pausas a quien habla a cámara | Ficción o tono solemne | `tool:silence_cutter`, `skill:creative/video-editing.md` | `local` |
| `cut_parallel` | Montaje paralelo | Dos líneas que se tensan o se comentan | El público ya tiene demasiados hilos | `skill:creative/editing-craft.md` | `local` |
| `cut_dissolve` | Encadenado | Paso de tiempo, pocas veces | Se usa para disimular un mal corte | `transition:dissolve` | `local` |
| `cut_dip` | Fundido a negro | Fin de bloque o capítulo | Dentro de una misma idea | `transition:dip_black` | `local` |
| `cut_whip` | Barrido rápido | Energía, comedia, salto de lugar | Pieza contemplativa | `transition:whip_pan_left`, `transition:whip_pan_right` | `local` |
| `cut_beat` | Corte al pulso | Videoclip o tramo donde la música manda. **Parcial:** solo por HyperFrames con `music-to-video`; la herramienta propia `beat_grid` es de la Fase 5 | Música sin pulso claro: se corta por frases | `skill:core/hyperframes.md` | `local` |
| `cut_escalation` | Escalada de tráiler | Avances y tráileres: planos cada vez más cortos | Contenido que necesita explicarse | `skill:creative/title-thumbnail-trailer.md`, `skill:creative/editing-craft.md` | `local` |

## 3. Cámara y puesta en escena

En imágenes y gráficos, los movimientos son aproximaciones 2D. Para movimiento 3D real usa `src_ai_video` con el `ai_prompt` del movimiento, o `src_3d_web`. Detalle en `skills/creative/camera-motion-library.md`.

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `cam_coverage` | Cobertura de planos | Toda escena con personas o personajes | Pieza puramente gráfica | `skill:creative/cinematography.md` | `local` |
| `cam_static` | Plano fijo | Dejar que la acción o el dato hablen | Imagen fija sin nada que mire el ojo | `camera:static`, `camera:breathe` | `local` |
| `cam_push` | Acercamiento | Presentar un sujeto o subir la tensión | Todos los planos lo llevan: deja de significar | `camera:dolly_in`, `camera:zoom_in_slow` | `local` |
| `cam_pull` | Alejamiento | Revelar escala o contexto, o cerrar | No hay nada más que revelar | `camera:dolly_out`, `camera:zoom_out_slow` | `local` |
| `cam_ken_burns` | Paneo sobre foto | Fotos de archivo con detalle | Sustituye movimiento prometido | `camera:ken_burns`, `camera:ken_burns_reverse` | `local` |
| `cam_parallax` | Paralaje | Dar profundidad a una imagen fija | La imagen no separa bien primer plano y fondo | `camera:parallax_drift`, `camera:truck_left` | `local` |
| `cam_handheld` | Cámara en mano | Urgencia, testimonio, realismo | Producto o tono institucional | `camera:handheld`, `camera:documentary_drift` | `local` |
| `cam_crash` | Zoom de golpe | Gancho, chiste o dato grande | Más de una o dos veces por pieza | `camera:crash_zoom_in`, `camera:punch_in` | `local` |
| `cam_orbit` | Órbita | Mostrar un objeto héroe | Fondo plano: en 2D se nota que es falso | `camera:orbit_cw`, `camera:arc_left` | `local` |
| `cam_crane` | Grúa | Apertura o cierre de escala | Espacios sin altura que mostrar | `camera:crane_up`, `camera:crane_down` | `local` |
| `cam_fpv` | Vuelo en primera persona | Recorridos que venden el espacio | Sin movimiento real suena a truco; pide 3D o video generado | `camera:fpv_drone`, `camera:flythrough` | `local` |
| `cam_dolly_zoom` | Vértigo | Una revelación que cambia todo | Sin motivo dramático | `camera:dolly_zoom` | `local` |
| `cam_dutch` | Plano inclinado | Inquietud o locura | Sin motivo narrativo parece error | `camera:dutch_angle` | `local` |
| `cam_rack_focus` | Cambio de foco | Pasar la atención de un punto a otro | El plano no tiene dos términos claros | `fx:rack_focus`, `fx:depth_blur` | `local` |

## 4. Motion graphics y texto

Detalle en `skills/creative/typography.md` y `skills/creative/camera-motion-library.md`.

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `mot_kinetic_type` | Tipografía cinética | Frases clave, ganchos, citas | Texto largo: no da tiempo a leer | `scene:kinetic_text`, `text:word_pop`, `text:mask_wipe` | `local` |
| `mot_stat_reveal` | Revelado de cifra | Un número sorprendente | Varias cifras seguidas sin jerarquía | `scene:stat_card`, `overlay:stat_reveal` | `local` |
| `mot_annotation` | Señalar en el plano | Dirigir la mirada a un detalle | El detalle ya es evidente | `overlay:focus_ring`, `overlay:arrow` | `local` |
| `mot_lower_third` | Rótulo inferior | Presentar personas o lugares | Se repite con la misma persona | `overlay:lower_third` | `local` |
| `mot_split_screen` | Pantalla dividida | Comparar o mostrar simultaneidad | Vertical con paneles pequeños | `scene:split_screen` | `local` |
| `mot_comparison` | Comparación animada | Antes y después, A contra B | Las dos opciones no son comparables | `scene:comparison` | `local` |
| `mot_scale` | Comparación de escala | Tamaños difíciles de imaginar | La escala no es el punto | `scene:scale_comparison` | `local` |
| `mot_collage` | Collage | Muchas pruebas o ejemplos a la vez | Cada elemento necesita leerse | `scene:collage` | `local` |
| `mot_double_exposure` | Doble exposición | Unir persona e idea en un plano | Las dos imágenes compiten por el mismo espacio | `scene:double_exposure` | `local` |
| `mot_svg_draw` | Trazo que se dibuja | Logos, mapas y esquemas que aparecen | Formas sin contorno claro | `skill:meta/animation-runtime-selector.md` | `local` |
| `mot_hud` | Interfaz sobre imagen | Vigilancia, ciencia, tono técnico | Decora sin aportar información | `overlay:hud_frame` | `local` |

## 5. Acabado de imagen

Detalle en `skills/creative/film-look-finishing.md`.

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `fin_grade` | Gradación de color | Toda pieza con material de varias fuentes | Gráficos puros con paleta propia | `tool:color_grade`, `skill:core/color-grading.md` | `local` |
| `fin_film_look` | Aspecto de película | Dar cuerpo a video generado o digital | Interfaz o tutoriales: ensucia la lectura | `tool:film_look`, `skill:creative/film-look-finishing.md` | `local` |
| `fin_conform` | Igualar y estabilizar clips | Mezclar fuentes de distinto fps o trepidación | Material ya homogéneo | `tool:clip_conform`, `skill:creative/clip-conform.md` | `local` |
| `fin_letterbox` | Franjas de cine | Tono de película en 16:9 | Vertical o móvil: gasta pantalla | `fx:letterbox` | `local` |
| `fin_glow` | Resplandor y halación | Luces que deben sentirse físicas | Texto pequeño: pierde lectura | `fx:bloom`, `fx:halation` | `local` |
| `fin_stylized` | Estética de época | Un recuerdo, un archivo falso, un pasaje | Se usa en todo el video | `fx:vhs`, `fx:crt`, `fx:grade_sepia` | `local` |
| `fin_freeze` | Congelado | Remarcar un instante o presentar a alguien | No está declarado en `intentional_ranges`: el QC lo marcará | `fx:freeze` | `local` |
| `fin_motion_blur` | Desenfoque direccional | Reforzar un barrido rápido. **Parcial:** es un filtro 2D, no desenfoque real de render | Se espera desenfoque por movimiento de objetos | `fx:motion_blur` | `local` |
| `fin_speed_ramp` | Rampa de velocidad | Acentuar un golpe de acción. **Parcial:** hoy hay velocidad constante por corte (`cut.speed`) y empuje de cámara con rampa; el reajuste real sobre clips es de la Fase 5 | Se necesita cámara lenta fluida con clips de pocos fps | `camera:ramp_push_in`, `camera:ramp_pull_out` | `local` |
| `fin_upscale` | Escalado | El material fuente vale y falta resolución | No hay GPU: mejor regenerar a mayor resolución | `tool:upscale`, `skill:creative/upscale-usage.md` | `→ src_ai_video` |

## 6. Sonido

Detalle en `skills/creative/audio-post-cinema.md` y `skills/creative/sound-design.md`.

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `snd_voiceover` | Voz en off | Explicar o guiar | La imagen ya lo cuenta todo | `tool:tts_selector`, `skill:meta/voice-performance-director.md` | `nube` |
| `snd_voice_cleanup` | Limpieza de voz | Voz grabada con ruido | Voz sintética ya limpia | `tool:audio_enhance` | `local` |
| `snd_music_bed` | Música de fondo | Sostener tono y ritmo | Compite con voz densa, o la licencia no está clara | `tool:pixabay_music`, `tool:music_gen`, `skill:creative/music-gen-usage.md` | `nube` |
| `snd_ducking` | Bajar música bajo la voz | Siempre que convivan voz y música | Pieza sin voz | `tool:audio_mixer`, `skill:creative/sound-design.md` | `local` |
| `snd_layers` | Diseño sonoro por capas | Ficción, cine y documental | Tutoriales: distrae | `tool:audio_mixer`, `skill:creative/audio-post-cinema.md` | `local` |
| `snd_sfx_accent` | Efectos de acento | Cortes, apariciones y golpes de ritmo | En cada animación: se vuelve ruido | `tool:audio_mixer`, `skill:creative/sound-design.md` | `local` |
| `snd_silence` | Silencio como golpe | Antes de una revelación | No está declarado en `intentional_ranges`: el QC lo marcará | `skill:creative/editing-craft.md` | `local` |
| `snd_master` | Máster final | **Siempre.** Es obligatorio en toda entrega con audio | Nunca se omite | `tool:audio_master`, `skill:core/loudness-mastering.md` | `local` |

## 7. Posproducción asistida

| ID | Técnica | Úsala cuando | Evítala cuando | Se ejecuta con | Sin GPU |
|---|---|---|---|---|---|
| `post_green_screen` | Croma | Hay fondo verde bien iluminado | Bordes o pelo con mala luz | `tool:green_screen_composite`, `tool:green_screen_processor` | `local` |
| `post_bg_remove` | Quitar fondo | Sacar un sujeto sin croma | Bordes complejos en movimiento rápido | `tool:bg_remove`, `skill:creative/bg-remove-usage.md` | `local` |
| `post_reframe` | Reencuadre vertical | Sacar 9:16 de un 16:9 | El encuadre original usa todo el ancho | `tool:auto_reframe` | `local` |
| `post_lip_sync` | Sincronía labial | Doblaje o avatar | Plano lejano: no compensa | `tool:kling_lip_sync`, `skill:creative/lip-sync-usage.md` | `nube` |
| `post_subtitle_files` | Subtítulos en archivo | **Por defecto** en YouTube: SRT o VTT | Nunca se evita si hay habla | `tool:subtitle_gen`, `skill:core/subtitle-sync.md` | `local` |
| `post_caption_burn` | Subtítulos quemados | Solo si el usuario lo pide para un formato ajeno al canal | Canal propio: la norma es sin subtítulos quemados | `tool:remotion_caption_burn`, `skill:meta/youtube-policy-gate.md` | `local` |

## Integración

- **technique-selector:** elige de este catálogo y deja el resultado en `technique_stack`.
- **animation-runtime-selector:** se aplica después; el motor sirve a la técnica, no al revés.
- **editing-craft, camera-motion-library, audio-post-cinema:** son el detalle de cada familia.
