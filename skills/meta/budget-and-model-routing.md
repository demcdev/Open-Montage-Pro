# Budget & Model Routing — Meta Skill

Decide **qué modelo usar en cada plano** según su importancia (caro solo donde se nota, barato o local en el resto) y cómo controlar el gasto con `cost_tracker` y un tope. El dinero se gasta en los planos que el espectador recuerda, no repartido por igual.

No sustituye a los selectores (`video_selector`, `image_selector`, `tts_selector`), que eligen proveedor dentro de una capacidad. Esta skill decide **el nivel** de cada plano y el **tope**; los selectores hacen el resto.

## Cuándo usarla

| Momento | Qué se hace |
|---|---|
| `proposal-director` | Clasificar planos por nivel, estimar con `estimate_cost` real, llenar `proposal_packet.cost_estimate` y acordar el tope con el usuario |
| `asset-director` | Antes de cada llamada pagada: `estimate` → `reserve` → ejecutar → `reconcile`. Detenerse ante un aviso de presupuesto |
| Al regenerar (`skills/meta/ai-shot-qa.md`) | Cada intento cuenta; el tercer fallo se escala al usuario |

## Niveles de plano

| Nivel | Qué planos | Ruta de modelo | Ejemplos |
|---|---|---|---|
| **0 — Gratis/local** | Animación vectorial, cartones, diagramas, fondos fijos con movimiento de cámara | HyperFrames/Remotion, `piper_tts`, imágenes locales (`local_diffusion`, `comfyui_image`) si hay GPU | La mayor parte de una serie animada en vectores |
| **1 — Borrador** | Animática, previsualización, pruebas de prompt, planos de relleno muy cortos | El proveedor más barato disponible o local (`ltx_video_local`, `wan_video`, `cogvideo_video`, `hunyuan_video` con GPU); imágenes fijas animadas en vez de video | Aprobación del plano en `skills/meta/shot-list-storyboard.md` |
| **2 — Estándar** | Planos de narrativa normal, B-roll, transiciones | Proveedor de gama media que pase la QA en la muestra | La mayoría de planos generados |
| **3 — Héroe** | `scene_plan.scenes[].hero_moment = true`, apertura, revelaciones, el plano de la miniatura, primeros planos de rostro | El mejor modelo disponible para ese tipo de plano (`video_selector` con `operation: "rank"`) e imagen-a-video desde un fotograma aprobado | 2–5 planos por capítulo |

Reglas:

1. **Máximo ~20 % de los planos en nivel 3.** Si todo es héroe, nada lo es.
2. **Imagen fija antes de video:** el fotograma clave se aprueba en imagen (barato) y luego se anima. Nunca se itera un prompt directamente en video caro.
3. **Muestra antes de lote:** 1–2 planos de muestra del nivel 2 y 3 antes de generar el resto (regla "un fotograma → 30 s → producción").
4. **Mismo modelo por escena** cuando sea posible: mezclar modelos dentro de una escena obliga a empatar color (`skills/creative/film-look-finishing.md`) y se nota en los rostros.
5. **Cambiar de proveedor o de modelo es una decisión del usuario** (contrato de AGENT_GUIDE "Decision Communication"); se anuncia herramienta, proveedor, modelo y motivo antes de ejecutar.

## Estimar con números reales

Los precios cambian y dependen de la cuenta; no se escriben de memoria. Se piden a las herramientas:

- `video_selector.estimate_cost(inputs)` devuelve el costo del proveedor que el selector elegiría para esas entradas (operación, duración, resolución, `preferred_provider`, `allowed_providers`).
- `video_selector` con `operation: "rank"` y `target_operation` (`text_to_video`, `image_to_video`, `reference_to_video`, `video_edit`) devuelve el ranking de proveedores **sin generar**; sirve para elegir el modelo del nivel 3.
- `image_selector.estimate_cost(inputs)` y `tts_selector.estimate_cost(inputs)` hacen lo mismo para imagen y voz; cada herramienta de proveedor tiene su propio `estimate_cost`.
- `CostTracker.estimate_from_reference(...)` estima un video completo a partir de un `video_analysis_brief` cuando hay video de referencia.

Fórmula por nivel: `planos × segundos por plano × costo por segundo × (1 + tasa de regeneración)`. Tasa de regeneración inicial: 0,5 en nivel 3 (uno de cada dos se repite), 0,3 en nivel 2, 0 en niveles 0–1. Se ajusta con el registro real de `asset_manifest.metadata.shot_qa`.

## `proposal_packet.cost_estimate`

Campos del esquema (no se agregan otros; `additionalProperties: false`):

```json
{
  "total_estimated_usd": 6.80,
  "line_items": [
    {"tool": "video_selector", "operation": "image_to_video, tier 3 hero shots", "quantity": 4, "estimated_usd": 4.80, "notes": "5 s each, 0.5 regeneration rate included"},
    {"tool": "video_selector", "operation": "text_to_video, tier 2", "quantity": 6, "estimated_usd": 1.60},
    {"tool": "image_selector", "operation": "keyframes for approval", "quantity": 10, "estimated_usd": 0.40},
    {"tool": "piper_tts", "operation": "narration EN + ES", "quantity": 2, "estimated_usd": 0.0}
  ],
  "budget_cap_usd": 10.0,
  "budget_verdict": "within_budget",
  "savings_options": ["Tier-2 B-roll as animated stills: -1.20 USD", "Local LTX for the animatic instead of a paid draft"]
}
```

- `budget_verdict`: `within_budget`, `near_limit` (más del 80 % del tope), `over_budget` o `no_budget_set`.
- Si es `over_budget`, se presentan `savings_options` concretas y el usuario elige; no se recorta calidad en silencio.
- El nivel de cada plano se guarda en `proposal_packet.metadata.shot_tiers` (objeto abierto): `{"sc03": 3, "sc04": 2, ...}`.

## Control de gasto con `cost_tracker`

Configuración global en `config.yaml` → `budget`: `mode` (`observe`, `warn`, `cap`), `total_usd`, `reserve_pct` (reserva para reintentos, 0,10), `single_action_approval_usd` (0,50) y `require_approval_for_new_paid_tool`.

Ciclo por cada llamada pagada (`tools/cost_tracker.py`):

1. `entry_id = tracker.estimate(tool, operation, estimated_usd)`
2. `tracker.reserve(entry_id)`:
   - `ApprovalRequiredError` si la acción supera `single_action_approval_usd` o es el primer uso pagado de esa herramienta: **parar y pedir aprobación**; con el sí, `tracker.approve_tool(tool)` y volver a reservar.
   - `BudgetExceededError` en modo `cap` si no alcanza el presupuesto usable (`total − gastado − reservado − reserva`): parar y presentar opciones.
   - En modo `warn` reserva igual y marca `budget_warning` en la entrada: avisar al usuario en el siguiente mensaje.
3. Ejecutar la herramienta.
4. `tracker.reconcile(entry_id, actual_usd, success)` con el costo real (o `tracker.refund(entry_id)` si no se ejecutó).

El registro queda en `cost_log.json` (`schemas/artifacts/cost_log.schema.json`). En el checkpoint de cada stage se informa `cost_snapshot()`: gastado, reservado y restante.

Modo recomendado: `warn` mientras se exploran ideas; **`cap` en producción de lotes** (un error en un bucle de regeneración no puede vaciar la cuenta).

## Registro de decisiones

- Nivel de un plano que sube a 3 fuera del plan, cambio de modelo o de proveedor: `decision_log` categoría `provider_selection`.
- Recorte de calidad para entrar en presupuesto: `budget_tradeoff` (y `downgrade_approval` con la aprobación del usuario).

## Errores comunes

- Generar todo con el modelo más caro "para que se vea bien".
- Estimar con precios de memoria en vez de `estimate_cost`.
- Iterar prompts en video caro en lugar de en imagen fija.
- Ignorar `budget_warning` en modo `warn`.
- No reconciliar: el presupuesto restante queda mal y la siguiente reserva falla o pasa sin control.
