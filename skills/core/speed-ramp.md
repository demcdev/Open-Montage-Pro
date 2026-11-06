# Speed Ramp — Core Skill

Cambiar la velocidad de un clip de forma gradual dentro del mismo plano con `speed_ramp`: entra rápido, frena en el momento clave y vuelve a acelerar. `cut.speed` solo da una velocidad fija para todo el corte.

## Cuándo usarla

Para acentuar un golpe de acción, un impacto o una revelación, una o dos veces por pieza. Si se repite, deja de ser un acento. No la uses en planos con personas hablando: el movimiento de los labios deja de coincidir.

## Uso

```json
{
  "input_path": "assets/video/mina.mp4",
  "keyframes": [
    {"time": 0, "speed": 2.5},
    {"time": 2, "speed": 0.3},
    {"time": 3, "speed": 0.3},
    {"time": 4.5, "speed": 2.5}
  ],
  "smoothing": "blend",
  "target_duration": 6.0
}
```

- `time` es un segundo del clip original, y `speed` la velocidad en ese punto. Entre dos puntos cambia en línea recta.
- `target_duration` escala toda la curva para que el clip dure eso, conservando su forma. Sirve para que el golpe caiga en un pulso de `beat_grid`.

Escribe `<clip>_ramp.mp4` y un `.ramp.json`. El clip resultante sustituye al original en el corte, con `cut.speed` en 1. `keyframe_output_times` dice en qué segundo del clip nuevo cae cada punto.

## Suavizado

| `smoothing` | Qué hace | Cuándo |
|---|---|---|
| `none` | Repite fotogramas | Clips con muchos fps, o un efecto entrecortado buscado |
| `blend` | Funde fotogramas vecinos | Por defecto: rápido, con algo de estela en lo lento |
| `motion` | Inventa fotogramas por movimiento | Cámara lenta suave en planos simples. Mucho más lento, y deforma la acción rápida |

Mira `real_frames_ratio`. A 0,3, solo 3 de cada 10 fotogramas de la parte más lenta son reales. Por debajo de 0,5 revisa ese tramo con ojos.

## Límites

- El clip sale sin audio, porque el sonido no puede seguir una rampa. El impacto se pone en la mezcla, con un efecto.
- La cámara lenta no crea detalle. Con clips generados de pocos fps se nota antes.
- El color y los demás efectos se aplican después, sobre el clip ya procesado.
