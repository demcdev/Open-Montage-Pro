# Shot List & Storyboard — Meta Skill

Antes de animar o generar video, cada escena se convierte en una **lista de planos** con intención, y cada plano en un **fotograma clave**. El usuario aprueba imágenes fijas baratas, no video caro. Formaliza el flujo que ya rige en este canal:

> **guion aprobado → prueba de UN fotograma → OK → 30 s completos (animación + voz + audio) → OK → resto de la producción.**

Nunca se salta un paso. Si el usuario interrumpe un render, es señal de que faltó mostrarle el fotograma antes.

## Cuándo usarla

- En el stage `scene_plan` de todo pipeline que genere o anime imagen (cinematic, animation, character-animation, explainer, hybrid, avatar).
- Para cada **parte** de un capítulo largo, no solo para el capítulo completo.
- No hace falta en pipelines que solo recortan metraje existente (clip-factory, podcast-repurpose), salvo los insertos nuevos.

## Paso 1 — Lista de planos

Una fila por plano. Se guarda en `scene_plan.scenes[]` (un plano = una entrada; las escenas largas se dividen) con los campos existentes:

| Campo de `scene_plan` | Qué va | Ejemplo |
|---|---|---|
| `id` | `s03_p02` (escena 3, plano 2) | |
| `start_seconds` / `end_seconds` | Tiempo **calculado** desde la duración real de la voz, no a ojo | 41.2 – 44.8 |
| `description` | Qué se ve, en una frase | Michael escucha la mentira de Walter |
| `framing` | Quién está en cuadro y dónde (texto libre) | Michael en el tercio izquierdo; Walter fuera de cuadro a la derecha |
| `movement` | Movimiento en palabras (texto libre) | Acercamiento lento, 5 % |
| `shot_language.shot_size` | `extreme_wide`, `wide`, `medium_wide`, `medium`, `medium_close`, `close_up`, `extreme_close_up`, `over_shoulder`, `insert`, `establishing` | `medium_close` |
| `shot_language.camera_movement` | `static`, `dolly_in`, `pan_left`, `whip_pan`, `rack_focus`… (enum del esquema) | `dolly_in` |
| `shot_language.lens_mm` | 14, 24, 35, 50, 85, 135 o 200 | 50 |
| `shot_language.lighting_key` | `high_key`, `low_key`, `rim_lit`, `neon`, `silhouette`… | `rim_lit` |
| `shot_language.depth_of_field` / `color_temperature` | `shallow`/`medium`/`deep`; `cool`/`neutral`/`warm`/`mixed` | `shallow`, `warm` |
| `shot_intent` | Por qué existe el plano (una frase) | Que se vea la reacción de Michael a la mentira |
| `narrative_role` | Enum del esquema: `establish_context`, `introduce_subject`, `build_tension`, `deliver_payload`, `transition`, `emotional_beat`, `evidence`, `comparison`, `resolution`, `call_to_action` | `emotional_beat` |
| `character_actions[]` | `character_id` (de la biblia), `action_sequence`, `emotion`, `dialogue`, `target`, `notes` | `{"character_id": "michael_davis", "emotion": "incrédulo", "action_sequence": ["levanta una ceja"], "dialogue": "¿En serio?"}` |
| `transition_in` / `transition_out` | `cut` para corte directo; `dissolve` o `fade` para fundido (otro texto se renderiza como fundido) | `cut` |
| `overlay_notes` | Textos en pantalla (nunca subtítulos incrustados) | tarjeta "3" |
| `required_assets[]` | Personajes, locaciones, SFX y música que necesita | |
| `hero_moment` | `true` en los 3–5 planos que definen el video | |

El esquema no admite campos extra dentro de cada escena. Lo que no tiene campo propio (función del plano en el guion como "gancho", "chiste" o "cliffhanger", referencia al fotograma) va en `scene_plan.metadata`, por ejemplo `metadata.beat_tags: {"s03_p05": "chiste"}`.

Reglas de la lista:

1. **Quien habla se ve.** Cuando un personaje se presenta o dice una línea importante, está en cuadro (plano medio o más cerca). Si no está, `shot_intent` debe justificarlo (por ejemplo, voz en off sobre una reacción).
2. **Cada plano tiene una sola intención.** Si necesita dos frases para explicarse, son dos planos.
3. **Variación de tamaño:** no más de dos planos seguidos del mismo tamaño en la misma escena (ver `skills/creative/cinematography.md`).
4. **Cortes relámpago de humor:** se listan como planos propios de 0,5–1,5 s, marcados en `metadata.beat_tags` como `chiste` (ver `skills/creative/editing-craft.md`).
5. **Duración según la voz:** el plano dura lo que dura su línea más la reacción; sin pausas muertas (huecos entre líneas de unos 0,4 s).

## Paso 2 — Fotogramas clave

Un fotograma por plano, en este orden de costo:

| Tipo de producción | Cómo se hace el fotograma | Herramienta |
|---|---|---|
| Animación vectorial (HyperFrames / Remotion) | Render de **un solo frame** de la composición real en el tiempo del plano | `hyperframes_compose` o render de Remotion con `frame` fijo |
| Video generado por IA | Imagen generada desde la biblia; será el primer fotograma del image-to-video | `image_selector` (FLUX, Imagen, Seedream, etc.) |
| Metraje real o stock | Captura del clip candidato | `frame_sampler` |

El fotograma se genera **desde la biblia** (`skills/meta/production-bible.md`): mismos SVG maestros o mismas referencias. Un fotograma que no respeta la biblia no se presenta.

## Paso 3 — Validación en tres niveles

| Nivel | Qué se muestra | Qué aprueba el usuario | Costo |
|---|---|---|---|
| 1. Un fotograma | El plano más representativo de la parte (normalmente el gancho o el hero) | Estilo, paleta, personajes, encuadre | Segundos |
| 2. Tablero | Todos los fotogramas de la parte en orden, con la línea de diálogo debajo | Orden, cobertura, que quien habla se vea, variedad de planos | Minutos |
| 3. 30 s completos | Animática o render real de los primeros 30 s con voz, audio y música | Ritmo, sincronía de boca, mezcla | Un render corto |

El tablero puede ser una animática barata: fotogramas fijos con la voz temporal y los tiempos reales, unidos con FFmpeg. Sirve para ver el ritmo antes de animar.

Cada nivel termina en un checkpoint `awaiting_human` y se **termina el turno** (protocolo de `skills/meta/checkpoint-protocol.md`). Una aprobación vale solo para ese nivel.

## Paso 4 — Mostrarlo en Backlot

El tablero se ve en Backlot porque vive en el artefacto `scene_plan`. Guardar las rutas de los fotogramas en `scene_plan.metadata.keyframes` (`{"s03_p02": "renders/keyframes/s03_p02.png"}`) para poder abrirlos desde el tablero.

## Errores comunes

- Mostrar el primer fotograma con un estilo que no es el de la biblia aprobada.
- Saltar del fotograma al capítulo completo sin los 30 s.
- Calcular los tiempos de los planos sin la duración real de la voz y luego estirar las escenas con pausas.
- Planos sin `shot_intent`: suelen ser relleno.

## Integración

- **scene-director:** produce la lista de planos y los fotogramas; no avanza a `assets` sin la aprobación del tablero.
- **asset-director:** solo genera video de planos con fotograma aprobado.
- **cinematography** (`skills/creative/cinematography.md`): define cómo se cubre cada escena.
- **Costos:** en video generado, los planos `hero_moment` justifican el modelo más caro; el resto puede ir en un modelo de borrador. El proposal-director lo refleja en el estimado.
