# Audio Post (Cinema) — Creative Skill

Diseño de sonido por capas para ficción, animación y piezas cinematográficas. Convierte "voz + música de fondo" en un mundo que suena. `skills/creative/sound-design.md` sigue valiendo para explicativos con locución; esta skill es para escenas con personajes, lugares y acción. El nivel final lo fija `skills/core/loudness-mastering.md`.

## Cuándo usarla

- Pipelines `character-animation`, `animation`, `cinematic`, `hybrid` y cualquier explicativo con escenas dramatizadas.
- En `asset-director` (qué sonidos se consiguen o generan) y en `edit-director` (dónde y a qué nivel entran).

## 1. Las cinco capas

| Capa | Qué es | Nivel orientativo en la mezcla | Regla |
|---|---|---|---|
| 1. Diálogo | Voces de personajes y narrador | Picos cerca de −12 dBFS | Siempre inteligible. Todo lo demás se acomoda a la voz |
| 2. Ambiente / room tone | Sonido continuo del lugar: lavandería, calle de noche, corte vacía | −30 a −24 dB | Nunca hay silencio digital dentro de una escena; cada locación tiene su ambiente |
| 3. Foley | Sonidos de los personajes: pasos, ropa, papeles, puerta, taza | −24 a −18 dB | Sincronizado con la acción en pantalla |
| 4. Efectos puntuales | Golpes, apariciones, el martillo, el timbre, transiciones | −18 a −12 dB | Pocos y con intención; uno por momento importante |
| 5. Música | Tema y momentos musicales | −24 a −18 dB bajo la voz (ducking) | Entra y sale a propósito, no suena todo el tiempo |

## 2. Mapa de sonido por escena (spotting)

Antes de buscar sonidos, una tabla por escena en `edit_decisions.metadata.sound_map`:

| Escena | Ambiente | Foley clave | Efectos | Música (entra / sale) | Silencios planeados |
|---|---|---|---|---|---|
| s03 lavandería | Zumbido de lavadoras, fluorescente | Pasos en baldosa, monedas | Titileo eléctrico cuando llega el fantasma | Entra en la tarjeta de título, sale en la primera línea | 1 s tras "Veo a los que ya no respiran" |

Reglas del mapa:

1. **La música es un personaje, no un relleno:** entra en cambios de tono, revelaciones y finales de bloque; sale bajo diálogos importantes o para dar golpe con el silencio.
2. **Cambio de lugar = cambio de ambiente**, idealmente con corte J (el ambiente nuevo entra 0,5–1 s antes de la imagen; ver `editing-craft.md`).
3. **Silencios intencionales** (quitar música o ambiente para que pegue un momento) se declaran en `edit_decisions.metadata.intentional_ranges` para el QC técnico.
4. **Sonido de los personajes fantásticos:** cada criatura o fantasma tiene su firma sonora fija (un tono, un susurro) definida en la biblia y repetida cada vez que aparece.

## 3. De dónde salen los sonidos

Por orden de preferencia y siempre con licencia registrada en el `asset_manifest` (`youtube-policy-gate`):

| Fuente | Para qué | Notas |
|---|---|---|
| Librería de SFX incluida en HyperFrames (`media-use/audio/assets/sfx`, 19 archivos, licencia Pixabay) | Efectos básicos sin credenciales | Primera opción sin costo |
| `media-use` | Música, SFX e imágenes con caché y registro | Deja el archivo congelado y su registro; el catálogo de HeyGen requiere cuenta y aprobación |
| ElevenLabs Sound Effects (`sound-effects`, `elevenlabs`) | Foley y efectos a medida desde una descripción | Requiere clave; describir material, acción y espacio ("pasos en baldosa mojada, eco de pasillo") |
| `pixabay_music`, `freesound_music`, YouTube Audio Library, música propia | Música | Guardar la evidencia de licencia en `assets/music/LICENSES.md` |
| Capa ambiental sintética con FFmpeg (ruido filtrado) | Solo como **provisional** | Sustituirla antes de publicar |

No usar modelos de foley automático con licencias no comerciales (MMAudio, ThinkSound, HunyuanVideo-Foley): el canal monetiza.

## 4. Diálogo

- **Una voz fija por personaje** (proveedor, voz, velocidad) tomada de la biblia; nunca cambiarla entre capítulos sin registrarlo.
- **Espacio coherente:** si la escena es en un ático o una corte enorme, la voz lleva una reverberación corta del lugar; en una oficina pequeña, casi nada. La misma reverb para todos los personajes de la misma escena.
- **Voces TTS:** pasarlas por de-esser (`audio_master` con `deess: true`) y no subir agudos.
- **Superposiciones:** cuando dos personajes se pisan a propósito, la línea principal manda y la otra baja 6 dB.
- **Doblaje EN/ES:** cada idioma tiene su propio mapa de tiempos; el ambiente, el foley y la música se comparten, la voz no. Al cambiar de idioma se ajustan los silencios entre líneas, no la música.

## 5. Mezcla

1. Montar capas por pista en `audio_mixer` (`full_mix`) con `role` por pista: `speech` para diálogo, `music` para música; ambiente, foley y efectos con su volumen fijo.
2. Ducking de la música bajo la voz (`ducking.music_volume_during_speech` 0,15–0,25).
3. Revisar en tres puntos: el inicio, la escena más cargada y el final; con audífonos y con el altavoz del teléfono.
4. Masterizar con `audio_master` y verificar con `technical_qc` (ver `loudness-mastering.md` y `technical-qc-gate.md`).

## Lista de control

- [ ] Ninguna escena tiene silencio digital no planeado.
- [ ] Cada locación tiene ambiente propio.
- [ ] Las acciones visibles importantes tienen foley.
- [ ] La música entra y sale en puntos anotados en el mapa.
- [ ] Todos los sonidos tienen licencia registrada.
- [ ] La capa ambiental sintética provisional fue reemplazada antes de publicar.
- [ ] Máster verificado con `audio_master` y QC técnico en `pass`.

## Integración

- **asset-director:** consigue los sonidos del mapa y registra licencias.
- **edit-director:** coloca las capas y los cortes J/L en `edit_decisions.audio`.
- **production-bible:** voces y firmas sonoras fijas por personaje.
- **loudness-mastering** y **technical-qc-gate:** nivel final y verificación.
