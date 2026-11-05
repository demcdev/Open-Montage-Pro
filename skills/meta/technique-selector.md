# Technique Selector — Meta Skill

Convierte un objetivo en una combinación corta de técnicas, cada una con motivo, herramienta y alternativa. Evita que un video use lo que la herramienta hace fácil en lugar de lo que la historia necesita. El menú está en `skills/creative/technique-catalog.md`.

## Cuándo usarla

En la etapa `proposal` o `idea` de los pipelines narrativos: ae, anim, avatar, char, cine, doc y hyb. Va después de elegir el concepto y **antes** de fijar `composition_mode` y `render_runtime`:

```
concepto → técnicas (este skill) → modo de composición → motor (animation-runtime-selector)
```

Primero la técnica, luego el motor. Si el motor se elige antes, la técnica queda limitada por él sin que nadie lo decida.

## Proceso

### 1. Reúne la entrada

- `brief_creativo`: objetivo emocional, qué está en juego, formato y duración.
- `delivery_promise` y `taste_profile`, si ya existen. `motion_required: true` descarta las técnicas que sustituyen movimiento por imagen fija.
- `VideoAnalysisBrief`, si hay video de referencia. Una técnica de la referencia entra por lo que aporta aquí, no por estar allí.

### 2. Mide la máquina

Nunca asumas qué está disponible. Consulta `registry.support_envelope()` y `video_compose.get_info()["render_engines"]`, y marca como no disponible toda herramienta:

- con estado distinto de `available`, o
- con `runtime` igual a `local_gpu` si la máquina no tiene gráfica dedicada.

Si la herramienta de una técnica no está disponible, usa el valor de la columna **Sin GPU** del catálogo o elige otra técnica. Si el arreglo es una clave o una instalación simple, ofrécelo con el protocolo de `AGENT_GUIDE.md`; no instales nada sin avisar.

### 3. Clasifica el objetivo

Parte de la receta. Es un punto de arranque, no una plantilla: quita lo que no sirva y añade lo que el brief pida.

| `goal` | Pieza típica | Receta de partida |
|---|---|---|
| `explainer` | Explicar una idea o sistema | `src_motion_graphics`, `src_data_viz`, `mot_kinetic_type`, `cut_hard`, `cam_push`, `snd_voiceover`, `snd_ducking` |
| `documentary` | Contar hechos reales con pruebas | `src_archive`, `src_stock`, `cut_j`, `cam_ken_burns`, `fin_grade`, `snd_voiceover`, `snd_layers` |
| `product_ad` | Vender un producto | `src_ai_video`, `cam_orbit`, `mot_stat_reveal`, `cut_whip`, `fin_film_look`, `snd_sfx_accent` |
| `short_vertical` | Short, Reel o TikTok | `src_stock`, `mot_kinetic_type`, `cut_jump`, `cam_crash`, `snd_voiceover`, `snd_sfx_accent` |
| `tutorial` | Enseñar a hacer algo | `src_screen_capture`, `src_synthetic_ui`, `mot_annotation`, `cut_hard`, `snd_voiceover` |
| `fiction` | Historia con personajes | `src_character_rig`, `cam_coverage`, `cut_reaction`, `cut_l`, `fin_grade`, `snd_layers` |
| `music_video` | La música manda | `src_motion_graphics`, `cut_beat`, `mot_kinetic_type`, `fin_stylized`, `snd_music_bed` |
| `presenter` | Una persona o avatar habla a cámara | `src_avatar`, `mot_lower_third`, `cut_jump`, `snd_voice_cleanup`, `snd_ducking` |
| `other` | Nada de lo anterior encaja | Sin receta: elige desde el catálogo y explica por qué |

`snd_master` no se elige: es obligatorio en toda entrega con audio. Tampoco cuenta en el límite de abajo.

### 4. Adapta y recorta

Para cada técnica, responde en una frase: **¿qué siente o entiende el espectador gracias a ella que no entendería sin ella?** Si no hay respuesta, sale.

Límites:

- **Entre 3 y 8 técnicas.** Debe haber al menos una de origen, una de montaje y una de sonido.
- **Una sola técnica `primary`:** la que define la pieza. El resto es `supporting` (se repite y sostiene) o `accent` (aparece pocas veces y por eso pesa).
- **Las técnicas `accent` se cuentan con una mano** y cada una dice en qué momento va. Un acento en todas partes es ruido.
- **Parcial** obliga a decir qué parte sí se entrega. **Pendiente** no se promete.

### 5. Preséntalo y regístralo

1. Muestra el stack junto al plan de producción: técnica, para qué sirve y con qué se hace. En lenguaje de oficio, sin IDs.
2. Di qué descartaste y por qué, con al menos una alternativa real.
3. Registra en `decision_log` una decisión de categoría `technique_selection`, con las alternativas en `options_considered`.
4. Escribe `technique_stack` en el artefacto de la etapa. La aprobación de esta etapa lo aprueba.

### 6. Dónde vive

| Etapa | Artefacto | Campo |
|---|---|---|
| `proposal` (ae, anim, char, cine) | `proposal_packet` | `proposal_packet.production_plan.technique_stack` |
| `idea` (avatar, doc, hyb) | `brief` | `brief.metadata.technique_stack` |

La forma es la misma en ambos y está definida en `schemas/artifacts/proposal_packet.schema.json`:

```json
"technique_stack": {
  "goal": "explainer",
  "techniques": [
    {
      "technique_id": "src_motion_graphics",
      "role": "primary",
      "purpose": "La idea es abstracta y el gráfico la hace visible sin costo de generación",
      "execution": "Escenas de Remotion stat_card y text_card",
      "fallback": "Tarjetas fijas con movimiento de cámara si el render falla"
    },
    {
      "technique_id": "cut_hard",
      "role": "supporting",
      "purpose": "Mantiene el ritmo de un dato nuevo por plano",
      "execution": "Corte seco en edit_decisions"
    },
    {
      "technique_id": "cam_crash",
      "role": "accent",
      "purpose": "Golpe en la cifra que cambia la conclusión",
      "execution": "camera crash_zoom_in",
      "applies_to": "Escena de la revelación, una sola vez"
    },
    {
      "technique_id": "snd_voiceover",
      "role": "supporting",
      "purpose": "La voz guía el orden de lectura",
      "execution": "tts_selector"
    }
  ],
  "rejected": [
    {
      "technique_id": "src_ai_video",
      "reason": "Cuesta y no aporta: la pieza no necesita mundo real"
    }
  ],
  "decision_id": "d-004"
}
```

## Después de aprobado

- `scene-director` y `edit-director` trabajan con este stack. Cada técnica `primary` y `accent` debe aparecer en un plano o corte concreto.
- **Añadir o quitar una técnica después de aprobar** exige otra decisión `technique_selection`. Si cambia lo que el usuario aprobó, se le consulta.
- Si una herramienta falla en producción, se aplica `fallback`. Un cambio silencioso es un fallo de revisión.

## Nunca hagas esto

- ❌ Elegir la técnica porque la herramienta ya está abierta o porque es la que mejor se conoce.
- ❌ Copiar la lista de técnicas de una referencia sin decir qué aporta aquí.
- ❌ Proponer algo que la máquina no puede ejecutar sin decirlo.
- ❌ Inventar un `technique_id`: si falta, añádelo al catálogo.
- ❌ Presentar una técnica `Parcial` como completa.

## Integración

- **creative-intake:** su brief es la entrada.
- **taste-direction:** `motion_intensity` y `visual_variance` acotan cuántos acentos caben.
- **animation-runtime-selector:** recibe el stack y elige el motor.
- **budget-and-model-routing:** las técnicas `nube` entran en `cost_estimate`.
- **reviewer:** comprueba que el stack exista y que se haya respetado.
