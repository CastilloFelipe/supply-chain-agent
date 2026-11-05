"""Convierte los controles del modo manual en operaciones what-if.

Es una funcion pura (sin Streamlit) para poder testearla.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ManualInputs:
    factory_capacity_pct: dict[str, int] = field(default_factory=dict)  # 100 = sin cambio
    region_demand_pct: dict[str, int] = field(default_factory=dict)
    transport_cost_pct: int = 100
    fixed_cost_pct: int = 100
    closed_depots: list[str] = field(default_factory=list)
    max_open_depots: int | None = None


def build_operations(inp: ManualInputs) -> list[dict]:
    ops: list[dict] = []
    for f, pct in inp.factory_capacity_pct.items():
        if pct != 100:
            ops.append({"op": "scale_factory_capacity", "factory": f, "factor": pct / 100})
    for r, pct in inp.region_demand_pct.items():
        if pct != 100:
            ops.append({"op": "scale_demand", "factor": pct / 100, "region": r})
    if inp.transport_cost_pct != 100:
        ops.append({"op": "scale_arc_costs", "factor": inp.transport_cost_pct / 100,
                    "origin": None, "destination": None})
    if inp.fixed_cost_pct != 100:
        ops.append({"op": "scale_depot_fixed_cost", "factor": inp.fixed_cost_pct / 100, "depot": None})
    for d in inp.closed_depots:
        ops.append({"op": "close_depot", "depot": d})
    if inp.max_open_depots is not None:
        ops.append({"op": "set_max_open_depots", "n": inp.max_open_depots})
    return ops
