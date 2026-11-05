# Agente de Optimización de Red Logística

Simulador *what-if* que combina un LLM con optimización matemática (MILP en Gurobi).
El usuario hace preguntas de negocio en lenguaje natural:

> "¿Qué pasa con el costo de transporte si la planta de Santiago reduce su capacidad
> a la mitad y la demanda en el norte aumenta un 20%?"

y el sistema (1) traduce la pregunta a cambios sobre el modelo, (2) resuelve con
Gurobi y (3) entrega un reporte ejecutivo con el impacto logístico.

## Arquitectura

```
Pregunta (lenguaje natural)
        │
        ▼
 [LLM] traductor ──► operaciones JSON (lista blanca)   ── Inyección #1: scenario.py
        │         └► hook de restricciones (opcional)   ── Inyección #2: model.py
        ▼
 NetworkData (copia) ──► build_model() ──► Gurobi ──► SolveResult
        │                                                │
        └──────────── caso base vs escenario ◄───────────┘
                                │
                                ▼
                  [LLM] reporte ejecutivo
```

## Estructura

```
├── main.py                     # Demo: caso base + escenario de ejemplo
├── data/base_network.json      # Red de ejemplo: 2 plantas, 4 CDs, 10 clientes (Chile)
├── data/orlib/                 # Instancias benchmark OR-Library (cap41, cap71, cap101, cap131)
├── scripts/import_orlib.py     # Conversor de OR-Library al formato de la red
├── src/network_opt/
│   ├── data.py                 # NetworkData: carga y validación
│   ├── model.py                # MILP en gurobipy (variables, objetivo, restricciones)
│   └── scenario.py             # Operaciones what-if (lista blanca)
├── src/whatif_agent/
│   ├── tools.py                # Herramientas para Claude (enums desde los datos, strict)
│   ├── translator.py           # Pregunta en lenguaje natural -> operaciones JSON
│   └── report.py               # Comparación base vs escenario + reporte ejecutivo
├── tests/                      # pytest
└── docs/                       # Notas de diseño y formulación
```

## Validación contra la literatura

El modelo se valida con las instancias de *Capacitated Warehouse Location* de la
[OR-Library](http://people.brunel.ac.uk/~mastjjb/jeb/orlib/capinfo.html) (J.E. Beasley),
que tienen óptimos publicados. Los tests exigen reproducirlos:

| Instancia | Bodegas × clientes | Óptimo publicado | Este modelo |
|---|---|---:|---:|
| cap41  | 16 × 50 | 1,040,444.375 | 1,040,444.375 |
| cap71  | 16 × 50 |   932,615.750 |   932,615.750 |
| cap101 | 25 × 50 |   796,648.437 |   796,648.438 |
| cap131 | 50 × 50 |   793,439.562 | requiere licencia académica |

Correr una instancia benchmark:

```bash
python main.py --datos data/orlib/cap101.json --pregunta "¿Qué pasa si cerramos la bodega B005 y la demanda total sube 10%?"
```

Las instancias más grandes (`capa`, `capb`, `capc`: 100 × 1000) se convierten con
`scripts/import_orlib.py`.

## Formulación

min Σ c_ij·x_ij + Σ fix_d·y_d + P·Σ u_c

- Capacidad de planta: Σ_j x_fj ≤ cap_f
- Conservación de flujo en CD: Σ_i x_id = Σ_j x_dj
- Capacidad de CD (si opera): Σ_i x_id ≤ cap_d·y_d
- Demanda: Σ_i x_ic + u_c = dem_c

Reglas opcionales de escenario: máximo de CDs abiertos (Σ y_d ≤ N), CD obligado a
operar (y_d = 1) y ruta bloqueada (x_ij = 0).

### Qué puede preguntar el usuario

| Tipo de cambio | Ejemplo de pregunta |
|---|---|
| Capacidad de planta o CD | "¿Y si la planta de Santiago produce a la mitad?" |
| Demanda por región o cliente | "¿Y si la demanda del norte sube 20%?" |
| Costos de transporte | "¿Y si el diésel sube 15%?" |
| Costos fijos de CDs | "¿Y si los arriendos suben 10%?" |
| Cierre o apertura obligada de CDs | "¿Y si cerramos La Serena pero mantenemos Santiago?" |
| Consolidación | "¿Y si operamos máximo 2 CDs?" |
| Cortes de ruta | "¿Y si se corta la ruta a Arica?" |

`u_c` es la demanda no servida y tiene una penalización P. Gracias a ella, un escenario
severo no termina en "INFEASIBLE": el modelo entrega cuántas unidades faltan y en qué clientes.

## Uso

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                 # escenario de ejemplo, sin LLM
pytest                         # los tests usan un cliente falso: no gastan créditos
```

### Preguntas en lenguaje natural

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --pregunta "¿Qué pasa si cerramos el CD de La Serena y el diésel sube 15%?"
```

El traductor usa Claude con *tool use*. Cada operación es una herramienta con `strict: true`,
y los nombres de plantas, CDs, clientes y regiones van como `enum` sacados de los datos, así
que el modelo no puede inventar nodos que no existen. Si una llamada no pasa la validación,
el error vuelve a Claude para que la corrija. El resultado final es un JSON auditable con las
operaciones, la interpretación, los supuestos y lo que no se pudo expresar. Ese JSON se puede
volver a ejecutar sin llamar al LLM.

El paquete `gurobipy` de pip trae una licencia restringida (2000 variables y restricciones),
suficiente para el caso de ejemplo. Para redes grandes, instala tu licencia académica:
`grbgetkey <tu-key>` desde la red de tu universidad.
