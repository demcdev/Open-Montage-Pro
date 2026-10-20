# Clip Conform — Creative Skill

Igualar los clips antes de editar: misma cadencia (24 o 30 fps), sin parpadeo, estables y del tamaño de la línea de tiempo. Los clips de distintos modelos llegan a 16, 24, 25 o 30 fps, a veces con fps variable, parpadeo de luz o menor resolución. Si no se igualan, el corte se nota aunque el contenido sea bueno.

## Cuándo usarla

- `asset-director`, en cuanto llega cada clip generado o de stock, **antes** de revisarlo con `skills/meta/ai-shot-qa.md` y antes del empate de color de `skills/creative/film-look-finishing.md`.
- Al recibir metraje real o de archivo para `documentary-montage`, `hybrid` o `talking-head`.
- No hace falta en animación renderizada por HyperFrames o Remotion: ya sale a los fps de la composición.

## Herramienta

`clip_conform` (`tools/video/clip_conform.py`).

| Operación | Qué hace |
|---|---|
| `analyze` | fps (y si es variable), tamaño, códec, etiquetas de color e **índice de parpadeo**. Devuelve `recommendations`; no cambia nada |
| `conform` | Una pasada (dos con estabilización): deflicker → denoise ligero → estabilización → fps → tamaño → yuv420p |
| `slow_motion` | Cámara lenta con interpolación por movimiento (`minterpolate`); el audio se descarta |

```json
{
  "operation": "conform",
  "input_path": "projects/<id>/assets/video/sc04_kling.mp4",
  "target_fps": 24,
  "content_type": "generated",
  "deflicker": true,
  "target_width": 1920,
  "target_height": 1080
}
```

## Cadencia del proyecto

- **24 fps** para ficción, cinematic y documental. **30 fps** para explicativos, screen-demo y redes cuando el resto del material ya está a 30.
- Se fija en la propuesta y en la biblia; todos los clips se conforman a ese valor. No se mezclan 24 y 30 en una línea de tiempo.
- No se sube todo a 60 fps: contradice el estándar de cine y duplica el peso sin ganar nada.

## Método de fps (`fps_method`, por defecto `auto`)

| Fuente → destino | `auto` elige | Por qué |
|---|---|---|
| Igual (±0,2 %) | `none` | Solo normaliza fps variable a constante |
| Menor, video generado o real (16 → 24) | `interpolate` | Crea los fotogramas que faltan. Es el único caso, junto con la cámara lenta, en que se interpola |
| Menor, `content_type: "animation"` (12 → 24) | `drop` | La animación "en dos" duplica dibujos. Interpolar los derrite; la herramienta se niega |
| Un poco mayor, ≤5 % (25 → 24) | `retime` | Reproduce los mismos fotogramas más lento (+4 % de duración) y ajusta el audio con `atempo` sin cambiar el tono. Evita un tirón por segundo |
| Mayor (30 → 24, 60 → 24) | `drop` | Descarta fotogramas. Si un paneo se ve a saltos, probar `blend` |

`retime` cambia la duración: se mide de nuevo el clip antes de armar `edit_decisions`.

## Parpadeo, ruido y estabilización

- **Deflicker:** activar cuando `analyze` da `flicker_index` > 0,012 o el usuario ve "respirar" la luz. El índice mide la luma que salta de un fotograma a otro sin seguir una tendencia; un paneo o un fundido no lo suben. `deflicker_size` 5 es suave; subir a 9–15 solo si persiste.
- **Denoise `light`:** para stock comprimido o metraje oscuro. No en video IA limpio (borra detalle) ni en animación.
- **Estabilización:** solo con temblor real (cámara en mano, dron, deriva del modelo). Usa `vidstab` en dos pasadas si el FFmpeg lo trae; si no, `deshake` (más débil) y la herramienta lo avisa en `warnings`. Revisar bordes que ondulan; `stabilize_smoothing` 10 es moderado. No estabilizar un movimiento de cámara intencional.

## Resolución, reescalado y rostros

- `target_width` + `target_height` con `resize_mode`: `fill` (escala y recorta al centro; por defecto) o `fit` (barras negras). Para cambiar de 16:9 a 9:16 con seguimiento de rostro se usa `auto_reframe`, no esta herramienta.
- **Reescalado:** si la fuente es menor que el destino, `lanczos` sirve hasta ~1,5×. Más que eso (720p → 1080p con detalle fino, o 480p → 1080p), `upscale_method: "realesrgan"` delega en la herramienta `upscale` (Real-ESRGAN, ver `skills/creative/upscale-usage.md`); `face_enhance: true` pasa GFPGAN sobre los rostros. Si `upscale` no está instalada, la operación falla y lo dice: no se baja a `lanczos` en silencio.
- **Restauración de rostros:** `face_restore` (CodeFormer, `skills/creative/face-restore-usage.md`) trabaja sobre imágenes. Se usa en el fotograma clave **antes** de imagen-a-video, no cuadro por cuadro sobre el clip (parpadea).
- **Archivo antiguo:** `analyze` → `conform` con `denoise: "light"` y `deflicker` → `upscale` si hace falta → acabado `archival` en `film_look`.

## Cámara lenta

`slow_motion` con `slow_motion_factor` (2 = mitad de velocidad). Funciona mejor con movimiento simple y fondo estable; las manos, el pelo y los objetos que se cruzan generan artefactos. Revisar cada fotograma del tramo. Si el modelo de video permite generar la cámara lenta directamente, es mejor que interpolar.

## Registro

- `asset_manifest.assets[]`: el clip conformado es el que se usa; su `generation_summary` dice "conform: 16→24 interpolate, deflicker" (el esquema no admite campos nuevos por asset; los detalles van en `asset_manifest.metadata.conform_log[]` con el `data` de la herramienta).
- Si `warnings` no está vacío, mencionarlo en el checkpoint de `assets`.

## Errores comunes

- Interpolar animación dibujada.
- Conformar después de editar (las duraciones de `retime` ya no cuadran).
- Estabilizar un plano con movimiento de cámara pensado.
- Reescalar 4× con `lanczos` y esperar detalle.
