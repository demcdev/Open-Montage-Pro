# Creative Intake y Brief creativo (Meta Skill)

Cubre las fases 0 y 1 del mapa (`skills/MAPA_POR_FASE.md`): entender qué quiere el usuario y fijar **qué historia se cuenta, para quién y por qué importa** antes de escribir una línea de guion. Es **obligatorio** en los pipelines narrativos (animated-explainer, animation, character-animation, cinematic, avatar-spokesperson, documentary-montage, hybrid). Idioma de trabajo con el usuario: **español**.

No arranques producción sobre un brief vago, y no escribas guion sin **brief creativo** aprobado (§5).

## 1. Preguntas (en conversación, no como encuesta)

1. **Propósito:** ¿para qué es el video? (educar, vender, inspirar, documentar, entretener)
2. **Audiencia:** ¿quién lo verá? (edad, conocimiento previo, contexto: «mi equipo» frente a «público de YouTube»)
3. **Plataforma:** ¿dónde vivirá? (YouTube, Shorts, redes, presentación, web)
4. **Tono:** ¿cómo se debe sentir? (serio, juguetón, cinematográfico, crudo, cálido, provocador)
5. **Referencias:** ¿algún video que admire o al que se quiera parecer?
6. **Resultado:** ¿qué debe **sentir** o **hacer** el espectador al terminar?
7. **Restricciones:** ¿presupuesto, plazo, contenido obligatorio?

## 2. Cómo preguntar

- No sueltes las siete a la vez. Empieza por propósito y audiencia y deja que la conversación fluya.
- Si el usuario ya respondió algo, no lo repitas. «Quiero un film de marca cinematográfico para Instagram» ya trae propósito, plataforma y tono: pregunta lo que falta.
- **Brief vago** («hazme un video sobre X»): reconoce el tema, haz la pregunta más importante que falte (casi siempre propósito o audiencia), luego la siguiente, y para cuando tengas suficiente para investigar. La investigación completa el detalle.
- **Brief detallado** (varios párrafos o un documento): resume en 1–2 frases lo que entendiste, señala los huecos («tengo claros audiencia y tono, ¿qué resultado esperas?») y confirma plataforma y restricciones.

## 3. Si la entrada es un video de referencia

1. Lee `skills/meta/video-reference-analyst.md` y sigue su protocolo en lugar de esta entrevista.
2. El `video_analysis_brief` responde casi todas las preguntas: tono, estructura, ritmo, señales de audiencia y estilo.
3. Quedan por preguntar: tema de **tu** versión (si cambia), duración, si lleva narración y presupuesto.
4. No preguntes «¿cómo se debe sentir?»: la referencia es la respuesta. Sácalo del análisis.

## 4. Salida de la fase 0: `intake_brief`

Notas informales (sin schema) que recibe la etapa de investigación o idea como contexto:

- Citas textuales del usuario donde su forma de decirlo revela intención.
- Respuesta a cada una de las siete preguntas, marcando **dicha** o **inferida**.
- Videos o imágenes de referencia mencionados.
- Restricciones que hay que respetar.

Existe para que la investigación no invente una intención que el usuario nunca expresó.

## 5. Salida de la fase 1: brief creativo (obligatorio)

El **brief creativo** junta en un solo bloque las decisiones de concepto que el guion necesita. Se arma para el concepto elegido y se aprueba **en la misma puerta** que la propuesta o la idea (no añade otra parada).

**Dónde vive** (sin tocar los schemas):

| Pipeline | Etapa | Campo |
|---|---|---|
| animated-explainer, animation, character-animation, cinematic | `proposal` | `proposal_packet.metadata.brief_creativo` |
| avatar-spokesperson, documentary-montage, hybrid | `idea` | `brief.metadata.brief_creativo` |

**Campos:**

| Campo | Qué responde | Regla |
|---|---|---|
| `logline` | La historia en una frase | Ficción: **personaje + deseo + obstáculo + lo que está en juego**. No ficción: **pregunta o sujeto + por qué importa + qué se descubre**. Si no cabe en una frase, el concepto no está listo |
| `tipo` | `ficcion`, `documental`, `explicativo`, `ensayo` u `otro` | Decide qué skill de guion se lee en la fase 2 |
| `audiencia` | Para quién es | Concreta («curiosos de 16+ sin formación científica»), nunca «todo el mundo» |
| `objetivo_emocional` | `{ "sentir": …, "hacer": … }` al terminar | Una emoción dominante, no una lista |
| `en_juego` | Qué se gana o se pierde | En ficción, lo que pierde el personaje si falla; en no ficción, lo que el espectador gana o arriesga al entenderlo |
| `conflicto` | Qué se opone | Personaje contra personaje, entorno o sí mismo; en no ficción, expectativa contra realidad |
| `transformacion` | Qué cambia del inicio al final | El personaje, la situación o lo que el espectador entiende. Si nada cambia, no hay historia |
| `tono` | Cómo se siente | Coherente con `taste_profile` si existe |
| `plataforma_formato` | Destino y relación de aspecto | YouTube 16:9, Shorts 9:16… |
| `duracion_objetivo_s` | Duración pedida | En segundos |
| `narrador` | `single_narrator`, `character_dialogue`, `narrator_plus_characters` o `sin_voz` | Es la `audio_architecture`; se fija aquí, no en el guion |
| `referencias` | Videos o imágenes de referencia | Con lo que se toma y lo que se cambia de cada una |
| `restricciones` | Presupuesto, plazo, contenido obligatorio | |
| `origen` | `{ campo: "dicho" \| "inferido" }` | Lo inferido se le muestra al usuario para que lo confirme |

**Ejemplo** («quiero un video para hablar sobre el universo»):

```json
"brief_creativo": {
  "logline": "Eres un turista que viaja de la Tierra al borde del universo observable y en cada parada descubre que lo que creía grande es diminuto.",
  "tipo": "explicativo",
  "audiencia": "público general curioso, 16+, sin formación científica",
  "objetivo_emocional": {"sentir": "asombro que termina en aprecio por la Tierra", "hacer": "comentar qué escala le voló la cabeza"},
  "en_juego": "la idea que el espectador tiene de su propio lugar en el cosmos",
  "conflicto": "expectativa (la Tierra es enorme) contra realidad (es un punto)",
  "transformacion": "de 'la Tierra es enorme' a 'la Tierra es un punto, y aun así es única'",
  "tono": "asombro con humor seco",
  "plataforma_formato": "YouTube 16:9",
  "duracion_objetivo_s": 600,
  "narrador": "single_narrator",
  "referencias": [],
  "restricciones": "sin video generado salvo 2–3 planos héroe",
  "origen": {"audiencia": "inferido", "duracion_objetivo_s": "dicho"}
}
```

**Al presentar la propuesta o la idea**, muestra al usuario como mínimo `logline`, `en_juego` y `transformacion` junto al concepto. Su aprobación de la puerta aprueba el brief.

## 6. Qué no hacer

- No presentes una encuesta numerada: es una conversación.
- No preguntes lo que el usuario ya dijo.
- No retrases la producción sin necesidad: si el brief está claro, avanza.
- No inventes respuestas: lo que el usuario no dijo va como **inferido** o **no especificado**.
- No asumas que quiere un explicativo: muchos quieren cine, animación o trabajo sobre material propio. Escucha las señales.
- No dejes `en_juego` ni `transformacion` en vacío «para resolverlo en el guion»: es justo lo que el guion necesita para empezar.

## 7. Comprobación antes de cerrar la fase 1

- [ ] ¿El `logline` cabe en una frase y sigue la fórmula de su tipo?
- [ ] ¿`en_juego`, `conflicto` y `transformacion` están escritos y son concretos?
- [ ] ¿Hay una sola emoción dominante en `objetivo_emocional`?
- [ ] ¿`narrador` está fijado?
- [ ] ¿Lo inferido está marcado y se le mostró al usuario?
- [ ] ¿El brief está en `metadata.brief_creativo` del artefacto de la etapa y se aprobó en su puerta?
