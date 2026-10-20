# Editing Craft — Creative Skill

El oficio del montaje: dónde cortar, cómo unir planos sin que se note y cómo construir ritmo, tensión y humor con el corte. Complementa `skills/creative/video-editing.md` (decisiones de corte y ritmo en general) y los `edit-director` de cada pipeline.

## Cuándo usarla

- En el stage `edit` de todo pipeline.
- Al unir clips generados por IA, donde el corte es lo que más delata (cortes bruscos sin motivo).
- Al planear cortes relámpago de humor desde el guion.

## 1. Prioridades al decidir un corte

De Walter Murch, en orden: **emoción**, historia, ritmo, dirección de la mirada, plano bidimensional (eje), espacio tridimensional. Un corte que sirve a la emoción se perdona aunque rompa la continuidad; al revés, no.

## 2. Tipos de corte y cuándo usarlos

| Corte | Qué es | Cuándo | Cómo se escribe |
|---|---|---|---|
| Corte seco | Cambio directo | Por defecto. Casi todo el video | `transition_in: cut` |
| Corte J | El **audio** del plano siguiente empieza antes que su imagen | Para anticipar: oímos la voz o el sonido del lugar antes de verlo. Une escenas con fluidez | En `edit_decisions.audio`, la pista del plano B empieza 0,3–1,5 s antes del corte |
| Corte L | El audio del plano anterior **sigue** sobre la imagen siguiente | Para ver la reacción mientras el otro termina de hablar; para dejar respirar una línea | La pista de A termina después del corte |
| Corte en movimiento | Cortar a mitad de una acción que continúa en el plano siguiente | Une planos de distinto tamaño sin salto; el ojo sigue el gesto | Cortar 2–3 cuadros después de iniciado el gesto |
| Corte por coincidencia | Forma, color, movimiento o sonido que se repite de un plano al otro | Saltos de lugar o de tiempo con sentido (la pupila que se vuelve un cráter, el reloj que se vuelve otro reloj) | `transition_in: cut`; anotar qué coincide en `metadata.match_notes` (es un corte seco: la coincidencia se construye en la imagen) |
| Corte de reacción | A la cara de quien escucha | Chistes, revelaciones, mentiras | Plano propio en la lista de planos |
| Smash cut | Corte abrupto de un momento a su contrario | Humor y sustos | Sin transición; el contraste de sonido hace el trabajo |
| Encadenado | Disolución entre planos | Paso de tiempo. Usar poco | `dissolve` |
| Fundido a negro | Bajar a negro y volver | Fin de capítulo o de bloque | `dip_black` |
| Barrido rápido | Movimiento borroso de cámara entre planos | Energía, comedia, salto a otro lugar | `whip_pan_left` / `whip_pan_right` |

> **Valores reales:** el vocabulario de Remotion está en `remotion-composer/src/lib/transitions.tsx`. `cut` y `none` son corte seco; `fade` y `crossfade` se convierten en `dissolve`; `fade_black` en `dip_black`. **Cualquier nombre desconocido (por ejemplo `hard_cut` o `match_cut`) se renderiza como disolución.** `video_compose` también trata solo `cut` y `none` como corte seco. Escribe `cut` para todo corte directo (incluidos J, L, en movimiento, por coincidencia y smash). En HyperFrames las transiciones se escriben en la composición y estos valores sirven de documentación.

Regla: **un vocabulario de transiciones pequeño por video** (corte seco + uno o dos especiales). Transiciones llamativas en cada corte son de amateur.

## 3. Unir clips de video generado

- **Cortar en el movimiento, no en el reposo:** los clips generados suelen arrancar y terminar quietos; recortar los primeros y últimos 6–12 cuadros y cortar ya en movimiento.
- **Dirección de movimiento coherente:** si un clip termina con movimiento hacia la derecha, el siguiente no empieza moviéndose hacia la izquierda.
- **Corte J de ambiente** entre dos clips de lugares distintos: el sonido del lugar nuevo entra antes y disimula el salto de imagen.
- **Corte por coincidencia** cuando dos clips comparten forma o color; se planea desde la lista de planos pidiendo al modelo el primer fotograma adecuado.
- **Evitar el salto de eje y el corte entre tamaños casi iguales** (ver `cinematography.md`).

## 4. Ritmo

- **Respiración:** alternar planos cortos y largos; no repetir la misma duración tres veces seguidas.
- **El plano dura lo que dura su información:** cuando el espectador ya entendió, se corta. La reacción fuerte se deja vivir un poco más.
- **Sin pausas muertas:** huecos de unos 0,4 s entre líneas de diálogo; las escenas se ajustan a la duración real de la voz.
- **Interrupciones de patrón** cada 20–45 s en ficción animada (cambio de plano, de ritmo, de sonido o un corte relámpago), según `guionista-core`.
- **Silencio como golpe:** quitar música 2–5 s antes de una revelación hace que pegue más. Declarar ese tramo en `edit_decisions.metadata.intentional_ranges` para que el QC técnico no lo marque.

## 5. Humor con el corte

- **Cortes relámpago:** un inserto de 0,5–1,5 s a otra escena o a un recuerdo que contradice lo que se acaba de decir ("Nunca he perdido un caso" → corte de 1 s al abogado que se encoge de hombros → vuelta). Visualmente distinto (desaturado, otro encuadre) para que se lea como inserto.
- **Timing del chiste:** línea → corte a la reacción → pausa breve → siguiente línea. El chiste se mata cortando antes de la reacción o dejándola demasiado larga.
- **Regla de tres en imagen:** dos planos que establecen un patrón, el tercero lo rompe.
- **El sonido remata:** un efecto seco o el corte del ambiente en el momento justo vale más que un efecto visual.

## 6. Estructura de tráiler y avance

Para avances de capítulo y tráileres: arranque con una imagen o línea fuerte, presentación del mundo, escalada con planos cada vez más cortos y música en subida, silencio o corte a negro, golpe final (la mejor línea o imagen), título. Nunca revelar el cliffhanger del capítulo.

## Lista de control del edit-director

- [ ] Cada corte tiene un motivo (emoción, información, ritmo).
- [ ] No hay cortes entre planos casi iguales ni saltos de eje sin anotar.
- [ ] Hay al menos un corte J o L en cada escena de diálogo.
- [ ] Los clips generados están recortados para cortar en movimiento.
- [ ] Las transiciones especiales se cuentan con los dedos de una mano.
- [ ] Los silencios planeados están declarados en `intentional_ranges`.
- [ ] Los chistes tienen su plano de reacción.

## Integración

- **edit-director:** aplica estas reglas al construir `edit_decisions` (`cuts`, `transitions`, `audio`).
- **shot-list-storyboard:** los cortes relámpago y por coincidencia se planean desde la lista de planos, no se improvisan en el montaje.
- **audio-post-cinema:** los cortes J y L y los silencios se coordinan con las capas de sonido.
- **technical-qc-gate:** verifica que las uniones no dejen negros ni silencios no planeados.
