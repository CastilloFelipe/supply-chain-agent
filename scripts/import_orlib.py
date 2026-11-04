"""Convierte instancias de OR-Library (Capacitated Warehouse Location, J.E. Beasley)
al formato JSON de la red.

Fuente: http://people.brunel.ac.uk/~mastjjb/jeb/orlib/capinfo.html
Formato del archivo original:
    m n                         (bodegas, clientes)
    capacidad costo_fijo        (m lineas)
    demanda                     (por cada cliente j, seguido de...)
    c_1j ... c_mj               (costo de asignar TODA la demanda de j a la bodega i)

Mapeo a nuestro modelo de 3 niveles:
    - Una planta ficticia "Fuente" con capacidad = demanda total y costo 0 a cada CD
      (OR-Library no modela produccion, solo bodegas -> clientes).
    - Bodegas -> CDs (capacidad, costo fijo).
    - Costo unitario del arco CD -> cliente = c_ij / demanda_j.
    - Penalizacion por demanda no servida mayor que cualquier costo unitario, para
      que el caso base sea exactamente el problema original.

Uso:
    python scripts/import_orlib.py cap41.txt --optimo 1040444.375 -o data/orlib/cap41.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse(text: str) -> tuple[list[dict], list[dict]]:
    tokens = text.split()
    pos = 0

    def take() -> str:
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    m, n = int(take()), int(take())
    warehouses = []
    for _ in range(m):
        cap = take()
        # Algunas instancias (capa/capb/capc) traen la palabra "capacity" en vez de un numero.
        cap = None if not cap.replace(".", "").isdigit() else float(cap)
        warehouses.append({"capacity": cap, "fixed_cost": float(take())})
    customers = []
    for _ in range(n):
        demand = float(take())
        customers.append({"demand": demand, "costs": [float(take()) for _ in range(m)]})
    if pos != len(tokens):
        raise ValueError(f"Sobran {len(tokens) - pos} tokens: formato inesperado")
    return warehouses, customers


def to_network(name: str, warehouses: list[dict], customers: list[dict],
               capacity_override: float | None, optimum: float | None) -> dict:
    total_demand = sum(c["demand"] for c in customers)
    unit = {}
    for j, c in enumerate(customers):
        for i, cost in enumerate(c["costs"]):
            unit[(i, j)] = cost / c["demand"] if c["demand"] else 0.0
    penalty = round(10 * max(unit.values()) + 1, 2)

    wname = lambda i: f"B{i + 1:03d}"
    cname = lambda j: f"C{j + 1:04d}"
    depots = {}
    for i, w in enumerate(warehouses):
        cap = w["capacity"] if w["capacity"] is not None else capacity_override
        if cap is None:
            raise ValueError("La instancia no trae capacidades: use --capacidad")
        depots[wname(i)] = {"capacity": cap, "fixed_cost": w["fixed_cost"], "region": "general"}

    arcs = [{"from": "Fuente", "to": d, "cost": 0} for d in depots]
    arcs += [{"from": wname(i), "to": cname(j), "cost": round(u, 6)} for (i, j), u in unit.items()]
    return {
        "meta": {
            "name": f"OR-Library {name} (Beasley, Capacitated Warehouse Location)",
            "source": "http://people.brunel.ac.uk/~mastjjb/jeb/orlib/capinfo.html",
            "units": {"flow": "unidades", "cost": "$"},
            "unmet_demand_penalty": penalty,
            "known_optimum": optimum,
        },
        "factories": {"Fuente": {"capacity": total_demand, "region": "general"}},
        "depots": depots,
        "customers": {cname(j): {"demand": c["demand"], "region": "general"} for j, c in enumerate(customers)},
        "arcs": arcs,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo")
    p.add_argument("-o", "--salida", required=True)
    p.add_argument("--optimo", type=float, help="Valor optimo publicado (capopt.txt)")
    p.add_argument("--capacidad", type=float, help="Capacidad para instancias capa/capb/capc")
    a = p.parse_args()
    warehouses, customers = parse(Path(a.archivo).read_text())
    net = to_network(Path(a.archivo).stem, warehouses, customers, a.capacidad, a.optimo)
    Path(a.salida).write_text(json.dumps(net, indent=1), encoding="utf-8")
    print(f"{a.salida}: {len(net['depots'])} CDs, {len(net['customers'])} clientes, {len(net['arcs'])} arcos")


if __name__ == "__main__":
    main()
