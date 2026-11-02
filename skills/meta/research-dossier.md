# Research Dossier — Meta Skill

## When to Use

At the **research stage of every project**, for any topic or niche (natural resources, programming, history, finance, anything). The dossier is the factual base of the script: everything the video says must be traceable to a source the agent actually opened. It replaces ad-hoc searching in every `research-director`.

Set by the user on 2026-11-01. Binding in all pipelines.

## Model and effort (binding)

The dossier is produced by the agent `research-dossier` (`.claude/agents/research-dossier.md`), pinned to **Opus with high effort**. Do not run it with a lighter model or lower effort "to save time". Launch it with the Agent tool: `subagent_type: "research-dossier"`, `model: "opus"`, `effort: "high"`. The user explicitly asked for this level of effort, so setting `effort` here is allowed.

## Step 1: Fill the variables, never leave them empty

The prompt below has variables. Fill them from what the project already says, **mark each one as `inferred` or `confirmed`**, and **ask the user for every variable that is missing or only inferred with low confidence**. Ask with selectable buttons (`AskUserQuestion`), one decision at a time, with a recommended option first. Never start the research with an empty or unconfirmed variable.

| Variable | Meaning | How to get it |
|---|---|---|
| `{{TEMA}}` | Specific subject of the dossier (e.g. "el origen del litio") | From the user's request; confirm the wording |
| `{{NICHO}}` | Channel niche and angle (e.g. "recursos naturales con ángulo latinoamericano") | From project memory or channel plan; confirm |
| `{{DURACION_MIN}}` | Target length of the video in minutes | Ask (suggest 15-20 for YouTube explainers) |
| `{{AUDIENCIA}}` | Who watches: region, level of prior knowledge, age range | Ask; offer 3 concrete options |
| `{{IDIOMA_MERCADO}}` | Recording language and dubbing targets | From channel plan (e.g. record in Spanish; auto-dub EN, PT, AR) |
| `{{CAPAS}}` | Three "layers" of the topic to cover | **Propose three layers adapted to the topic** (see below) and let the user confirm or edit with buttons |
| `{{CAPA_PRIORITARIA}}` | Layer that gets more depth, or none | Ask; default "none: equal effort" |
| `{{NIVEL_PROFUNDIDAD}}` | How exhaustive (default: very thorough) | Default "thorough"; ask only if the user mentions time or cost limits |

### How to propose the layers

The three layers are not fixed. Derive them from the topic, keeping the idea of "where does it come from, how does it work, what is its story":

- **Natural resource** (e.g. lithium): cosmic origin · geological formation and location · history and strategic value.
- **Technology or software** (e.g. a language, a framework, programming as a field): problem it solved and why it appeared · how it works internally · history, adoption and current state.
- **Historical event or place**: causes and context · how it unfolded · consequences and how it is told today.
- **Company, product or industry**: founding and context · how the business or product works · crises, competition and present.

Present the proposal as a short list, say which layer is the riskiest to source, and let the user confirm or rename before the agent starts.

## Step 2: The prompt (verbatim template)

Pass this text to the agent after replacing every variable. Do not shorten it and do not remove the honesty rules.

```
Investiga {{TEMA}} y entrégame un dossier de las mejores fuentes confiables, con los hechos clave que cada una respalda, para que yo escriba después el guion de un video de YouTube.

Contexto
Voy a producir un video de YouTube divulgativo (duración objetivo: {{DURACION_MIN}} minutos, audiencia: {{AUDIENCIA}}) para un canal de {{NICHO}}. Idioma de grabación y doblajes: {{IDIOMA_MERCADO}}. Este dossier es la base de datos del guion: todo lo que afirme el video debe poder rastrearse a una fuente. Por eso prefiero pocas fuentes sólidas y verificables antes que muchas dudosas.

Alcance: tres capas
Cubre las tres, porque el tema puede entenderse desde cualquiera de ellas:
{{CAPAS}}
Si {{CAPA_PRIORITARIA}} está definida, dale más profundidad a esa capa; si no, reparte el esfuerzo en partes iguales.

Qué buscar
Para cada capa, prioriza en este orden de confiabilidad:
- Nivel 1: artículos revisados por pares y revisiones científicas, y publicaciones de instituciones oficiales del campo (agencias, universidades, observatorios, organismos de estándares, documentación oficial de la tecnología).
- Nivel 2: libros de divulgación de editoriales académicas o de autores con trayectoria verificable, y medios especializados serios.
- Nivel 3: documentales, charlas y canales de YouTube de divulgación, solo para referencia de enfoque narrativo y nunca como respaldo de un dato.
Descarta blogs anónimos, contenido SEO sin autoría, foros y notas de prensa de empresas como fuente de datos técnicos o científicos (sí pueden servir para datos comerciales, marcados como tales).

Formato de output
Responde en español, en este orden:
1. Resumen ejecutivo (máx. 8 líneas): qué se sabe con certeza, qué está en debate y qué sorprendería a mi audiencia.
2. Fuentes por capa. Una tabla por capa con estas columnas: Fuente (título, autor/institución, año) | Nivel (1-3) | Qué hecho respalda | Enlace.
3. Hechos clave verificados (lista): cada hecho en una línea, con su fuente entre paréntesis. Incluye cifras y fechas solo si las leíste en la fuente.
4. Controversias y datos que se contradicen entre fuentes, con qué dice cada una.
5. Huecos: qué no pude confirmar o dónde las fuentes son débiles.

Reglas de honestidad
- Incluye solo fuentes que realmente encontraste y abriste en esta sesión. Nunca construyas ni completes un enlace de memoria.
- Si un dato no está en una fuente que hayas leído, márcalo como "no verificado" en lugar de rellenarlo.
- Parafrasea; si citas, que sea una frase corta con atribución. Esto protege el guion de problemas de derechos de autor.
- Si dos fuentes de nivel 1 discrepan, preséntalas ambas sin elegir una por tu cuenta.
```

## Step 3: Rules for running it

1. **Open every source.** A search snippet is not a source. If a page is blocked (403, anti-bot), try the integrated browser; if it stays blocked, list it under "Huecos" and do not cite it.
2. **No on-screen text implication.** The dossier is for the narration. When it suggests visuals, they must follow the No-Text Rule in `AGENT_GUIDE.md` (numbers, symbols, flags, icons only).
3. **Dates and numbers.** Write numbers with a thin space for thousands (56 000) in facts meant for the video, and note the unit and the year of each figure.
4. **Freshness.** Today's date comes from the session; for figures that change (prices, production, reserves) record the year of the data and say if a newer edition should exist.
5. **Health, legal or financial claims** need primary sources from the audience's country (see `skills/meta/youtube-policy-gate.md`).
6. **Credit limits.** If a search tool runs out of credits, say so, switch to the integrated web search and browser, and mention it in the dossier's method note.

## Step 4: Where the result goes

1. Save the dossier as `projects/<project-id>/artifacts/research_dossier.md` (full text, with the confirmed variables at the top and the date).
2. Map it into the `research_brief` artifact for the next stage: facts → `data_points`, sources → `sources`, controversies and gaps → `metadata.limitations`, angles that the dossier suggests → `angles_discovered`. The `research_brief` must validate against `schemas/artifacts/research_brief.schema.json`.
3. Show the user the executive summary and the gaps; the full text stays in the file.

## Step 5: Self-review before the checkpoint

- Every fact in section 3 has a source that appears in section 2.
- No link was built from memory; every URL was opened in this session.
- Contradictions between Level 1 sources are shown, not resolved.
- Every variable at the top is marked `confirmed` by the user.
- Gaps are listed honestly, including sources that were blocked.
