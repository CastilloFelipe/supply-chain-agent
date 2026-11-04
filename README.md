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
├── src/network_opt/
│   ├── data.py                 # NetworkData: carga y validación
│   ├── model.py                # MILP en gurobipy (variables, objetivo, restricciones)
│   └── scenario.py             # Operaciones what-if (futuras herramientas del LLM)
├── tests/                      # pytest
└── docs/                       # Notas de diseño y formulación
```

Fases siguientes: `src/agent/` (traductor LLM y redactor de reportes) y
`src/network_opt/loaders/` (dataset DataCo Smart Supply Chain).

## Formulación

min Σ c_ij·x_ij + Σ fix_d·y_d + P·Σ u_c

- Capacidad de planta: Σ_j x_fj ≤ cap_f
- Conservación de flujo en CD: Σ_i x_id = Σ_j x_dj
- Capacidad de CD (si opera): Σ_i x_id ≤ cap_d·y_d
- Demanda: Σ_i x_ic + u_c = dem_c

`u_c` es la demanda no servida y tiene una penalización P. Gracias a ella, un escenario
severo no termina en "INFEASIBLE": el modelo entrega cuántas unidades faltan y en qué clientes.

## Uso

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
pytest
```

El paquete `gurobipy` de pip trae una licencia restringida (2000 variables y restricciones),
suficiente para el caso de ejemplo. Para redes grandes, instala tu licencia académica:
`grbgetkey <tu-key>` desde la red de tu universidad.
