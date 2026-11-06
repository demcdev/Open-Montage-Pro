# Cold Review — Meta Skill

Segunda opinión sobre el video terminado, de alguien que no lo hizo. `reviewer.md` es autorrevisión: el agente que hizo el video lo juzga, y conoce todo lo que intentó hacer. El revisor en frío solo ve lo que vería un espectador con el brief en la mano.

Es obligatoria en los pipelines narrativos: `animated-explainer`, `animation`, `avatar-spokesperson`, `character-animation`, `cinematic`, `documentary-montage` e `hybrid`. `export_bundle` rechaza la entrega sin ella.

## Cuándo corre

Al final de `compose`, sobre el máster definitivo:

render → `audio_master` → `technical_qc` → revisión en frío → `export_bundle`

Si el máster cambia después, la revisión queda anulada.

## Pasos

1. **Preparar.** `cold_review` con `operation: "prepare"`:

```json
{
  "operation": "prepare",
  "video_path": "renders/final.mp4",
  "brief": {"title": "…", "audience": "…", "promise": "…"},
  "scenes": [{"id": "s1", "start": 0, "end": 6.5}],
  "has_narration": true,
  "narration_report_path": "assets/audio/narracion.narration.json",
  "layout_report_path": "renders/final_raw.layout.json"
}
```

2. **Revisar.** Llama al agente `cold-viewer` y pásale **solo** la ruta de `packet.json`. No le cuentes qué se intentó, qué costó ni qué crees que falla. En otro entorno sin subagentes, usa una sesión nueva sin historial.
3. **Registrar.** `cold_review` con `operation: "record"`, las puntuaciones y hallazgos tal como vinieron, y `round`.
4. **Actuar** según el veredicto.

## Rúbrica

Cada criterio se puntúa de 1 a 5 con evidencia: un segundo o un fotograma concreto.

| Criterio | `id` | 1 | 3 | 5 |
|---|---|---|---|---|
| Gancho | `hook` | Nada da razón para quedarse | Se entiende de qué va | Abre una pregunta que obliga a seguir |
| Ritmo | `pacing` | Escenas casi iguales o sin avance | Avanza, con tramos planos | Cada escena cambia algo |
| Legibilidad | `legibility` | No se lee o no se entiende el foco | Se entiende con esfuerzo | Se entiende al instante |
| Continuidad | `continuity` | Saltos de estilo, personaje o tema | Consistente con detalles sueltos | Una sola pieza coherente |
| Audio | `audio` | Métricas malas o transcripción incoherente | Correcto | Métricas limpias y texto que acompaña la imagen |
| Promesa | `promise` | No cumple el brief | Lo cumple en parte | Cumple lo prometido y al público indicado |
| Voz | `voice` | `narration_qc` sin `pass` | `pass` con frases aceptadas | `pass` limpio |
| Orden visual | `layout` | Elementos encimados o fuera de cuadro | Avisos revisados | Composición limpia en todos los fotogramas |

Por debajo de 3, un criterio falla. `voice` es nulo si el video no tiene voz.

La regla "No-Text Rule" de `AGENT_GUIDE.md` manda sobre la rúbrica: una cifra sin rótulo no es un fallo si la voz la explica, y ninguna corrección puede añadir palabras en pantalla. Por eso `legibility` se juzga con la transcripción delante.

La herramienta limita `voice` y `layout` a 1 si falta el informe medido o está mal, aunque el revisor los puntúe alto. Lo medido manda, porque el revisor no oye ni ve el movimiento.

## Veredicto

| Veredicto | Cuándo | Qué hacer |
|---|---|---|
| `pass` | Ningún criterio falla | Seguir a `publish` |
| `revise` | Falla algo en la ronda 1 o 2 | Corregir lo señalado, renderizar, volver a medir y revisar en la ronda siguiente |
| `escalate` | Sigue fallando en la ronda 3 | Parar y mostrárselo al usuario. Decide el usuario |

A diferencia de `reviewer.md`, aquí nada pasa solo. Si el usuario acepta entregar con `escalate`, registra una decisión `cold_exception` y pasa `cold_exception` a `export_bundle` con `reason` y `decision_id`.

## Límites

- No ve el movimiento entre fotogramas ni oye el audio.
- No sustituye la revisión del usuario: es un filtro antes de que el video le llegue.
- Tres rondas son el máximo, para que el ciclo no se alargue sin fin.
