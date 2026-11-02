# Technical QC Gate — Meta Skill

Puerta técnica obligatoria antes de entregar o publicar cualquier render. Revisa lo que se puede **medir**: negros, imagen congelada, silencios, loudness, true peak, conformidad del archivo y licencias. Lo **creativo** (si el corte funciona, si el chiste pega) sigue en `skills/meta/reviewer.md`. Son dos revisiones distintas y las dos son obligatorias.

## Cuándo usarla

| Momento | Qué se corre | Por qué |
|---|---|---|
| Después de cada render de **parte o escena** que se va a mostrar al usuario | `technical_qc` con el perfil de destino | El usuario no debe descubrir un frame negro o un silencio que una máquina detecta en segundos |
| Después de **unir partes** (concat con FFmpeg) | `technical_qc` sobre el archivo unido | Las uniones son donde aparecen huecos, saltos de volumen y frames negros |
| En el **compose-director**, antes del checkpoint `compose` | `technical_qc` + `asset_manifest_path` | El checkpoint no se marca `completed` con veredicto `block` |
| En el **publish-director**, antes de `export_bundle` | Último `technical_qc` sobre el máster final | Es el archivo que se sube; nada de lo anterior cuenta si este cambió |

## Herramienta

`technical_qc` (`tools/analysis/technical_qc.py`). Una sola pasada de decodificación con `blackdetect`, `freezedetect`, `silencedetect` y `ebur128`, más `ffprobe`. Escribe `<render>.qc.json` junto al archivo.

```json
{
  "input_path": "renders/capitulo1_es_v2.mp4",
  "profile": "youtube",
  "expected": {"width": 1920, "height": 1080, "fps": 24, "video_codec": "h264", "pixel_format": "yuv420p", "sample_rate": 48000},
  "freeze_min_seconds": 4.0,
  "intentional_ranges": [{"start": 212.0, "end": 214.0, "reason": "silencio cuando Walter intenta decir el nombre"}],
  "asset_manifest_path": "projects/<id>/artifacts/asset_manifest.json"
}
```

Perfiles: `youtube` y `social` (−14 LUFS, −1 dBTP), `podcast` (−16), `broadcast_ebu` (−23), `broadcast_atsc` (−24, −2 dBTP).

## Veredicto y qué hacer

| Veredicto | `exit_code` | Acción |
|---|---|---|
| `pass` | 0 | Seguir. Mencionar en el resumen del checkpoint que el QC pasó |
| `warn` | 10 | Abrir **cada** marca de tiempo señalada (`visual_qa` operación `review` en esos segundos) y decidir: real → corregir; intencional → agregarla a `intentional_ranges` y volver a correr. No se entrega con advertencias sin revisar |
| `block` | 1 | No se entrega ni se publica. Corregir y volver a correr. Nunca bajar umbrales para que pase |

Bloquea siempre: video completamente negro, sin pista de video, loudness a más de 3 LU del objetivo, true peak por encima de −0,1 dBTP (recorte), resolución, fps o códec distintos al pedido, y cualquier asset sin licencia en el `asset_manifest`.

## Cómo evitar falsos positivos (sin ocultar problemas)

- **Animación con poses sostenidas:** la animación vectorial tiene planos quietos a propósito. Sube `freeze_min_seconds` a 4–6 s para animación y deja 2 s para video generado o metraje real. Un congelado de 2 s en video IA casi siempre es un error del modelo.
- **Fundidos al inicio y al final:** el negro o el silencio que toca los bordes dentro de `edge_grace_seconds` (1,5 s) se reporta como `info`.
- **Silencios dramáticos y cortes a negro planeados:** se declaran en `edit_decisions.metadata.intentional_ranges` y se pasan tal cual a la herramienta. Si no estaban planeados, son errores.
- **Escenas de espacio:** un cielo negro con estrellas y poco más se mide como negro. Si es parte del chiste o del mapa, va en `intentional_ranges`; si es un plano de gancho, el aviso tiene razón: añade contenido (en el turista se resolvió con un mapa del viaje).
- **No uses un rango intencional para tapar una toma quieta durante la voz.** Si el personaje solo parpadea 3 s o más, dale movimiento (ver «Congelado en animación» abajo).

## Arreglos típicos

| Hallazgo | Causa probable | Arreglo |
|---|---|---|
| Negro corto entre partes | Concat con duraciones desalineadas o un clip que no cargó | Re-unir con duraciones exactas; revisar el clip faltante |
| Audio que se adelanta al final | Un render de escena salió un fotograma más largo | `outpoint <duración exacta>` por clip en la lista de concat (ver `skills/core/hyperframes.md`) |
| Congelado en animación vectorial durante la voz | Pose sostenida sin movimiento secundario | Reposo leve (cuello, hombros, torso) o un acercamiento lento de cámara; no subir el umbral para ocultarlo |
| Congelado en video generado | El modelo se quedó quieto o se extendió un clip | Regenerar el plano o recortarlo |
| Silencio no planeado | Pista de voz que no empezó a tiempo o capa ambiental cortada | Revisar `start_seconds` de las pistas en el mix |
| Loudness fuera de objetivo | Mezcla sin masterizar | Correr `audio_master` (ver `skills/core/loudness-mastering.md`) y volver a pasar el QC |
| True peak alto | Picos de SFX o música sin limitar | `audio_master` con el preset correcto; nunca solo subir el volumen |
| Asset sin licencia | Música o SFX sin evidencia | Completar `license` y la evidencia (ver `youtube-policy-gate`) o reemplazar el asset |

## Integración

- **Reviewer:** el reporte de QC se adjunta a la revisión del stage `compose`. El reviewer no repite estas medidas; se concentra en lo creativo.
- **Checkpoint:** incluir en el resumen `verdict`, conteo de `block/warn/info` y la ruta del reporte.
- **Decision log:** si se acepta una advertencia como intencional, registrar la decisión (categoría `qc_exception`).
- **Política de YouTube:** `youtube-policy-gate` decide qué se puede publicar; esta skill comprueba que el archivo cumple técnicamente.
