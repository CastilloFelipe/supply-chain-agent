import json
from pathlib import Path

import pytest

from network_opt import load_network
from whatif_agent.offline import catalog, load_scenario

BASE = Path(__file__).resolve().parents[1] / "data" / "base_network.json"


@pytest.fixture
def data():
    return load_network(BASE)


def write(tmp_path, calls, **extra):
    p = tmp_path / "esc.json"
    p.write_text(json.dumps({"question": "q", "calls": calls, **extra}), encoding="utf-8")
    return p


def test_loads_valid_scenario(tmp_path, data):
    p = write(tmp_path, [
        {"name": "scale_factory_capacity", "input": {"factory": "Planta Santiago", "factor": 0.5}},
        {"name": "scale_demand", "input": {"region": "norte", "factor": 1.2}},
    ], interpretation="i", assumptions=["a"])
    s = load_scenario(p, data)
    assert s.operations == [
        {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
        {"op": "scale_demand", "factor": 1.2, "region": "norte"},
    ]
    assert s.assumptions == ["a"]


@pytest.mark.parametrize("call, msg", [
    ({"name": "borrar_todo", "input": {}}, "desconocida"),
    ({"name": "close_depot", "input": {"depot": "CD Marte"}}, "no existe"),
    ({"name": "close_depot", "input": {}}, "campos"),
    ({"name": "set_max_open_depots", "input": {"n": "dos"}}, "integer"),
    ({"name": "set_max_open_depots", "input": {"n": True}}, "integer"),
])
def test_rejects_invalid_calls(tmp_path, data, call, msg):
    with pytest.raises(ValueError, match=msg):
        load_scenario(write(tmp_path, [call]), data)


def test_catalog_excludes_finish_and_has_enums(data):
    names = {t["name"] for t in catalog(data)}
    assert "finish_scenario" not in names and "block_route" in names
