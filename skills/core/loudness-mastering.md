# Loudness Mastering — Core Skill

Cómo dejar el audio final en el volumen correcto para cada plataforma, medido y verificado. Es el último paso de audio antes de entregar.

## Reparto de herramientas

| Paso | Herramienta | Qué hace |
|---|---|---|
| 1. Mezcla | `audio_mixer` (`full_mix`, `mix`, `duck`) | Junta voz, música, ambiente y SFX con ducking. Su `loudnorm` es de una pasada y dinámico: sirve para borradores |
| 2. Máster | `audio_master` operación `master` | Mide, normaliza en **dos pasadas en modo lineal** (una sola ganancia para todo el programa, respeta la dinámica), limita el true peak y vuelve a medir |
| 3. Verificación | `technical_qc` | Confirma el loudness en el archivo final junto con el resto del QC |

Regla: **todo lo que se entrega pasa por `audio_master`**. En la mezcla final, usa `normalize: false` en `audio_mixer` para no normalizar dos veces, o déjalo activo en borradores.

## Objetivos por destino

| Destino | Preset | Integrado | True peak | Nota |
|---|---|---|---|---|
| YouTube (largo y Shorts) | `youtube` | −14 LUFS | −1 dBTP | Convención de la industria. YouTube baja lo que excede, no sube lo que falta: quedar bajo suena débil |
| TikTok, Reels | `social` | −14 LUFS | −1 dBTP | LRA más corto: la gente escucha en el teléfono |
| Podcast | `podcast` | −16 LUFS | −1 dBTP | Apple y Spotify |
| Broadcast Europa | `broadcast_ebu` | −23 LUFS | −1 dBTP | EBU R128 |
| Broadcast EE. UU. | `broadcast_atsc` | −24 LKFS | −2 dBTP | ATSC A/85 |

## Uso

```json
{"operation": "master", "input_path": "renders/capitulo1_es_v2.mp4", "preset": "youtube", "deess": true}
```

- Acepta audio o video. En video copia la imagen sin recodificar y escribe AAC 320 kbps a 48 kHz.
- `deess: true` para voces TTS (Google, ElevenLabs, Azure): suaviza las "s" y "ch" metálicas. No lo uses en música sola.
- El resultado trae `before`, `after`, `delta_lu`, `verification_passed` y `linear_mode`.

## Cómo leer el resultado

| Situación | Significado | Qué hacer |
|---|---|---|
| `verification_passed: true`, `linear_mode: true` | Ideal | Entregar |
| `linear_mode: false` | La ganancia lineal habría pasado el techo de picos y `loudnorm` cayó a modo dinámico | Bajar picos en la mezcla (SFX o golpes de música muy altos) y volver a masterizar |
| `delta_lu` fuera de ±1 | Programa con mucho silencio o muy corto | Revisar silencios largos; en piezas de menos de 10 s la medida integrada es poco fiable |
| `before.input_lra` > 15 LU | Diálogo muy bajo frente a música o efectos muy altos | Corregir niveles en la mezcla, no en el máster |

## Reglas de mezcla que hacen que el máster funcione

1. **La voz manda.** Diálogo con picos alrededor de −12 dBFS en la mezcla; música −18 a −24 dB bajo la voz (ducking en `audio_mixer`).
2. **Un solo máster por entrega.** Si se unen partes, se masteriza el archivo unido, no cada parte por separado (si no, cada parte queda en un nivel distinto).
3. **Versiones por idioma:** cada idioma (EN, ES) se masteriza aparte con el mismo preset. Las voces de cada idioma tienen otra densidad y duración.
4. **No subir el volumen para "competir".** −14 es el techo útil en YouTube; más alto solo se aplasta.
5. **Silencios intencionales:** declararlos en `edit_decisions.metadata.intentional_ranges` para que el QC no los marque.
6. **Muchas pistas: mezclar por escena.** Con unas 100 entradas en un solo comando, FFmpeg se cae en Windows con un código de salida sin mensaje. Mezcla voz y efectos por escena (pistas de igual duración que la escena), une las pistas con concat y haz el ducking de la música sobre la voz unida. Así cada comando tiene ~10 entradas.
7. **Margen para el AAC:** la codificación a AAC sube el true peak unas décimas (−1,0 → −0,9 dBTP medido). Masteriza con `true_peak: -1.5` para que el MP4 final quede bajo −1,0.

## Integración

- **edit-director:** fija `edit_decisions.metadata.loudnorm_target` y `mastering_preset`.
- **compose-director:** corre `audio_master` después del render final y antes de `technical_qc`, y guarda el resultado en `render_report.outputs[].mastering` (`preset`, `verification_passed`, `linear_mode`). Solo se omite si la salida no tiene pista de audio.
- **audio-post-cinema** (`skills/creative/audio-post-cinema.md`): define las capas; esta skill solo fija el nivel final.
