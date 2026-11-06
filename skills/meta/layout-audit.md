# Layout Audit — Meta Skill

Revisa la composición **antes del render** midiendo cajas reales en el navegador. Atrapa lo que el muestreo de fotogramas deja pasar: gráficos o textos desbordados, encimados o tapados.

## Cuándo corre

Corre sola dentro de `video_compose` y `hyperframes_compose`, justo antes de renderizar. También se puede llamar directo mientras se ajusta una escena. El informe queda en `<render>.layout.json`, junto al máster.

`skip_layout_audit: true` es solo para borradores. Una entrega sin su `.layout.json` no pasa la revisión en frío.

## Qué detecta

| Regla | Qué significa | Remotion | HyperFrames |
|---|---|---|---|
| `text_off_canvas` | Texto que se sale del lienzo | Sí | Sí |
| `text_cut_off` | Texto recortado por su contenedor | Sí | Sí |
| `text_overlap` | Un texto encima de otro | Sí | Sí |
| `text_covered` | Texto tapado por un gráfico | Sí | Sí, si `check` lo reporta como `text_occluded` |
| `graphic_off_canvas` | Gráfico pequeño que se sale del lienzo | Sí | Sí, si `check` lo reporta como `panel_out_of_canvas` |

Remotion usa `remotion-composer/scripts/layout-probe.js`, que se suma al empaquetado sin tocar el código del proyecto. HyperFrames usa la sección `layout` de `hyperframes check`.

## Veredicto

| Severidad | Cuándo | Efecto |
|---|---|---|
| `block` | Un problema de texto que dura 1 s o más | El render no corre |
| `warn` | Algo más corto, normalmente un elemento que entra o sale, o cualquier `graphic_off_canvas` | El render sigue. Hay que abrir ese momento y decidir |

## Qué hacer con un hallazgo

1. Abrir el segundo señalado con `visual_qa` operación `review`.
2. Si es un error, corregir la composición y volver a correr.
3. Si es intencional, declararlo en el elemento y dejar el motivo en `decision_log`:

| Atributo | Para qué |
|---|---|
| `data-layout-allow-overlap` | Encimado buscado, como un título sobre otro en una transición |
| `data-layout-allow-overflow` | Elemento que sale del lienzo a propósito, como una nube que cruza la pantalla |
| `data-layout-ignore` | Excluir un elemento decorativo por completo |

Nunca añadir un atributo solo para que pase. La regla se relaja en el elemento concreto, no en toda la escena.

## Límites

- Solo mide lo que dibuja el motor. El texto incrustado en una imagen o un video generado no se puede medir; eso queda para la revisión en frío.
- Entre dos tarjetas o fondos sin texto no comprueba encimados.
- Si la auditoría no pudo correr, el render sigue, pero no queda `.layout.json` y la revisión en frío lo cuenta como fallo.
