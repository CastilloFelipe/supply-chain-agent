---
name: what-if
description: Simula una pregunta de negocio sobre la red logística ("¿qué pasa si...?"). Traduce la pregunta a operaciones del modelo, resuelve con Gurobi y redacta el reporte ejecutivo, sin usar la API de Anthropic. Úsalo cuando el usuario haga una pregunta what-if sobre capacidades, demanda, costos, CDs o rutas.
---

# Simulación what-if sin API

Haces el trabajo de las dos capas LLM del proyecto (traductor y redactor). Gurobi
calcula todas las cifras. Nunca inventes ni recalcules números a mano.

## 1. Elegir la red

Por defecto `data/base_network.json` (Chile). Si el usuario nombra una instancia
OR-Library (cap41, cap71, cap101, cap131), usa `--datos data/orlib/<nombre>.json`.

## 2. Traducir la pregunta

```bash
python main.py --catalogo [--datos <red>]
```

Esto imprime las herramientas válidas con sus `enum`. Solo puedes usar esas
herramientas y esos valores. Sigue las mismas reglas que `SYSTEM_PROMPT` en
`src/whatif_agent/translator.py`:

- Una llamada por cambio. Los factores son multiplicativos ("a la mitad" = 0.5,
  "sube 20%" = 1.2).
- `"*"` significa "todos" en los campos que lo permiten.
- Si algo es ambiguo, elige la lectura más razonable y anótala en `assumptions`.
- Si algo no se puede expresar con las herramientas, no lo aproximes: explícalo
  en `unsupported`.

Escribe el escenario en `outputs/escenario_<tema>.json` (crea la carpeta con `mkdir -p outputs` si no existe):

```json
{
  "question": "<pregunta literal del usuario>",
  "interpretation": "<una frase>",
  "assumptions": [],
  "unsupported": "",
  "calls": [{"name": "close_depot", "input": {"depot": "CD La Serena"}}]
}
```

## 3. Resolver

```bash
python main.py --escenario outputs/escenario_<tema>.json [--datos <red>]
```

Si falla la validación, corrige el JSON según el mensaje y vuelve a correr.
El comando crea `outputs/<timestamp>/` con `escenario.json` (incluye la
comparación completa) y `cifras.md`.

## 4. Redactar el reporte

Lee `outputs/<timestamp>/escenario.json` y escribe `outputs/<timestamp>/narrativa.md`
siguiendo la estructura y las reglas de `SYSTEM_PROMPT` en
`src/whatif_agent/report.py`: Resumen, Qué cambia en la red, Riesgos y lectura
correcta de las cifras, Recomendaciones. No incluyas la tabla de cifras: se
agrega automáticamente.

```bash
python scripts/componer_reporte.py outputs/<timestamp>
```

## 5. Responder

Muestra al usuario el resumen y la ruta de `reporte.md`. Si hubo supuestos o
partes no modelables, dilo explícitamente.
