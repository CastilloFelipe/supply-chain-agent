---
name: evaluar-traductor
description: Corre el set de evaluación del traductor (evals/preguntas.json) traduciendo cada pregunta a ciegas y luego mide los aciertos. Úsalo cuando el usuario pida evaluar o medir la precisión del traductor.
---

# Evaluación a ciegas del traductor

**Regla principal: NO abras, leas ni busques en `evals/respuestas_esperadas.json`**
(ni en `evals/resultados/`) hasta el paso 3. Si las ves antes, la evaluación pierde
validez: dilo al usuario y no reportes el puntaje.

## 1. Preparar

```bash
python main.py --catalogo
```

Lee `evals/preguntas.json`. Crea `evals/predicciones/<YYYYMMDD-HHMM>/`.

## 2. Traducir cada pregunta

Para cada pregunta escribe `evals/predicciones/<corrida>/<id>.json` con el formato
de `--escenario` (ver `.claude/skills/what-if/SKILL.md`, paso 2), usando solo las
herramientas y valores del catálogo y las reglas del `SYSTEM_PROMPT` de
`src/whatif_agent/translator.py`. Traduce cada pregunta de forma independiente y
no corrijas traducciones después de ver resultados.

## 3. Medir

```bash
python evals/run_eval.py --predicciones evals/predicciones/<corrida>
```

Reporta el puntaje y, para cada fallo, la pregunta, lo que tradujiste y lo
esperado (ahora sí puedes leer `respuestas_esperadas.json`). Si un fallo muestra
que la respuesta esperada es discutible, dilo, pero no cambies el puntaje de esta
corrida.
