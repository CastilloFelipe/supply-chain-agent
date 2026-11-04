"""Tests del traductor con un cliente falso (no llaman a la API ni gastan creditos)."""

from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from network_opt import load_network
from whatif_agent import TranslationError, translate
from whatif_agent.tools import build_tools

BASE = Path(__file__).resolve().parents[1] / "data" / "base_network.json"


@pytest.fixture
def data():
    return load_network(BASE)


def tool_use(id_, name, **args):
    return NS(type="tool_use", id=id_, name=name, input=args)


def response(*blocks, stop="tool_use"):
    return NS(stop_reason=stop, content=list(blocks))


class FakeClient:
    """Devuelve respuestas guionadas y registra lo que se envio."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


FINISH = dict(interpretation="x", assumptions=[], unsupported="")


def test_translates_example_question(data):
    client = FakeClient(response(
        tool_use("1", "scale_factory_capacity", factory="Planta Santiago", factor=0.5),
        tool_use("2", "scale_demand", region="norte", factor=1.2),
        tool_use("3", "finish_scenario", **FINISH),
    ))
    s = translate("Santiago a la mitad y norte +20%", data, client=client)
    assert s.operations == [
        {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
        {"op": "scale_demand", "factor": 1.2, "region": "norte"},
    ]
    assert data.factories["Planta Santiago"]["capacity"] == 150  # base intacta


def test_invalid_call_is_returned_as_error_and_model_can_fix_it(data):
    client = FakeClient(
        response(
            tool_use("1", "scale_factory_capacity", factory="Planta Santiago", factor=-0.5),
            tool_use("2", "finish_scenario", **FINISH),
        ),
        response(
            tool_use("3", "scale_factory_capacity", factory="Planta Santiago", factor=0.5),
            tool_use("4", "finish_scenario", **FINISH),
        ),
    )
    s = translate("...", data, client=client)
    assert s.operations == [{"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5}]
    # messages: [user, assistant, tool_results, assistant]
    tool_results = client.calls[1]["messages"][2]["content"]
    assert tool_results[0]["is_error"] is True


def test_wildcards_map_to_none(data):
    client = FakeClient(response(
        tool_use("1", "scale_arc_costs", origin="*", destination="*", factor=1.15),
        tool_use("2", "finish_scenario", **FINISH),
    ))
    s = translate("diesel +15%", data, client=client)
    assert s.operations == [{"op": "scale_arc_costs", "factor": 1.15, "origin": None, "destination": None}]


def test_refusal_raises(data):
    with pytest.raises(TranslationError):
        translate("...", data, client=FakeClient(response(stop="refusal")))


def test_ending_without_finish_raises(data):
    text = NS(type="text", text="No entiendo")
    with pytest.raises(TranslationError):
        translate("...", data, client=FakeClient(response(text, stop="end_turn")))


def test_tool_enums_come_from_data(data):
    tools = {t["name"]: t for t in build_tools(data)}
    enum = tools["scale_factory_capacity"]["input_schema"]["properties"]["factory"]["enum"]
    assert enum == ["Planta Concepcion", "Planta Santiago"]
    assert all(t["strict"] for t in tools.values())
