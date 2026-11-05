import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from manual import ManualInputs, build_operations  # noqa: E402


def test_no_changes_means_no_operations():
    assert build_operations(ManualInputs({"Planta Santiago": 100}, {"norte": 100})) == []


def test_controls_map_to_operations():
    ops = build_operations(ManualInputs(
        {"Planta Santiago": 50}, {"norte": 120}, transport_cost_pct=115, fixed_cost_pct=100,
        closed_depots=["CD La Serena"], max_open_depots=2,
    ))
    assert ops == [
        {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
        {"op": "scale_demand", "factor": 1.2, "region": "norte"},
        {"op": "scale_arc_costs", "factor": 1.15, "origin": None, "destination": None},
        {"op": "close_depot", "depot": "CD La Serena"},
        {"op": "set_max_open_depots", "n": 2},
    ]
