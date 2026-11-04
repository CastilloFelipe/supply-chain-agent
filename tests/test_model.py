from pathlib import Path

import pytest

from network_opt import load_network, solve
from network_opt.scenario import apply_operations

BASE = Path(__file__).resolve().parents[1] / "data" / "base_network.json"


@pytest.fixture(scope="module")
def base_data():
    return load_network(BASE)


@pytest.fixture(scope="module")
def base_result(base_data):
    return solve(base_data)


def test_base_case_is_optimal_and_serves_all_demand(base_result):
    assert base_result.status == "OPTIMAL"
    assert base_result.unmet_demand == {}


def test_cost_breakdown_adds_up(base_result):
    r = base_result
    assert r.total_cost == pytest.approx(r.transport_cost + r.fixed_cost + r.unmet_penalty_cost)


def test_flow_is_conserved_at_depots(base_data, base_result):
    for d in base_data.depots:
        inflow = sum(q for (i, j), q in base_result.flows.items() if j == d)
        outflow = sum(q for (i, j), q in base_result.flows.items() if i == d)
        assert inflow == pytest.approx(outflow)


def test_capacities_respected(base_result):
    assert all(u <= 1 + 1e-6 for u in base_result.factory_utilization.values())
    assert all(u <= 1 + 1e-6 for u in base_result.depot_utilization.values())


def test_scenario_does_not_mutate_base(base_data):
    before = base_data.factories["Planta Santiago"]["capacity"]
    apply_operations(base_data, [{"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5}])
    assert base_data.factories["Planta Santiago"]["capacity"] == before


def test_capacity_cut_creates_unmet_demand_instead_of_infeasibility(base_data):
    scen = apply_operations(base_data, [
        {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
        {"op": "scale_demand", "factor": 1.2, "region": "norte"},
    ])
    r = solve(scen)
    assert r.status == "OPTIMAL"
    total_demand = sum(c["demand"] for c in scen.customers.values())
    total_capacity = sum(f["capacity"] for f in scen.factories.values())
    assert sum(r.unmet_demand.values()) == pytest.approx(total_demand - total_capacity)


def test_closing_a_depot_removes_its_flow(base_data):
    r = solve(apply_operations(base_data, [{"op": "close_depot", "depot": "CD Antofagasta"}]))
    assert "CD Antofagasta" not in r.open_depots
    assert not any("CD Antofagasta" in arc for arc in r.flows)


def test_constraint_hook_is_applied(base_data):
    def at_most_two_depots(m, v, data):
        m.addConstr(v.open_depot.sum() <= 2, name="max_2_cds")

    r = solve(base_data, extra_constraints=at_most_two_depots)
    assert len(r.open_depots) <= 2


@pytest.mark.parametrize("ops", [
    [{"op": "drop_table"}],
    [{"op": "scale_factory_capacity", "factory": "Planta Marte", "factor": 0.5}],
    [{"op": "scale_demand", "factor": 1.1, "region": "antartica"}],
])
def test_invalid_operations_are_rejected(base_data, ops):
    with pytest.raises(ValueError):
        apply_operations(base_data, ops)
