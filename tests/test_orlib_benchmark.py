"""Validacion contra la literatura: el modelo debe reproducir los optimos publicados
de OR-Library (Beasley). Es la prueba de que la formulacion esta bien."""

from pathlib import Path

import gurobipy as gp
import pytest

from network_opt import load_network, solve

DATA = Path(__file__).resolve().parents[1] / "data" / "orlib"


@pytest.mark.parametrize("instance", sorted(p.stem for p in DATA.glob("*.json")))
def test_matches_published_optimum(instance):
    data = load_network(DATA / f"{instance}.json")
    try:
        r = solve(data)
    except gp.GurobiError as e:
        if "size-limited license" in str(e):
            pytest.skip("Instancia grande: requiere licencia academica de Gurobi")
        raise
    assert r.status == "OPTIMAL"
    assert r.unmet_demand == {}
    assert r.total_cost == pytest.approx(data.meta["known_optimum"], rel=1e-6)
