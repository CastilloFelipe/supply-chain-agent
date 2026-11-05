---
name: evaluar-traductor
description: Corre un set de evaluación del traductor (evals/<set>/preguntas.json) traduciendo cada pregunta a ciegas y luego mide los aciertos. Úsalo cuando el usuario pida evaluar o medir la precisión del traductor.
---

# Evaluación a ciegas del traductor

**Regla principal: NO abras, leas ni busques en ningún `evals/*/respuestas_esperadas.json`**
(ni en `evals/resultados/`) hasta el paso 3. Si las ves antes, la evaluación pierde
validez: dilo al usuario y no reportes el puntaje.

## 1. Preparar

Elige el set (por defecto el más reciente, p.ej. `v2`). Lee `evals/<set>/preguntas.json`
y crea `evals/predicciones/<set>-<YYYYMMDD-HHMM>/`. Algunas preguntas traen `datos`:
esa es la red sobre la que se traduce. Obtén el catálogo de cada red con:

```bash
python main.py --catalogo --datos <datos>   # sin --datos: red de Chile
```

## 2. Traducir cada pregunta

Para cada pregunta escribe `evals/predicciones/<corrida>/<id>.json` con el formato
de `--escenario` (ver `.claude/skills/what-if/SKILL.md`, paso 2), siguiendo las `reglas`, el contexto `red_y_solucion_base` y solo las
`herramientas` que imprime `--catalogo`. Traduce cada pregunta de forma independiente y
no corrijas traducciones después de ver resultados.

## 3. Medir

```bash
python evals/run_eval.py --set <set> --predicciones evals/predicciones/<corrida>
```

Reporta el puntaje y, para cada fallo, la pregunta, lo que tradujiste y lo
esperado (ahora sí puedes leer `evals/<set>/respuestas_esperadas.json`). Si un fallo muestra
que la respuesta esperada es discutible, dilo, pero no cambies el puntaje de esta
corrida.
