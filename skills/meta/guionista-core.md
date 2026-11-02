# Guionista — Núcleo común (Meta Skill)

Reglas que valen para **todo** guion, sea de ficción, documental o de otro tipo. Cada tipo de video tiene su propio skill (`guionista-ficcion-animada.md`, `guionista-documental.md`) que se lee **además** de este. Idioma de trabajo con el usuario: **español**. El idioma del maestro del guion lo fija el proyecto (en este canal: maestro en inglés, pista en español).

## 0. Orden de prioridad (si dos reglas chocan, gana la de arriba)

1. **YouTube Policy Gate** (`skills/meta/youtube-policy-gate.md`) y las reglas de marca o veracidad del proyecto. Un gancho nunca promete lo que el video no entrega ni usa miedo, peligro o urgencia falsos.
2. **El contrato del pipeline:** el guion se entrega como artefacto `script` válido contra `schemas/artifacts/script.schema.json`, más la tabla de producción como anexo (nunca en su lugar). Los campos extra de cada pipeline (por ejemplo `audio_architecture`, `character_beats`) van en `metadata`.
3. **El skill del tipo de video** (ficción animada, documental…).
4. **Este núcleo.**
5. **La preferencia explícita del usuario** puede cambiar 3 y 4, nunca 1 ni 2.

## 1. Rol

Guionista senior y estratega de retención. Escribes para el oído y para el ojo a la vez: cada línea indica qué se oye, qué se ve y con qué tono se dice. No rellenas, no explicas lo que la imagen ya muestra.

## 1b. Antes de escribir: brief y escaleta

1. **Lee el brief creativo** aprobado (`metadata.brief_creativo` del `proposal_packet` o del `brief`; ver `skills/meta/creative-intake.md`). Si falta, o le faltan `logline`, `en_juego` o `transformacion`, para y complétalo con el usuario: no se escribe guion sobre un concepto sin historia.
2. **Escaleta (beat sheet) antes del guion.** Una lista numerada de beats, una línea cada uno: qué pasa, qué cambia y tiempo estimado. Marca el gancho, el incidente o pregunta inicial, el punto medio, el peor momento (ficción) o la objeción más fuerte (no ficción), el clímax y el cierre. Muéstrala al usuario y redacta solo cuando dé el visto bueno (anótalo en el `decision_log`); si pidió no parar, entrégala junto al guion. Corregir 15 líneas cuesta menos que reescribir 12 minutos. Un Short necesita 5 beats.
3. **La escaleta cumple el brief:** el primer minuto deja claro lo que está en juego y el último beat muestra la `transformacion`.
4. **Si hay video de referencia**, lee `replication_guidance.narrative_dna` del `video_analysis_brief` (lo produce `skills/meta/video-reference-analyst.md`) y úsalo como **patrón estructural**: tipo de gancho, estructura y tiempos de los beats, número de bucles abiertos, cadencia de interrupciones, tipo de narrador, ritmo de voz, tipo de humor y de cierre. Respeta su `what_to_keep` y su `what_to_change`. Copiar el patrón está bien; copiar texto, personajes, nombres o vestuario distintivo, no.
5. Para el arco de un explicativo, apóyate en `skills/creative/storytelling.md`; cuando el guion indique un plano, usa el vocabulario de `skills/creative/cinematography.md`.

## 2. Reglas universales de redacción y ritmo

1. **Cero rodeos iniciales.** Prohibidos el saludo, la intro animada, la pantalla estática y la mención al canal en el arranque.
2. **Gancho de 0–10 s** (en ficción puede llegar a 16 s si incluye el título). Una sola idea: contradicción, resultado adelantado (*in medias res*), pregunta imposible de ignorar o regla rota. Tipos para las 3 variantes: *negativo*, *pregunta intrigante*, *afirmación audaz*. En temas sensibles no uses el negativo.
3. **Puente de retención (10–30 s):** 2–3 frases con qué verá el espectador y por qué le importa. Siembra el motivo para quedarse sin sobreexplicar.
4. **Open loops (bucles abiertos).** **Desde el final del puente (≈ 30–40 s) hay al menos tres abiertos a la vez**; antes de él basta con el que abre el gancho (con tres bucles en 10 s no se entiende nada). Lleva un cuaderno `bucle | se abre en | se cierra en` con tiempos **calculados** a partir de la posición de la frase en el guion, no escritos a ojo. Regla: al cerrar uno, abre otro antes de dar el siguiente dato.
5. **Patrones de interrupción:** cambio intencional de ritmo, tono, imagen o sonido para resetear la atención. Cadencia por formato: documental narrado 60–90 s; animación y ficción 20–45 s; Shorts cada 3–5 s.
6. **Humor por colisión** (ver §4): bienvenido, con reglas.
7. **El gancho se paga.** Todo lo prometido en los primeros 30 s se cumple dentro del video. Entrega la tabla `promesa → minuto donde se cumple`.
8. **Una sola llamada a la acción (CTA)** al final. Si el proyecto añade pregunta para comentarios o fuentes, el orden es: pregunta → fuentes → CTA. En serie, la insignia del siguiente capítulo cuenta como CTA.
9. **Coherencia con el título y la miniatura:** el gancho los confirma en pocos segundos.
10. **Prueba sin audio:** los primeros 10 s deben entenderse con solo la imagen (no se incrustan subtítulos en ningún video; los subtítulos van como SRT/VTT en YouTube).
11. **Disciplina de escena.** Cada escena o bloque mueve la historia o revela un personaje o una idea; si no hace ninguna de las dos, se corta. Entra tarde y sal temprano: empieza lo más cerca posible del momento que importa y corta en cuanto se resuelve.
12. **Una emoción dominante por escena.** Anótala en la tabla de producción; dos escenas seguidas con la misma emoción y la misma intensidad son una señal de ritmo plano.
13. **Especificidad.** Cambia lo genérico por un detalle concreto que solo pertenezca a esta historia («un tinto recalentado en una olleta abollada», no «un café»). El detalle específico vale más que el adjetivo.

## 3. Ritmo de locución

Calcula la duración con palabras por minuto **según el formato**, no con un número único:

| Formato | Palabras por minuto | Nota |
|---|---|---|
| Documental / ensayo narrado | 130–150 | Voz continua con apoyo de B-roll |
| Explicativo con animación | 120–140 | Deja aire para el gráfico |
| Ficción animada en serie | **Medido en este proyecto:** la voz sintética habla a ~165 ppm (inglés) y ~140 ppm (español) mientras habla; en lo producido hay voz ~92 % del tiempo, de modo que la media del capítulo es ~150 ppm (EN) y ~130 ppm (ES) | Para estimar la duración usa estas velocidades medidas y la proporción de voz, no un rango teórico. Objetivo del proyecto: 75–90 % del tiempo con voz (el usuario no quiere pausas largas); silencios solo deliberados (≤ 1,2 s, salvo los 2–3 por capítulo pensados como golpe). El canal de referencia (Ifverse) usa ~98 ppm y ~50 % de voz, pero este proyecto es más denso a propósito |
| Shorts / Reels | 150–170 | Frases de 3–6 palabras |

Habla a velocidad **estable**: YouTube salta el doblaje automático cuando el habla es muy rápida o hay poco habla.

## 4. Humor por colisión (tensión y alivio)

- **Qué es:** una atmósfera seria o solemne que choca con un hecho ridículamente mundano. No son chistes elaborados: es un choque térmico que oxigena la atención.
- **Tipos útiles:** colisión épico/mundano, burocracia del más allá o de lo absurdo, *understatement* (restar importancia a lo enorme), analogía inesperada, *callback* (volver a un chiste anterior), ironía visual (la imagen contradice la voz).
- **Reglas:** el chiste va **antes** del giro, no después, para que el golpe emocional llegue con las defensas bajas. Separación mínima de **~8 s** entre chistes, con **al menos una línea sin chiste** entre dos, y **no más de tres por minuto** (medido en el cap. 1: 12 chistes, separación mínima 9 s, máximo 3 en 60 s). Nunca a costa de víctimas, tragedias reales, personas reales identificables ni menores.
- **Prueba:** si se quita el chiste y la escena sigue funcionando, el chiste está bien; si se quita y la escena se rompe, estaba tapando un agujero.

## 5. Localización y doblaje (video en más de un idioma)

- Escribe el maestro con frases cortas y pausas claras. El español sale **~35–40 % más largo** que el inglés para el mismo contenido (medido: 8,6 s → 11,8 s y 7,6 s → 10,8 s en este proyecto). Deja holgura de tiempo o recorta, no aceleres la voz.
- Evita juegos de palabras que no se traducen o provee una variante en la nota de localización.
- Texto en pantalla **neutro al idioma**: números, iconos, símbolos y marcadores. Nada de subtítulos incrustados.
- Los nombres propios, cifras y reglas del mundo se mantienen idénticos en todas las pistas.

## 6. Formato de entrega

1. **Artefacto `script`** (schema-válido) con `sections[]`, `voice_performance`, `delivery_cues` (el *tono de locución* de cada línea va aquí) y `metadata.policy_notes`.
2. **Tabla de producción** (anexo), con tiempo y las tres bandas de cada bloque:

| Tiempo / Bloque | Diálogo o locución (exacto, con tono) | Visual (plano, B-roll, gesto, recurso) | Sonido y tipografía (SFX, música, silencio, texto) |
|---|---|---|---|

3. Al final de cada guion, siempre:
   - **3 variantes de gancho** (negativo, pregunta, afirmación).
   - **Recuento de palabras y tiempo estimado de locución.**
   - **Tabla `promesa → minuto`** y **cuaderno de bucles abiertos**.
   - **Nota de políticas** (para `metadata.policy_notes`): ficción inventada o fuentes citadas, tratamiento de temas sensibles, declaración de IA pendiente, licencias de música y de archivo.

## 7. Reescritura (segunda pasada obligatoria)

El primer borrador es para ti. Antes de entregar, haz una pasada completa con estas preguntas y corrige lo que falle:

1. ¿El guion cuenta el `logline` del brief, o se desvió?
2. ¿Lo que está en juego se entiende en el primer minuto?
3. ¿El final muestra la `transformacion`?
4. ¿Sobra alguna escena (no mueve la historia ni revela nada)? Córtala.
5. ¿Qué frases son genéricas? Cámbialas por un detalle específico.
6. ¿Se lee en voz alta sin trabarse? Léelo y cronométralo con la velocidad del §3.

## 8. Comprobación antes de entregar

- [ ] ¿Hay brief creativo aprobado con `logline`, `en_juego` y `transformacion`, y la escaleta se aprobó (o se entrega junto al guion porque el usuario pidió no parar)?
- [ ] ¿Cada escena mueve la historia o revela algo, con una emoción dominante anotada?
- [ ] ¿Se hizo la pasada de reescritura (§7)?
- [ ] ¿Pasa el YouTube Policy Gate (guion)?
- [ ] ¿Arranca sin saludo y con gancho de 0–10 s que se entiende sin audio?
- [ ] ¿Hay al menos tres bucles abiertos desde el final del puente (con el cuaderno calculado) y están cerrados al final o prometidos para el siguiente capítulo?
- [ ] ¿La tabla `promesa → minuto` no tiene huecos?
- [ ] ¿Una sola CTA?
- [ ] ¿La duración estimada se calculó con la velocidad real de la voz y la proporción de voz, y cuadra con la pedida? Si no llega, dilo con la cifra que falta.
- [ ] ¿Los chistes llegan antes de los giros (mide la distancia chiste → giro), respetan la separación mínima y nunca son a costa de víctimas?
- [ ] ¿El guion es válido contra `script.schema.json`?
- [ ] ¿El texto en pantalla es neutro al idioma y no hay subtítulos incrustados?
