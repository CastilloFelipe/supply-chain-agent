"""Modelo MILP de diseno de red de suministro en gurobipy.

Conjuntos
    F: plantas, D: centros de distribucion (CD), C: clientes, A: arcos (i, j)

Parametros
    cap_f, cap_d : capacidad de planta / throughput de CD
    fix_d        : costo fijo de operar el CD d
    dem_c        : demanda del cliente c
    c_ij         : costo unitario de transporte en el arco (i, j)
    P            : penalizacion por unidad de demanda no servida

Variables
    x_ij >= 0  : flujo en el arco (i, j)
    y_d in {0,1}: 1 si el CD d opera
    u_c >= 0   : demanda no servida del cliente c (holgura)

Objetivo
    min  sum c_ij x_ij + sum fix_d y_d + P sum u_c

Restricciones
    (1) Capacidad de planta:    sum_j x_fj <= cap_f                 para f en F
    (2) Conservacion en CD:     sum_i x_id  = sum_j x_dj            para d en D
    (3) Capacidad de CD:        sum_i x_id <= cap_d * y_d           para d en D
    (4) Demanda:                sum_i x_ic + u_c = dem_c            para c en C

La holgura u_c es deliberada: en un simulador what-if, un escenario severo
(p.ej. capacidad a la mitad) no debe devolver "INFEASIBLE" sin explicacion,
sino "faltan N unidades en estos clientes", que es lo que el reporte ejecutivo
necesita contar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import gurobipy as gp
from gurobipy import GRB

from .data import NetworkData

TOL = 1e-6


@dataclass
class ModelVars:
    flow: gp.tupledict      # x[i, j]
    open_depot: gp.tupledict  # y[d]
    unmet: gp.tupledict     # u[c]


# Firma del PUNTO DE INYECCION #2 (ver build_model).
ConstraintHook = Callable[[gp.Model, ModelVars, NetworkData], None]


@dataclass
class SolveResult:
    status: str
    total_cost: float | None = None
    transport_cost: float | None = None
    fixed_cost: float | None = None
    unmet_penalty_cost: float | None = None
    flows: dict[tuple[str, str], float] = field(default_factory=dict)
    open_depots: list[str] = field(default_factory=list)
    unmet_demand: dict[str, float] = field(default_factory=dict)
    factory_utilization: dict[str, float] = field(default_factory=dict)
    depot_utilization: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Salida serializable: esto es lo que recibira el LLM para redactar el reporte."""
        d = self.__dict__.copy()
        d["flows"] = [{"from": i, "to": j, "qty": q} for (i, j), q in self.flows.items()]
        return d


def build_model(
    data: NetworkData,
    extra_constraints: ConstraintHook | None = None,
    env: gp.Env | None = None,
) -> tuple[gp.Model, ModelVars]:
    m = gp.Model("supply_network_design", env=env) if env else gp.Model("supply_network_design")

    F, D, C = list(data.factories), list(data.depots), list(data.customers)
    arcs, cost = gp.multidict(data.arcs)

    # --- Variables -------------------------------------------------------
    x = m.addVars(arcs, lb=0.0, name="flow")
    y = m.addVars(D, vtype=GRB.BINARY, name="open")
    u = m.addVars(C, lb=0.0, name="unmet")
    v = ModelVars(flow=x, open_depot=y, unmet=u)

    # --- Objetivo --------------------------------------------------------
    transport = x.prod(cost)
    fixed = gp.quicksum(data.depots[d]["fixed_cost"] * y[d] for d in D)
    penalty = data.unmet_demand_penalty * u.sum()
    m.setObjective(transport + fixed + penalty, GRB.MINIMIZE)

    # --- Restricciones ---------------------------------------------------
    m.addConstrs(
        (x.sum(f, "*") <= data.factories[f]["capacity"] for f in F), name="factory_cap"
    )
    m.addConstrs((x.sum("*", d) == x.sum(d, "*") for d in D), name="depot_balance")
    m.addConstrs(
        (x.sum("*", d) <= data.depots[d]["capacity"] * y[d] for d in D), name="depot_cap"
    )
    m.addConstrs(
        (x.sum("*", c) + u[c] == data.customers[c]["demand"] for c in C), name="demand"
    )

    # ====================================================================
    # PUNTO DE INYECCION #2 (restricciones) -- codigo generado por el LLM
    # ====================================================================
    # Para preguntas que NO son un cambio de parametros, p.ej.:
    #   "Que pasa si exigimos que el CD Temuco atienda todo el sur?"
    #   "Que pasa si a lo mas operamos 3 CDs?"
    # el LLM generara una funcion con la firma ConstraintHook:
    #
    #   def hook(m, v, data):
    #       m.addConstr(v.open_depot.sum() <= 3, name="max_3_cds")
    #
    # Reglas para la fase LLM: el hook solo recibe (m, v, data), se ejecuta
    # en un entorno restringido (sin imports, sin acceso a disco/red) y se
    # registra junto al reporte para que el escenario sea reproducible.
    if extra_constraints is not None:
        extra_constraints(m, v, data)

    m.update()
    return m, v


def solve(
    data: NetworkData,
    extra_constraints: ConstraintHook | None = None,
    verbose: bool = False,
    time_limit: float = 60.0,
) -> SolveResult:
    with gp.Env(params={"OutputFlag": int(verbose)}) as env:
        m, v = build_model(data, extra_constraints, env=env)
        m.Params.TimeLimit = time_limit
        m.optimize()
        try:
            return _extract(m, v, data)
        finally:
            m.dispose()


def _extract(m: gp.Model, v: ModelVars, data: NetworkData) -> SolveResult:
    status = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INFEASIBLE_OR_UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }.get(m.Status, f"STATUS_{m.Status}")

    if m.SolCount == 0:
        return SolveResult(status=status)

    flows = {a: x.X for a, x in v.flow.items() if x.X > TOL}
    transport = sum(data.arcs[a] * q for a, q in flows.items())
    open_depots = [d for d, y in v.open_depot.items() if y.X > 0.5]
    fixed = sum(data.depots[d]["fixed_cost"] for d in open_depots)
    unmet = {c: u.X for c, u in v.unmet.items() if u.X > TOL}

    def util(node: str, cap: float, outgoing: bool) -> float:
        q = sum(qty for (i, j), qty in flows.items() if (i if outgoing else j) == node)
        return q / cap if cap > 0 else 0.0

    return SolveResult(
        status=status,
        total_cost=m.ObjVal,
        transport_cost=transport,
        fixed_cost=fixed,
        unmet_penalty_cost=data.unmet_demand_penalty * sum(unmet.values()),
        flows=flows,
        open_depots=open_depots,
        unmet_demand=unmet,
        factory_utilization={
            f: util(f, a["capacity"], outgoing=True) for f, a in data.factories.items()
        },
        depot_utilization={
            d: util(d, a["capacity"], outgoing=False) for d, a in data.depots.items()
        },
    )
