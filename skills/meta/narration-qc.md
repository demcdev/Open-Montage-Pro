# Narration QC — Meta Skill

Protege la narración de dos fallos: una voz de otro idioma leyendo el guion y frases que se salen del idioma a mitad de video. Corre en la etapa `assets`, antes de gastar en render.

## Por qué pasa

Las voces `Multilingual` detectan el idioma leyendo el texto. Con nombres propios o frases muy cortas pueden cambiar de idioma por un momento. En una prueba real con `it-IT-GiuseppeMultilingualNeural`, el guion decía "Londres. Tokio." y Whisper oyó "London" y "Tokyo". Cuatro voces nativas en español leyeron bien el mismo texto.

## Paso 1: elegir la voz

Una voz nativa del idioma del guion evita el problema de raíz.

Pasa siempre `language_code` a `tts_selector`. Si la voz está nombrada para otro idioma (`fr-FR-…`, `it-IT-…`) y no coincide, la herramienta se niega a generar. Para usarla de todos modos:

1. Pregunta al usuario, explicando el riesgo.
2. Registra una decisión `voice_language` en `decision_log`.
3. Pasa `allow_voice_language_mismatch: true`.

Las voces sin idioma en el nombre, como las de ElevenLabs, no se pueden comprobar. Con ElevenLabs, pasa `language_code` para fijar el idioma.

## Paso 2: la muestra

La muestra de voz debe incluir las frases de más riesgo: las de una o dos palabras, nombres extranjeros, marcas y cifras. El usuario la escucha antes de generar el resto.

## Paso 3: comprobar la narración

Corre `narration_qc` sobre cada pista de narración, antes de mezclar la música:

```json
{
  "audio_path": "projects/mi-video/assets/audio/narracion.mp3",
  "script_text": "El texto exacto que leyó la voz.",
  "language": "es"
}
```

Tarda algo más que la duración del audio en CPU. Escribe `<audio>.narration.json`.

Cada frase se revisa buscando tres señales:

| Señal | Significa |
|---|---|
| `wrong_words` | Whisper oyó otras palabras |
| `foreign_language` | El audio no suena al idioma del guion. Solo en clips de 1 s o más |
| `low_confidence` | Whisper dudó de lo que oyó |

Una palabra distinta al guion marca su frase por sí sola, y el informe la nombra en `wrong_words`. `foreign_language` y `low_confidence` son ruido normal por separado, así que marcan solo si coinciden.

## Paso 4: resolver lo marcado

| Veredicto | Qué hacer |
|---|---|
| `pass` | Seguir |
| `review` | Mostrar al usuario cada frase, con su segundo y lo que oyó Whisper |

Para cada frase marcada, el usuario escucha y decide:

- **Mal:** regenerar solo esa frase con la misma voz, reescribiéndola o alargándola si hace falta, y volver a correr `narration_qc`.
- **Bien:** volver a correr con la frase en `accepted_sentences`.

No aceptes frases sin que el usuario las haya escuchado. La revisión en frío rechaza una narración sin `pass`.

## Límites

- Whisper no mide el acento. Un cambio de acento que no altere las palabras puede pasar sin marca, por eso importa la muestra.
- Un `pass` no prueba que la voz suene bien.
- Las reglas se calibraron con 6 voces y un texto, sin escuchar el audio.
