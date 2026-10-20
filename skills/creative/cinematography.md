# Cinematography — Creative Skill

Dirección de fotografía aplicada: cómo **cubrir una escena** (qué planos, en qué orden, desde dónde), cómo poner a los personajes en el espacio y cómo iluminarlos. Sirve igual para prompts de video generado y para encuadrar animación 2D. `skills/creative/video-gen-prompting.md` da el vocabulario (lentes, movimientos, 5 aspectos por plano); esta skill da las **decisiones**.

## Cuándo usarla

- `scene-director` de cualquier pipeline con personajes o puesta en escena.
- Al escribir prompts de video generado (antes de la skill de prompting del modelo).
- Al revisar un tablero de fotogramas (`skills/meta/shot-list-storyboard.md`).

## 1. Cobertura de una escena con diálogo

Patrón base para dos personajes. Se puede recortar, pero cada plano que se quite debe quitarse a propósito.

| Orden | Plano (`shot_size`) | Función |
|---|---|---|
| 1 | `establishing` o `wide` | Dónde estamos y dónde está cada uno. Fija el eje |
| 2 | `medium` de dos (two-shot) | La relación entre ellos |
| 3 | `over_shoulder` A → B | B habla; vemos su cara, el hombro de A en primer plano |
| 4 | `over_shoulder` B → A | Contraplano: A responde |
| 5 | `medium_close` o `close_up` de A | Reacción o línea importante de A |
| 6 | `close_up` de B | Reacción o revelación de B |
| 7 | `insert` | El objeto que importa (un formulario, una firma, un reloj) |

Reglas:

1. **Quien habla se ve.** Una línea importante, una presentación ("Soy Michael Davis") o una revelación van con el personaje en cuadro, en `medium` o más cerca.
2. **La reacción vale tanto como la línea.** Un chiste suele funcionar mejor en la cara del que lo escucha.
3. **Acercarse con la tensión.** Los planos se cierran a medida que sube la emoción; el plano más cerrado se guarda para el momento más fuerte.
4. **Variar el tamaño:** no más de dos planos seguidos del mismo `shot_size` en una escena. Corte entre tamaños parecidos (dos `medium` casi iguales) = salto feo.
5. **Volver al general** después de una revelación o cuando alguien entra o sale, para reubicar al espectador.

## 2. Eje y dirección de pantalla

- **Regla de 180°:** en una conversación hay una línea imaginaria entre los dos personajes. La cámara se queda de un lado. Así A mira siempre hacia la derecha de cuadro y B hacia la izquierda, y los planos de uno y otro "se miran".
- **Cruzar el eje solo a propósito:** con un plano en movimiento que lo cruce a la vista, un plano neutral (de frente, sobre el eje) o un corte a otro lugar. Se anota en `shot_intent`.
- **Línea de mirada:** en el contraplano, la mirada apunta a donde está el otro personaje fuera de cuadro, a la misma altura.
- **Dirección de movimiento:** si un personaje sale por la derecha, entra por la izquierda en el plano siguiente. Un viaje largo va siempre en la misma dirección de pantalla.
- **Lados fijos** en la biblia (`skills/meta/production-bible.md` §5): quién va a qué lado en cada locación.

En video generado esto se escribe con locks explícitos (ver `seedance-2-5`: `FIRST FRAME AND SPATIAL BLOCKING`, `SCREEN DIRECTION`). En animación se respeta al ubicar los SVG.

## 3. Composición y puesta en escena

- **Tercios:** ojos en la línea del tercio superior; el personaje en un tercio, con aire hacia donde mira (espacio de mirada).
- **Profundidad:** primer plano, medio y fondo. Un objeto en primer plano desenfocado o más oscuro da escala y ayuda al ojo. Los textos y tarjetas no son capas de profundidad: van en `overlay_notes`.
- **Altura de cámara:** a la altura de los ojos es neutral; desde abajo da poder; desde arriba hace al personaje más pequeño o vulnerable. Usar el cambio de altura para marcar quién domina la escena.
- **Escala relativa:** las alturas de la biblia se respetan en todos los planos (un personaje no cambia de tamaño entre un plano y el siguiente).
- **Bloqueo:** decidir antes dónde está cada uno y cómo se mueve en la escena (entra, se sienta, se acerca a la ventana). El movimiento del actor puede reemplazar el movimiento de cámara.

## 4. Lente (`lens_mm`) y lo que comunica

| `lens_mm` | Sensación | Uso típico |
|---|---|---|
| 14–24 | Espacio grande, distorsión, inmersión | Establecimiento, lugares imponentes, comedia física cercana |
| 35 | Natural con contexto | Planos medios con ambiente, seguimiento |
| 50 | Neutral, como el ojo | Diálogo, `medium` |
| 85 | Íntimo, fondo suave | Primeros planos, emoción |
| 135–200 | Comprimido, observado desde lejos | Tensión, vigilancia, detalle a distancia |

Mantener un rango de lentes por escena; saltar de 14 a 200 sin motivo se siente como dos películas. En animación 2D el "lente" se traduce en cuánto se escala el fondo respecto al personaje y cuánta perspectiva tienen los decorados.

## 5. Luz (`lighting_key`, `color_temperature`)

- **Esquema de tres puntos:** luz clave (la principal, de un lado), relleno (suaviza la sombra del otro lado), contraluz o luz de borde (separa al personaje del fondo). En animación vectorial: el lado de las sombras, el tono de la sombra y la línea de borde de color.
- **Relación clave/relleno:** relleno alto (`high_key`) para comedia y tono ligero; relleno bajo (`low_key`) para misterio y tensión.
- **Luz motivada:** cada luz tiene una fuente creíble en la escena (ventana, lámpara, pantalla). Si la lámpara titila, la luz del personaje titila con ella.
- **Continuidad:** el lado de la luz clave y la temperatura salen del mapa de luz de la biblia y no cambian dentro de la escena salvo que el guion lo pida.
- **Color con intención:** cálido para refugio o nostalgia, frío para soledad o amenaza, mezcla cálido/frío para conflicto. Un cambio de temperatura marca un cambio de tono (por ejemplo, de colores vivos a oscuro cuando llega el fantasma).

## 6. Movimiento de cámara (`camera_movement`)

- **Un movimiento por plano, con motivo:** `dolly_in` para revelar o intensificar, `dolly_out` para aislar o terminar, `pan` para seguir, `whip_pan` para un corte cómico o de energía, `static` cuando la actuación hace el trabajo.
- **El movimiento empieza y termina** dentro del plano, o se corta en movimiento hacia otro plano que se mueve en la misma dirección (ver `editing-craft.md`).
- La librería de movimientos para Remotion está en `skills/creative/camera-motion-library.md` y `docs/MOTION_CATALOG.md`.

## 7. Traducción al prompt de video generado

Por plano, en este orden (el detalle de sintaxis está en la skill de cada modelo):

1. Sujeto con el ancla de identidad **literal** de la biblia.
2. Acción en orden temporal.
3. Lugar, hora y fuente de luz (del mapa de luz).
4. Encuadre: `shot_size`, posición en cuadro, profundidad.
5. Cámara: lente, altura, ángulo, foco, movimiento.
6. Locks de continuidad (lado de pantalla, conteo de personajes, lente fijo).

No usar adjetivos vacíos ("cinematográfico", "épico"): describir la luz, el lente y el movimiento que producen esa sensación (`skills/creative/cinematic.md`).

## Lista de control del scene-director

- [ ] Cada escena tiene un plano que fija el espacio.
- [ ] Quien dice una línea importante está en cuadro.
- [ ] Nadie cruza el eje sin que esté anotado.
- [ ] No hay más de dos planos seguidos del mismo tamaño.
- [ ] La luz clave cae del lado que dice la biblia.
- [ ] Cada plano tiene un `shot_intent` que no es "variedad".

## Integración

- **scene-director:** llena `shot_language` y `framing` con estas decisiones.
- **shot-list-storyboard:** los fotogramas muestran la cobertura para aprobarla antes de producir.
- **production-bible:** fuente de lados de pantalla, alturas y mapa de luz.
- **editing-craft:** decide cómo se unen estos planos.
