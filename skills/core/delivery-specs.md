# Delivery Specs — Core Skill

Especificaciones de entrega por destino: qué archivo se exporta para YouTube 16:9, Shorts, Reels y TikTok; cómo se arman las versiones en inglés y en español; normas de subtítulos SRT/VTT y capítulos. Un solo lugar para no resolverlo distinto en cada pipeline.

**Regla del proyecto: nunca se queman subtítulos en el video.** Los subtítulos son archivos `.srt` o `.vtt` aparte que se cargan en la plataforma. Los textos en pantalla que son parte del diseño (títulos, letreros, rótulos de nombre) no son subtítulos.

> Las cifras de plataformas cambian. Están verificadas a 2026-10 contra la ayuda oficial de cada plataforma tal como se conocía; ante una diferencia, manda la ayuda oficial vigente y se actualiza esta tabla.

## Cuándo usarla

- `proposal-director`: elegir destino(s) y formato antes de producir (`brief.target_platform`: `youtube`, `instagram`, `tiktok`, `linkedin` o `generic`).
- `compose-director`: exportar el máster con estas especificaciones; `technical_qc` lo comprueba (`expected`).
- `publish-director`: armar el paquete por idioma y por plataforma con `export_bundle`.

## Máster por destino

| Destino | Lienzo | fps | Video | Audio | Duración | Notas |
|---|---|---|---|---|---|---|
| **YouTube 16:9** | 1920×1080 (o 3840×2160) | El del proyecto (24 o 30), sin convertir | H.264 High, yuv420p, BT.709, `-movflags +faststart`. ~8 Mbps a 1080p 24/30 (12 a 48/60 fps); en la práctica CRF 16–18 | AAC-LC estéreo, 48 kHz, 320–384 kbps; −14 LUFS, −1 dBTP | Sin límite práctico | Subir el máster de mayor calidad; YouTube recomprime todo |
| **YouTube Shorts** | 1080×1920 (9:16) | Igual que el largo | Igual | Igual | Hasta 3 min | Ganchos en el primer segundo; la interfaz tapa la franja inferior |
| **Instagram Reels** | 1080×1920 | 24–30 | H.264, yuv420p | AAC 48 kHz, −14 LUFS | Hasta 3 min en Reels | Zona segura: dejar libre ~14 % arriba y ~20 % abajo para la interfaz |
| **TikTok** | 1080×1920 | 24–30 | H.264, yuv420p | AAC 48 kHz, −14 LUFS | Según la cuenta (minutos) | Zona segura similar a Reels, más margen a la derecha (botones) |

- El perfil de loudness viene de `skills/core/loudness-mastering.md` (`audio_master` preset `youtube` o `social`).
- La comprobación técnica es `technical_qc` con `profile` `youtube` o `social` y `expected` con lienzo, fps y códec de esta tabla (`skills/meta/technical-qc-gate.md`).
- Las etiquetas de color BT.709 las escribe `film_look` (`skills/creative/film-look-finishing.md`).
- Para pasar de 16:9 a 9:16 se usa `auto_reframe` (seguimiento de rostro) o una composición vertical nativa; nunca barras negras arriba y abajo en un Short.
- Nombres de archivo: `<serie>_<capítulo>_<idioma>_v<n>.mp4` (por ejemplo `vigilante_c03_es_v2.mp4`), y el mismo nombre base para `.srt`, `.vtt` y miniaturas.

## Versiones en inglés y en español

Cada idioma es una **versión completa**, no un subtítulo encima de la otra:

| Pieza | Qué cambia por idioma |
|---|---|
| Voz | Doblaje completo (TTS) por idioma, con su propia actuación (`skills/meta/voice-performance-director.md`) |
| Mezcla | Se remezcla y se masteriza cada idioma por separado: el texto cambia de largo y de ritmo |
| Textos en pantalla | Rótulos, letreros y títulos en el idioma de la versión |
| Subtítulos | `.srt`/`.vtt` del mismo idioma (accesibilidad) y, opcional, del otro idioma |
| Metadatos | Título, descripción, capítulos y etiquetas traducidos y adaptados, no calcados |
| Miniatura | Texto de la miniatura en el idioma de la versión (`skills/creative/title-thumbnail-trailer.md`) |

Cómo publicar en YouTube (decisión del usuario, se registra en el `decision_log`):

1. **Dos videos** (uno por idioma, en el mismo canal o en canales separados): lo más simple y compatible.
2. **Un video con varias pistas de audio**, si el canal tiene disponible la función de audio en varios idiomas: un solo máster de imagen y una pista de audio por idioma. Requiere que la imagen no lleve texto de un idioma (o que el texto sea neutral).

En ambos casos el título y la descripción del otro idioma se cargan en YouTube Studio como traducciones.

## Subtítulos (SRT y VTT)

Se generan con `subtitle_gen` a partir de la transcripción con tiempos por palabra (`skills/core/subtitle-sync.md`). Normas:

| Norma | Valor |
|---|---|
| Caracteres por línea | Máximo 42 (`max_chars_per_line: 42`) |
| Líneas por subtítulo | Máximo 2 |
| Velocidad de lectura | Hasta 17 caracteres por segundo en adultos (13 para público infantil) |
| Duración | Mínimo 0,83 s (5/6 de segundo), máximo 7 s |
| Separación | Al menos 2 fotogramas entre subtítulos |
| Cortes de línea | Por unidad de sentido: no separar artículo y sustantivo ni nombre y apellido |
| Diálogo | Un guion (`-`) por hablante cuando dos hablan en el mismo subtítulo |
| Sonidos relevantes | Entre corchetes en la pista de accesibilidad: `[puerta que se cierra]` |
| Formato | `.srt` (UTF-8) para YouTube; `.vtt` cuando el reproductor lo pide. Mismo contenido |

- Los subtítulos de la versión en español se generan desde la voz en español, no se traducen desde el SRT en inglés (los tiempos no coinciden).
- Nombres propios y términos de la serie: lista de correcciones en `subtitle_gen` (`corrections`) desde la biblia.
- `edit_decisions.subtitles.enabled` queda en `false` para el render (no se queman); la ruta del archivo va en `export_bundle.subtitles_path`.

## Capítulos de YouTube

- El primero empieza en `00:00`; mínimo 3 capítulos; cada uno de al menos 10 s.
- Títulos cortos que prometen algo, sin destripar la sorpresa final.
- Se pasan a `export_bundle` como `chapters` (`{start_seconds, title}`) y quedan en `publish_log.entries[].metadata_used.chapters`.

## Paquete de entrega

`export_bundle` una vez **por idioma** (acepta un solo `subtitles_path`): `video_path`, `title`, `description`, `tags`, `chapters`, `subtitles_path`, `thumbnail_path` y `platform` (`youtube`, `youtube_shorts`, `instagram_reels`, `tiktok`). Escribe la entrada de `publish_log` con `status: "exported"`; `export_bundle` no sube nada a ninguna plataforma.

## Lista final

- [ ] Máster con lienzo, fps, códec y loudness de la tabla; `technical_qc` en `pass`
- [ ] Sin subtítulos quemados; `.srt` (y `.vtt` si aplica) por idioma
- [ ] Velocidad de lectura y largo de línea dentro de norma
- [ ] Capítulos válidos (00:00, ≥3, ≥10 s)
- [ ] Una versión completa por idioma (voz, mezcla, textos, metadatos, miniatura)
- [ ] Zona segura respetada en verticales
- [ ] `youtube-policy-gate` pasado (divulgación de IA, música, miniatura honesta)
