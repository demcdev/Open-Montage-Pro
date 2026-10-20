# Film Look Finishing — Creative Skill

Acabado de imagen: grano, halación, bloom, viñeta, LUT, empate de color entre planos de modelos distintos y etiquetas de color BT.709 correctas. Es lo que más separa "video IA" de "filmado". La intensidad la decide el **estilo visual**: en animación vectorial plana el acabado es casi nulo; en video IA cinematográfico es parte del look.

`color_grade` (`skills/core/color-grading.md`) elige el grado de color base. Esta skill viene **después**: textura, respuesta a la luz y consistencia entre planos.

## Cuándo usarla

| Momento | Qué se hace |
|---|---|
| `proposal` o biblia de producción | Fijar `style`, LUT y `lut_intensity` de toda la pieza o serie (`skills/meta/production-bible.md`). No cambian entre capítulos |
| `assets` con clips de varios modelos | Después de `clip_conform`: empatar color de cada plano con el plano héroe (`match_reference_path`) |
| `compose` | Acabado final sobre el render (o por plano si el render es HyperFrames y no tiene `fx`) |
| Antes de cualquier lote | Un **preview** de un fotograma aprobado por el usuario (regla "un fotograma → 30 s → producción") |

## Herramienta

`film_look` (`tools/enhancement/film_look.py`). Operaciones:

- `preview`: un fotograma, original | acabado lado a lado (PNG). Siempre primero.
- `apply`: una pasada de FFmpeg. Orden fijo: empate de color → LUT → halación y bloom → viñeta → conversión a yuv420p con matriz BT.709 explícita → grano solo de luma, temporal y con semilla → etiquetas BT.709 en fotogramas y contenedor.
- `measure`: estadísticas de luma, croma y saturación (`signalstats`) para comparar planos.

```json
{
  "operation": "preview",
  "input_path": "projects/<id>/assets/video/sc03_hero.mp4",
  "style": "cinematic_ai",
  "lut_path": "warm_film",
  "lut_intensity": 0.6,
  "preview_at_seconds": 2.0
}
```

## Intensidad por estilo (`style`)

| `style` | Grano | Halación | Bloom | Viñeta | Para qué |
|---|---|---|---|---|---|
| `none` | 0 | 0 | 0 | 0 | Solo etiquetas BT.709 y LUT si se pide |
| `flat_vector` | 0,03 | 0 | 0 | 0 | Animación vectorial plana (HyperFrames, SVG). Una traza de grano solo rompe el bandeo de degradados tras la recompresión de YouTube |
| `anime` | 0,08 | 0 | 0,2 | 0,1 | Anime o cel shading con brillos |
| `stylized_2d` | 0,12 | 0 | 0,1 | 0,15 | Ilustración pintada, collage, 2D con textura |
| `live_action` | 0,25 | 0,2 | 0,1 | 0,2 | Metraje real o stock |
| `cinematic_ai` | 0,35 | 0,3 | 0,15 | 0,25 | Video generado que debe leerse como filmado |
| `archival` | 0,6 | 0,15 | 0 | 0,4 | Material de archivo o flashback |

Cualquier capa se puede fijar a mano (`grain`, `halation`, `bloom`, `vignette`, de 0 a 1) y gana sobre el estilo.

Reglas:

1. **El estilo de la serie manda.** Si la biblia dice `flat_vector`, no se agrega grano "para que se vea más cine". Se cambia solo con aprobación del usuario.
2. **Halación y bloom son para fuentes de luz**: ventanas, lámparas, cielo, reflejos. En una escena sin altas luces no aportan; bajar a 0.
3. **Grano y YouTube:** el grano fuerte se convierte en bloques al recomprimir. Por encima de 0,4 solo en `archival` y revisando el resultado subido como no listado.
4. **Una sola pasada de acabado.** No apilar `film_look` dos veces ni sumarlo a `fx: ["film_grain"]` de Remotion sobre el mismo plano.

## Remotion, HyperFrames y acabado posterior

- **Remotion:** ya tiene `fx` por escena y globales (`film_grain`, `halation`, `vignette`, `letterbox`; ver `skills/creative/camera-motion-library.md`). Si se usan, `film_look` se corre con `style: "none"` solo para LUT y etiquetas, o no se corre.
- **HyperFrames y video unido con FFmpeg:** no hay `fx` de acabado; `film_look` se corre sobre el render final, antes de `audio_master` y de `technical_qc`.
- **Clips de video IA mezclados:** acabado por plano solo para **empatar color**; la textura (grano, halación) se aplica una vez sobre el render final para que sea continua entre cortes.

## Empate de color entre planos de modelos distintos

Cada modelo (Kling, Seedance, Veo, Runway) tiene su propia curva y temperatura. Sin empatar, el corte delata el cambio de modelo.

1. Elegir el **plano de referencia**: el plano héroe aprobado de la escena (`scene_plan.scenes[].hero_moment = true`).
2. `film_look` `measure` sobre la referencia y sobre cada plano: comparar `YAVG`, `YLOW`/`YHIGH` (percentiles 10 y 90), `UAVG`/`VAVG` y `SATAVG`.
3. Si la luma media difiere más de 8 o el croma más de 3, `apply` con `match_reference_path` y `style: "none"`. La herramienta mapea niveles por percentiles, desplaza el croma y ajusta saturación (con límites para no romper el plano).
4. Revisar en un `preview`: el empate es estadístico; un plano de noche contra uno de día no se empata, se replantea.

## Etiquetas de color (BT.709)

Muchos clips de modelos llegan **sin etiquetas** de color. Un reproductor que no sabe qué matriz usar puede asumir BT.601 y desplazar los colores (pieles verdosas, rojos apagados).

- `film_look` convierte a RGB con `input_matrix` explícita (por defecto `bt709`; usar `bt601` solo con fuentes SD antiguas) y escribe `bt709` en primarios, transferencia, matriz y rango `tv`.
- `clip_conform` `analyze` avisa cuando un clip no tiene etiquetas.
- No se usan flujos ACES ni HDR: las fuentes son MP4 Rec.709 de 8 bits y YouTube entrega SDR (decisión en `docs/analisis-skills-faltantes-2026-10.md` §5).

## LUTs

En `assets/luts/` (ver su `README.md`): `identity`, `warm_film`, `teal_orange_soft`, `bleach_bypass_soft`, todos CC0. Un nombre sin extensión se resuelve a esa carpeta. Un LUT de terceros necesita licencia de uso comercial guardada junto al archivo y registrada en el `asset_manifest` (`type: "lut"`, `license`, `original_url`).

## Registro

- `edit_decisions.metadata.film_look`: `style`, capas, LUT e intensidad aplicados (el esquema deja `metadata` abierto).
- `decision_log`: el estilo y el LUT son decisiones de proyecto (categoría `playbook_selection`; un cambio a mitad de producción, `playbook_override`). Si cambian, se registra la decisión nueva; la anterior no se edita.
- `render_report.verification_notes`: "film_look aplicado: <style>, LUT <nombre> al <intensidad>".

## Errores comunes

- Grano en animación vectorial "porque se ve más cine".
- Empatar color después de aplicar el LUT (el empate va antes).
- Aplicar textura por plano: el grano cambia de patrón en cada corte.
- Olvidar las etiquetas: el render se ve bien en el editor y mal en YouTube móvil.
