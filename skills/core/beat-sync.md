# Beat Sync — Core Skill

Cortar al pulso con `beat_grid`, que detecta el tempo, los pulsos y los compases de una pista y mueve los cortes hasta ellos. Funciona con FFmpeg y numpy, sin instalar nada ni pagar por ello.

## Cuándo usarla

Cuando la música manda en un tramo: montajes, secuencias sin voz, finales o videos cortos con energía. Bajo una narración, la frase manda: mueve al pulso solo los cortes que caen cerca de uno.

## Uso

Pasa la pista sola, nunca la mezcla final: la voz confunde al detector.

```json
{
  "audio_path": "assets/music/pista.mp3",
  "offset_seconds": 12.0,
  "duration_seconds": 40.0,
  "music_start_seconds": 3.0,
  "cut_times": [3.1, 7.4, 11.9],
  "tolerance_seconds": 0.25,
  "min_gap_seconds": 0.5
}
```

- `offset_seconds`: segundo de la pista donde empieza a sonar. Es el mismo que usa la mezcla.
- `duration_seconds`: cuánto suena. Pásalo siempre: se analiza solo ese tramo, y una pista puede fallar entera y pasar en una parte.
- `music_start_seconds`: segundo del video donde entra la música.
- `cut_times`: cortes en el tiempo del video.

Escribe `<audio>.beats.json`. `timeline` trae los pulsos en tiempo de video, y `snapped_cuts` dice dónde va cada corte y cuánto se movió.

## Cómo leer el resultado

| Campo | Qué hacer |
|---|---|
| `usable: false` | La música no tiene pulso claro. No fuerces la rejilla: corta por frases musicales. Se ve mucho en pistas ambientales |
| `downbeats_reliable: false` | No se distinguen los compases. Si pediste `snap_to: "downbeats"`, se usan pulsos, y `snap_target` lo indica |
| `snapped: false` en un corte | Quedó lejos de un pulso o se pegaba al corte anterior, así que no se movió |

Usa `downbeats` solo en los cortes importantes. Son cuatro veces menos que los pulsos.

## Después de ajustar

1. Pasa los tiempos de `snapped_cuts` a `edit_decisions` y recorta los clips en consecuencia, sin dejar huecos entre un corte y el siguiente.
2. Guarda el tempo en `edit_decisions.metadata.beat_timing`.
3. Mira un tramo con sonido. El oído es la comprobación final.

## Límites

- El tempo puede salir a la mitad o al doble. A 174 BPM dio 87 en la prueba. Si se nota, ajusta `min_bpm` y `max_bpm`.
- Supone compás de 4/4 y tempo casi constante.
- En pistas reales con compases poco marcados, `downbeats_reliable` suele salir falso.
- Se probó con pistas de clics de tempo conocido: acierta cada pulso con 6 ms de error. En música real solo se comprobó que el pulso sea regular, no contra una referencia.
- La música cinematográfica suele tener el pulso débil: el umbral de `usable` se fijó con 6 pistas y no con el oído.
