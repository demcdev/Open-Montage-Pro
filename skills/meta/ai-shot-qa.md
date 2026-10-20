# AI Shot QA — Meta Skill

Revisión de cada plano de **video generado** antes de montarlo: manos, deformaciones (morphing), parpadeo, cambio de rostro o de vestuario, física imposible y texto ilegible. Decide **aceptar, recortar o regenerar** con un umbral fijo y deja registro de cada rechazo para no repetir el mismo prompt.

Solo aplica a video generado por modelos (Kling, Seedance, Veo, Runway, Sora, LTX, Wan, MiniMax, etc.). No aplica a animación vectorial renderizada por HyperFrames o Remotion, que se revisa con `skills/meta/reviewer.md`.

Es distinta de `skills/meta/technical-qc-gate.md`: aquella mide el render final (negros, silencios, loudness); esta mira cada plano generado, uno por uno, antes de editar.

## Cuándo usarla

| Momento | Qué se revisa |
|---|---|
| `asset-director`, al recibir cada clip generado | El clip ya conformado (`skills/creative/clip-conform.md`) |
| Antes de un lote | Los 1–2 planos de muestra; si fallan, se corrige el prompt antes de gastar en el resto |
| Al regenerar | El plano nuevo, con la misma lista |

## Herramientas

| Herramienta | Uso aquí |
|---|---|
| `frame_sampler` | Extraer fotogramas: `strategy: "interval"` con `interval_seconds: 0.5` (un clip de 5 s da 10 fotogramas). Para movimiento rápido, 0.25 |
| Inspección visual del agente | **La revisión principal.** Abrir cada fotograma extraído como imagen y recorrer la lista de defectos. Los modelos de visión locales no detectan dedos de más con fiabilidad |
| `video_understand` | Filtro previo y segunda opinión: `mode: "quality"` para nitidez y ruido; `mode: "qa"` con preguntas concretas ("How many fingers does the left hand have?"). Corre local (CLIP, BLIP-2 o LLaVA); si no está instalado, se sigue solo con inspección visual |
| `clip_conform` `analyze` | `flicker_index` objetivo para el parpadeo |
| `technical_qc` | Sobre el clip suelto con `freeze_min_seconds: 2`: un congelado en video IA casi siempre es un error del modelo |

```json
{"tool": "frame_sampler", "input_path": "projects/<id>/assets/video/sc05_take2.mp4", "strategy": "interval", "interval_seconds": 0.5, "output_dir": "projects/<id>/qa/sc05_take2"}
```

## Lista de defectos y gravedad

| Defecto | Cómo se ve | Gravedad |
|---|---|---|
| Rostro cambia | Otra cara, otra edad o rasgos que se mueven entre fotogramas; no coincide con la hoja del personaje | **Crítico** si el personaje es reconocible |
| Morphing | Un objeto o un cuerpo se convierte en otro; extremidades que se funden | **Crítico** |
| Manos | Dedos de más o de menos, dedos fundidos, mano que atraviesa objetos | **Crítico** en primer plano; mayor en plano general |
| Vestuario o utilería cambia | Color, prenda u objeto distinto a la biblia (`skills/meta/production-bible.md`) | **Mayor** |
| Física imposible | Pies que patinan, objetos que flotan, líquido que sube | **Mayor** |
| Parpadeo | La luz "respira"; `flicker_index` > 0,012 | **Menor** si `deflicker` lo arregla; **mayor** si no |
| Texto | Letreros o pantallas con letras inventadas | **Mayor** si se lee en cuadro; menor si está desenfocado |
| Congelado o deriva | El plano se queda quieto o la cámara se va sola | **Mayor** |
| Fondo inestable | Arquitectura que cambia, multitudes que se deforman | **Menor** en planos cortos |

## Umbral de decisión

| Resultado | Decisión |
|---|---|
| Ningún defecto crítico ni mayor | **Aceptar** |
| Defectos solo en un tramo y el resto sirve para la duración del plano en `scene_plan` | **Recortar** (`video_trimmer`) y anotar el tramo usado |
| Un menor que se arregla en post (parpadeo, ruido) | **Aceptar con arreglo**: `clip_conform` o `film_look`, y volver a revisar |
| Cualquier crítico en el tramo que se va a usar, o dos o más mayores | **Regenerar** |
| Tercer intento fallido del mismo plano | **Escalar al usuario**: cambiar el enfoque (otro encuadre, imagen-a-video con fotograma clave aprobado, otro modelo o un plano fijo animado) en vez de seguir pagando |

Reglas:

1. **Defecto en un plano héroe** (`scene_plan.scenes[].hero_moment = true`): nunca se acepta con defectos mayores.
2. **No se "esconde" un defecto crítico** con un corte rápido o un desenfoque; se ve al pausar y en la miniatura.
3. Antes de regenerar, **cambiar algo**: el prompt, la semilla, el encuadre o el fotograma clave. Regenerar con lo mismo es pagar dos veces el mismo error. Las causas típicas y sus arreglos están en `skills/creative/video-gen-prompting.md` y en la skill de capa 3 del modelo.
4. El costo de cada intento cuenta contra el presupuesto (`skills/meta/budget-and-model-routing.md`).

## Registro de rechazos

El esquema de `asset_manifest.assets[]` no admite campos nuevos; el registro va en `asset_manifest.metadata.shot_qa[]` (objeto abierto):

```json
{
  "scene_id": "sc05",
  "take": 2,
  "path": "assets/video/sc05_take2.mp4",
  "model": "kling-v2",
  "verdict": "regenerate",
  "defects": [{"type": "hands", "severity": "critical", "at_seconds": 3.5, "note": "six fingers on the right hand"}],
  "frames_dir": "qa/sc05_take2",
  "change_for_next_take": "image-to-video from the approved keyframe; hands out of frame"
}
```

- El plano aceptado entra en `asset_manifest.assets[]` con `quality_score` (0–1): 1 sin defectos, 0,8 con menores arreglados, 0,6 recortado.
- Cada regeneración que cambia de modelo o de enfoque va al `decision_log` (categoría `visual_accuracy_check`; si cambia de proveedor, también `provider_selection` y se avisa al usuario antes).
- El checkpoint de `assets` resume: planos aceptados, recortados, regenerados (con el número de intento) y escalados.

## Errores comunes

- Revisar solo el primer fotograma o la miniatura del clip.
- Confiar en un puntaje de `video_understand` sin mirar los fotogramas.
- Regenerar cinco veces el mismo prompt.
- No guardar el registro y repetir el mismo error en el capítulo siguiente.
