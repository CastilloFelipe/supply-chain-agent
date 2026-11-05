import json
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

from run_eval import same_operations, score_case  # noqa: E402

from network_opt import load_network  # noqa: E402
from network_opt.scenario import apply_operations  # noqa: E402

A = {"op": "scale_demand", "factor": 1.2, "region": "norte"}
B = {"op": "close_depot", "depot": "CD Temuco"}


def test_order_does_not_matter_and_factor_has_tolerance():
    assert same_operations([B, {**A, "factor": 1.2001}], [A, B])


def test_wrong_factor_or_extra_op_fails():
    assert not same_operations([{**A, "factor": 1.3}], [A])
    assert not same_operations([A, B], [A])


def test_unsupported_must_be_declared():
    exp = {"aceptables": [[]], "unsupported": True}
    assert not score_case([], "", exp)["acierto"]
    assert score_case([], "No hay herramienta para abrir CDs nuevos", exp)["acierto"]


@pytest.mark.parametrize("eval_set", ["v1", "v2", "v3"])
def test_expected_answers_are_valid_scenarios(eval_set):
    """Cada respuesta esperada debe ser un escenario ejecutable (evita errores en el set)."""
    folder = ROOT / "evals" / eval_set
    expected = json.loads((folder / "respuestas_esperadas.json").read_text(encoding="utf-8"))
    questions = json.loads((folder / "preguntas.json").read_text(encoding="utf-8"))
    assert {q["id"] for q in questions} == {k for k in expected if not k.startswith("_")}
    for q in questions:
        data = load_network(ROOT / q.get("datos", "data/base_network.json"))
        for alt in expected[q["id"]]["aceptables"]:
            apply_operations(data, alt)
