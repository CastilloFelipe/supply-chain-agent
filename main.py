"""Punto de entrada: resuelve el caso base y un escenario what-if de ejemplo.

Uso:
    python main.py                 # caso base + escenario de ejemplo
    python main.py --verbose       # muestra el log de Gurobi
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from network_opt import SolveResult, load_network, solve  # noqa: E402
from network_opt.scenario import apply_operations  # noqa: E402

BASE_DATA = Path(__file__).parent / "data" / "base_network.json"

# ======================================================================
# FUTURO: esta lista la producira el LLM a partir de la pregunta:
#   "Que pasa con el costo de transporte si la fabrica de Santiago reduce
#    su capacidad a la mitad y la demanda en el norte aumenta un 20%?"
# ======================================================================
EXAMPLE_SCENARIO = [
    {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
    {"op": "scale_demand", "factor": 1.2, "region": "norte"},
]


def print_result(title: str, r: SolveResult) -> None:
    print(f"\n=== {title} ===")
    print(f"Estado: {r.status}")
    if r.total_cost is None:
        return
    print(f"Costo total:        {r.total_cost:>12,.0f}")
    print(f"  Transporte:       {r.transport_cost:>12,.0f}")
    print(f"  Fijo CDs:         {r.fixed_cost:>12,.0f}")
    print(f"  Penalizacion:     {r.unmet_penalty_cost:>12,.0f}")
    print(f"CDs abiertos: {', '.join(r.open_depots)}")
    print("Utilizacion plantas: " + ", ".join(f"{k} {v:.0%}" for k, v in r.factory_utilization.items()))
    print("Utilizacion CDs:     " + ", ".join(f"{k} {v:.0%}" for k, v in r.depot_utilization.items()))
    if r.unmet_demand:
        print("Demanda NO servida:  " + ", ".join(f"{k} {v:.1f}" for k, v in r.unmet_demand.items()))


def print_delta(base: SolveResult, scen: SolveResult) -> None:
    # FUTURO: este diff (base vs escenario, en formato to_dict()) es el
    # input que recibira el LLM para redactar el reporte ejecutivo.
    if base.total_cost is None or scen.total_cost is None:
        return
    print("\n=== Impacto del escenario ===")
    for label, attr in [
        ("Costo total", "total_cost"),
        ("Transporte", "transport_cost"),
        ("Fijo CDs", "fixed_cost"),
        ("Penalizacion", "unmet_penalty_cost"),
    ]:
        b, s = getattr(base, attr), getattr(scen, attr)
        pct = f"{(s - b) / b:+.1%}" if b else "n/a"
        print(f"{label:<14}{b:>10,.0f} -> {s:>10,.0f}  ({pct})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Mostrar log de Gurobi")
    args = parser.parse_args()

    base_data = load_network(BASE_DATA)
    base = solve(base_data, verbose=args.verbose)
    print_result("Caso base", base)

    scen_data = apply_operations(base_data, EXAMPLE_SCENARIO)
    scen = solve(scen_data, verbose=args.verbose)
    print_result("Escenario: Planta Santiago al 50% + demanda norte +20%", scen)

    print_delta(base, scen)


if __name__ == "__main__":
    main()
