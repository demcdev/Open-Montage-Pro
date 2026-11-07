# Pre-Render Review — Meta Skill

Revisar el video mientras se hace, para corregir en caliente y no después de un render completo. Son los mismos ojos de `meta/cold-review.md`, pero antes. Es obligatoria en los pipelines narrativos, en estos momentos:

| Momento | Etapa | Qué revisa | Qué atrapa |
|---|---|---|---|
| `script` | `script`, antes de generar la voz | Guion, aperturas alternativas y mapa de retención | Gancho débil, tramos sin motivo para seguir, frases engañosas, guion demasiado largo |
| `plan` | `scene_plan`, antes de aprobarlo | Cada frase con su plano y su cifra | Voz y cifra que no coinciden, imagen que no acompaña la frase, anacronismos |
| `clips` | `assets`, al elegir stock | Hoja de contacto de cada clip | Objetos modernos, planos que no encajan, clips marcados como IA |
| `frames` | `compose`, antes del render | Fotogramas de cada escena | Composición, contraste, gráficos ilegibles |

## Pasos

1. **Preparar.** `cold_review` con `operation: "preview"`, `project_dir`, `stage` y `brief`.
2. **Revisar.** Llama al agente `cold-viewer` y pásale **solo** la ruta del `packet.json`. No le cuentes qué se intentó.
3. **Registrar.** `cold_review` con `operation: "record_preview"`, el mismo `stage`, el `verdict` y los `findings` tal como vinieron, y `pass_number`.
4. **Actuar** según el veredicto.

## Entrada de cada momento

**`script`:** el guion, al menos 3 aperturas distintas y el mapa de retención, con un momento por cada motivo para seguir viendo.

```json
{
  "stage": "script",
  "script_text": "El guion completo.",
  "hooks": ["Apertura con paradoja.", "Apertura con cifra.", "Apertura con pregunta."],
  "retention_map": [{"second": 0, "reason": "Abre la pregunta"}, {"second": 6, "reason": "Primer giro"}],
  "target_seconds": 30
}
```

La herramienta mide antes de opinar. Fuerza `fix` si hay menos de 3 aperturas, si una pasa de 5 s, si empieza con una fórmula genérica, si el guion se pasa más de un 15 % o si hay un tramo largo sin motivo para seguir. El tiempo se estima a 2,5 palabras por segundo.

Antes de generar la voz, muéstrale al usuario las aperturas y la elegida por el revisor. Guarda el resultado en `script.metadata.hook_options` y `script.metadata.retention_map`.

**`plan`:** una fila por frase del guion.

```json
{
  "stage": "plan",
  "lines": [{"scene_id": "s1", "narration": "En Indonesia, el volcán explota.", "visual": "Columna de ceniza", "on_screen": "1815"}]
}
```

**`clips`:** cada candidato con la frase que acompaña y las etiquetas de la fuente. Un clip marcado como IA obliga a `fix`, sea cual sea la opinión del revisor.

```json
{
  "stage": "clips",
  "clips": [{"id": "nieve", "path": "assets/video/nieve.mp4", "scene_id": "s4", "narration": "En Boston…", "tags": "snow, field"}]
}
```

**`frames`:** las escenas y el motor.

```json
{
  "stage": "frames",
  "engine": "remotion",
  "entry": "remotion/index.tsx",
  "composition_id": "MiVideo",
  "public_dir": "public",
  "scenes": [{"id": "s1", "start": 0, "end": 6.5}]
}
```

Con HyperFrames, pasa `engine: "hyperframes"` y `workspace_path`.

## Veredicto

| Veredicto | Qué hacer |
|---|---|
| `go` | Seguir |
| `fix` | Corregir solo lo señalado y repetir este momento con `pass_number: 2` |
| `escalate` | Tras dos repasos sigue en `fix`: mostrárselo al usuario y que decida |

No bloquea el render: avisa temprano. La puerta dura sigue siendo la revisión final. Registra los momentos en esa revisión pasando `project_dir` a `record`.

## Borrador

Para juzgar ritmo y movimiento, el usuario necesita verlo. En piezas importantes, renderiza un borrador con `skip_layout_audit: true`: en Remotion a mano, `bespoke.scale: 0.25`; en HyperFrames, `quality: "draft"`. El revisor no lo evalúa porque no ve movimiento.

## Límites

- No sustituye la revisión final, que juzga el máster con su audio y su compresión.
- En piezas largas, `frames` limita el muestreo a 40 fotogramas; `cues` añade segundos exactos.
- Puede marcar falsos problemas: por eso avisa y no bloquea.
