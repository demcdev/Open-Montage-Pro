# Production Bible — Meta Skill

La biblia de producción es el contrato visual y sonoro de un proyecto o serie: cómo son los personajes, qué llevan puesto, dónde ocurre todo, con qué luz, con qué paleta y con qué voces. Se escribe **antes** de generar o animar y la consultan todas las etapas. Resuelve el defecto más visible del video hecho con IA o por partes: el personaje, el decorado o la luz cambian entre planos.

> La biblia narrativa (premisa, reglas del mundo, temporada, arcos) sigue siendo trabajo de `guionista-ficcion-animada.md`. Esta skill agrega la parte de **producción**: identidad visual, referencias y continuidad. En una serie, las dos viven en el mismo archivo.

## Cuándo usarla

- Cualquier proyecto con **personajes recurrentes**, aunque sea un solo video.
- Toda **serie**: se escribe en el capítulo 1 y se **actualiza**, nunca se rehace, en los siguientes.
- Pipelines: `character-animation`, `animation`, `cinematic`, `hybrid`, `explainer` con personajes, `avatar-spokesperson`.
- No hace falta en `screen-demo`, `podcast-repurpose` o `clip-factory` sin personajes.

## Dónde vive

`projects/<id>/production_bible.md` (o la sección "Production" dentro de `series_bible_vN.md` si ya existe). Las imágenes de referencia van en `projects/<id>/assets/bible/`. La aprueba el usuario en el checkpoint de `proposal` o de `character_design`, y queda registrada en el `decision_log` (categoría `production_bible`).

## Estructura obligatoria

### 1. Personajes (una ficha por personaje)

| Campo | Contenido |
|---|---|
| `id` y nombre | `michael_davis` — Michael Davis |
| Ancla de identidad (texto) | Una frase **fija** que se pega igual en cada prompt o se usa como guía de dibujo. No se reescribe nunca: reescribirla abre la variación |
| Silueta y proporciones | Altura relativa a los demás (en cabezas), complexión, rasgo de silueta reconocible a contraluz |
| Rostro | Forma de cabeza, ojos, cejas, boca; qué expresión tiene en reposo |
| Paleta del personaje | 3–5 HEX: piel o relleno, pelo, ropa principal, acento. Debe contrastar con la paleta del decorado |
| Vestuario por estado | Un estado = un asset: `limpio`, `empapado`, `herido`. Los estados solo avanzan dentro de una escena (no vuelve a estar limpio sin una elipsis) |
| Utilería fija | Objetos que siempre lleva (gafas, maletín) y en qué mano o lado |
| Voz | Proveedor, voz exacta (`es-US-Chirp3-HD-Charon`), velocidad, y una frase de acondicionamiento fija si el proveedor la usa |
| Hoja de referencia | Ver §4 |

### 2. Locaciones (una ficha por lugar)

- Plano de planta simple: dónde está la puerta, la ventana, el escritorio. **Lado de pantalla fijo** de cada elemento (la ventana siempre a la izquierda de cuadro desde el ángulo principal).
- Paleta del lugar y su variante nocturna o dramática.
- Mapa de luz: ver §3.
- Imagen de referencia de cada lado que se vaya a ver.

### 3. Mapa de luz por escena

| Escena | Hora / fuente | Dirección de la luz clave | Temperatura | Relleno | Contraluz | Cambio dentro de la escena |
|---|---|---|---|---|---|---|
| s03 lavandería | Noche, fluorescente | Arriba, ligeramente desde cuadro izquierda | 4500 K verdosa | Alto (sombras suaves) | No | Titila cuando llega el fantasma |

Regla: dentro de una escena la luz clave **no cambia de lado** salvo que la historia lo pida y quede escrito aquí. En animación vectorial esto define hacia dónde caen las sombras y de qué lado va la luz de borde.

### 4. Hojas de referencia (para video generado)

Método de `seedance-2-5`, válido para cualquier modelo con referencias:

1. **Tres placas por personaje, el rostro en una sola:** cuerpo completo de frente sin rostro, cuerpo completo de espaldas, y primer plano en tres cuartos con el rostro en dos versiones (neutral y sonriente). El modelo copia la cara más nítida del set; si hay caras pequeñas y borrosas, copia el borrón.
2. **Regla de 10:** antes de aprobar una hoja, generar al personaje diez veces en poses y luces distintas. Debe seguir reconocible las diez.
3. **Locaciones en movimiento:** para fondos, generar un recorrido lento de cámara por el espacio vacío y sacar de ahí los ángulos, no una sola imagen frontal.

Cómo se inyectan según el modelo (leer la skill de capa 3 antes de usarlas):

| Modelo / herramienta | Mecanismo | Skill |
|---|---|---|
| Seedance 2.0 / 2.5 | Imágenes de referencia + bloques de lock (`IDENTITY`, `SCREEN DIRECTION`, `LENS LOCK`) | `seedance-2-0`, `seedance-2-5`, `skills/creative/prompting/seedance-prompting.md` |
| Kling oficial | Elements y referencias del modo Omni | `kling-official` |
| Gemini Omni | Etiquetas `<IMAGE_REF_N>` y `<FIRST_FRAME>` | `gemini-omni` |
| ComfyUI | IP-Adapter o LoRA del personaje | `comfyui` |
| Imagen (FLUX, Imagen, etc.) | Imagen de referencia + misma semilla para variantes | `flux-best-practices`, `skills/creative/image-gen-usage.md` |

Para animación vectorial (HyperFrames, Remotion), la "hoja de referencia" es el **SVG maestro** del personaje y su rig: todas las escenas importan el mismo archivo, nunca una copia redibujada.

### 5. Reglas de continuidad (locks del proyecto)

Lista corta de lo que nunca cambia, en positivo:

- Conteo de personajes en escena ("en la oficina están exactamente dos: Michael y Walter").
- Lado de pantalla de cada personaje en un diálogo (ver `skills/creative/cinematography.md`, regla de 180°).
- Objetos que no se mueven solos.
- Qué no lleva texto legible ni logos reales.

### 6. Kit del canal

Tipografías, colores de título, estilo de miniatura y de la insignia de capítulo, para que todos los capítulos se reconozcan como la misma serie.

## Chequeo de continuidad (en cada stage de assets y compose)

Para cada escena, comparar los fotogramas muestreados (`frame_sampler` o `visual_qa` operación `review`) contra la biblia:

- [ ] El personaje es reconocible y su paleta coincide.
- [ ] El vestuario está en el estado correcto para este punto de la historia.
- [ ] La luz cae del lado que dice el mapa de luz.
- [ ] Los personajes están del lado de pantalla correcto.
- [ ] La utilería fija está presente y en su lugar.
- [ ] No aparecen personajes, objetos o textos que no deberían.

Un fallo en video generado = regenerar el plano con la referencia corregida. Un fallo en animación = corregir el SVG o la escena, no "parchar" en la composición.

## Errores comunes

- Reescribir el ancla de identidad en cada prompt ("hombre joven de traje" y luego "abogado de traje gris"): cada versión es una persona distinta.
- Pedir variaciones de vestuario en el prompt en vez de tener un asset por estado.
- Dibujar de nuevo un personaje en una escena en vez de reutilizar el SVG maestro.
- Aprobar una hoja con una sola generación buena.
- Cambiar la paleta del capítulo 3 sin registrar la decisión en la biblia.

## Integración

- **idea / proposal-director:** decide qué entra en la biblia y la presenta para aprobación.
- **character-design-director** (`character-animation`): produce las fichas y el SVG maestro; esta skill define el formato y el chequeo.
- **scene-director:** cada escena de `scene_plan` referencia los `id` de personajes y locaciones de la biblia en `character_actions` y `required_assets`.
- **asset-director:** usa las referencias del §4 y corre el chequeo de continuidad.
- **shot-list-storyboard** (`skills/meta/shot-list-storyboard.md`): los fotogramas clave se dibujan o generan desde la biblia.
