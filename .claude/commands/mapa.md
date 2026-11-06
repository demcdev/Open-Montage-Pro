---
description: Genera el mapa visual de un cambio o del sistema (arquitectura, impacto y etapas del pipeline) y lo abre en el navegador.
argument-hint: [cambios | commit [ref] | rama [base] | sistema] [título opcional]
---

Genera el mapa con `scripts/change_map.py` desde la raíz del proyecto. Elige el comando según la primera palabra de la petición:

| Petición | Comando |
|---|---|
| vacía o `cambios` | `.venv/Scripts/python.exe scripts/change_map.py --open` |
| `commit` | `.venv/Scripts/python.exe scripts/change_map.py --commit HEAD --open` |
| `commit <ref>` o un hash | `.venv/Scripts/python.exe scripts/change_map.py --commit <ref> --open` |
| `rama` | `.venv/Scripts/python.exe scripts/change_map.py --base main --open` |
| `rama <base>` | `.venv/Scripts/python.exe scripts/change_map.py --base <base> --open` |
| `sistema` | `.venv/Scripts/python.exe scripts/change_map.py --system --open` |

- El texto que sobre es el título: añádelo con `--title "<texto>"`. Si no hay texto, no pases `--title`.
- Sin argumentos o con `cambios`, corre antes `git status --short`. Si no hay cambios, no generes el mapa: dilo y sugiere `/mapa commit` o `/mapa sistema`.
- El script imprime la ruta del HTML. Responde con esa ruta como enlace y una línea con lo que cubre el mapa.
- El mapa solo lleva datos automáticos. No añadas decisiones, riesgos ni quiz, y no hagas commit.
- Si el comando falla, muestra el error tal cual.

Petición: $ARGUMENTS
