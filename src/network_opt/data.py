"""Capa de datos: carga y valida la red (plantas -> centros de distribucion -> clientes).

El modelo de optimizacion SOLO consume un objeto NetworkData. Asi, el caso base
(JSON), un dataset publico (DataCo) o un escenario modificado por el LLM son
intercambiables: todos producen un NetworkData.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NetworkData:
    factories: dict[str, dict]            # nombre -> {capacity, region}
    depots: dict[str, dict]               # nombre -> {capacity, fixed_cost, region}
    customers: dict[str, dict]            # nombre -> {demand, region}
    arcs: dict[tuple[str, str], float]    # (origen, destino) -> costo unitario
    unmet_demand_penalty: float = 500.0   # costo por unidad de demanda no servida
    meta: dict = field(default_factory=dict)

    def copy(self) -> "NetworkData":
        """Copia profunda: cada escenario what-if trabaja sobre su propia copia."""
        return copy.deepcopy(self)

    def validate(self) -> None:
        """Falla rapido con un mensaje claro si los datos son inconsistentes.

        Importante para la fase LLM: un escenario mal generado debe detectarse
        aqui, antes de llegar a Gurobi.
        """
        names = [*self.factories, *self.depots, *self.customers]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"Nombres de nodo duplicados entre tipos: {sorted(dupes)}")

        for (i, j), cost in self.arcs.items():
            if i not in self.factories and i not in self.depots:
                raise ValueError(f"Arco ({i} -> {j}): el origen debe ser planta o CD")
            if j not in self.depots and j not in self.customers:
                raise ValueError(f"Arco ({i} -> {j}): el destino debe ser CD o cliente")
            if cost < 0:
                raise ValueError(f"Arco ({i} -> {j}): costo negativo ({cost})")

        for kind, nodes, key in (
            ("planta", self.factories, "capacity"),
            ("CD", self.depots, "capacity"),
            ("cliente", self.customers, "demand"),
        ):
            for name, attrs in nodes.items():
                if attrs.get(key, -1) < 0:
                    raise ValueError(f"{kind} {name}: '{key}' falta o es negativo")

        unreachable = [c for c in self.customers if not any(j == c for _, j in self.arcs)]
        if unreachable:
            raise ValueError(f"Clientes sin ningun arco de entrada: {unreachable}")


def load_network(path: str | Path) -> NetworkData:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    arcs = {(a["from"], a["to"]): float(a["cost"]) for a in raw["arcs"]}
    data = NetworkData(
        factories=raw["factories"],
        depots=raw["depots"],
        customers=raw["customers"],
        arcs=arcs,
        unmet_demand_penalty=float(raw["meta"].get("unmet_demand_penalty", 500)),
        meta=raw.get("meta", {}),
    )
    data.validate()
    return data
