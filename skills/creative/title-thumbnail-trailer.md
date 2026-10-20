# Title, Thumbnail & Trailer — Creative Skill

Empaque de cada capítulo: miniaturas (3 variantes para la prueba A/B de YouTube), título del video, títulos de serie dentro del video, créditos y avance del capítulo siguiente. En una serie la miniatura y el título deciden el clic; el avance decide si vuelven.

Todo pasa por `skills/meta/youtube-policy-gate.md`: título y miniatura **honestos** (lo que muestran ocurre en el video), sin copiar miniaturas ni títulos de otro canal, sin texto vulgar ni violencia gráfica.

## Cuándo usarla

| Momento | Qué se hace |
|---|---|
| `proposal` / `script` | Escribir el título y la idea de miniatura **junto con** el gancho: si no hay una miniatura clara, el concepto es débil |
| `scene` / `assets` | Marcar el fotograma o plano que alimenta la miniatura y producirlo con calidad de póster |
| `edit` | Título de serie, créditos y avance del próximo capítulo |
| `publish` | 3 miniaturas finales, título, descripción y capítulos; entrega con `export_bundle` |

## Miniaturas

### Las tres variantes

Cada capítulo lleva **3 miniaturas que prueban ideas distintas**, no tres colores de la misma:

| Variante | Idea | Ejemplo (serie de vida de un vigilante) |
|---|---|---|
| A — Rostro y emoción | Primer plano del protagonista con una emoción fuerte y legible | Walter con los ojos muy abiertos, linterna en mano |
| B — Situación | El conflicto o el objeto clave del capítulo, con contexto | La puerta del almacén entreabierta y una sombra |
| C — Curiosidad | Contraste o pregunta visual: algo que no cuadra | Un uniforme de vigilante colgado en una habitación de hospital |

- YouTube "Probar y comparar" (Test & Compare) acepta hasta 3 miniaturas y elige la que logra más tiempo de visualización. Se suben las tres desde el inicio.
- Después de la prueba, anotar la ganadora en `publish_log.metadata.thumbnail_test` para aprender qué tipo funciona en la serie.

### Reglas de diseño

1. **Se lee en el móvil:** a 168×94 px (tamaño en la lista de sugeridos) la idea se entiende. Probar reduciendo la imagen antes de aprobar.
2. **Un sujeto, un punto focal.** Máximo 3 elementos.
3. **Texto: 0 a 4 palabras**, que **no repitan el título**: lo completan. Tipografía gruesa, con contorno o caja (ver `skills/creative/typography.md`). En la versión en español, el texto en español.
4. **Contraste alto** de luminancia entre sujeto y fondo; probar en escala de grises.
5. **Esquina inferior derecha libre:** ahí va la duración del video.
6. **Coherencia de serie:** la misma familia tipográfica, la misma posición del logo o número de capítulo, la paleta de la biblia (`skills/meta/production-bible.md`). Que se reconozca la serie en la página del canal.
7. **Mismo estilo que el video.** Una miniatura fotorrealista para una animación vectorial es engañosa y viola la política.

### Especificaciones

- 1280×720 (16:9), JPG o PNG, menos de 2 MB. Para Shorts, la portada se elige de un fotograma del video.
- Nombre: `<serie>_<capítulo>_<idioma>_thumb_<A|B|C>.jpg`.

### Cómo se producen

- **Animación (HyperFrames):** componer la miniatura como una composición fija de 1280×720 con los mismos personajes y fondos, y extraer el fotograma (skill de capa 3 `hyperframes-cli` para el renderizado de un fotograma, o `frame_sampler` con `strategy: "timestamps"` sobre un render corto).
- **Video generado:** imagen fija de alta calidad del plano héroe con `image_selector` (misma referencia de personaje que el video), no una captura borrosa del clip.
- Revisar las tres contra la lista de la política antes de entregarlas al usuario.

## Título del video

- 40–60 caracteres; lo importante en las primeras palabras (se corta en el móvil).
- Promete una situación o una pregunta, no un resumen: "Cuidé un almacén vacío 20 años. Una noche alguien respondió".
- El número de capítulo va al final o en la miniatura, no al inicio.
- Escribir 5 opciones y elegir con el usuario; título y miniatura se piensan juntos (la miniatura muestra, el título cuenta).
- Versión en inglés adaptada, no traducida palabra por palabra.

## Títulos de serie, créditos y avance (dentro del video)

| Pieza | Duración | Reglas |
|---|---|---|
| Cartón de título de serie | 2–4 s | Después del gancho, nunca antes. Mismo diseño en todos los capítulos. Sonido propio corto (`skills/creative/audio-post-cinema.md`) |
| Rótulo de capítulo | 1,5–2,5 s | "Capítulo 3 — La llave" sobre imagen, no sobre negro |
| Créditos finales | 5–10 s | Voces (TTS: proveedor), música (licencia), herramientas de IA usadas si corresponde a la divulgación. Legibles; sin pasar a toda velocidad |
| Avance del próximo capítulo | 10–20 s | 3–5 planos del capítulo siguiente sin revelar la resolución; termina en una pregunta o un corte en seco (`skills/creative/editing-craft.md`). Solo si el siguiente capítulo ya está escrito |
| Pantalla final de YouTube | Últimos 5–20 s | Dejar espacio libre para las tarjetas de pantalla final (video siguiente y suscripción) |

- El avance es un minitráiler: estructura de 3 tiempos (situación → escalada → corte), música que sube y se corta, una línea de diálogo fuerte como remate.
- Los textos en pantalla se traducen en cada versión de idioma (`skills/core/delivery-specs.md`).

## Registro

- `proposal_packet.metadata.packaging`: título provisional y concepto de miniatura (objeto abierto en el esquema).
- `export_bundle`: `title`, `thumbnail_path` (la variante A; las otras dos se entregan junto al paquete) o `thumbnail_concept` si aún no hay imagen.
- `publish_log.entries[].metadata_used.title` queda con el título final.

## Errores comunes

- Miniatura que muestra algo que no ocurre en el video.
- Tres variantes iguales con distinto color de fondo.
- Texto de la miniatura que repite el título.
- Avance que cuenta el final del capítulo siguiente.
- Título de serie antes del gancho: se pierde a quien todavía no decidió quedarse.
