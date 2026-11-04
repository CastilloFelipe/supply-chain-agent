from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from network_opt import load_network, solve
from network_opt.scenario import apply_operations
from whatif_agent.report import ReportError, compare, summary_table, write_report

BASE = Path(__file__).resolve().parents[1] / "data" / "base_network.json"
OPS = [
    {"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
    {"op": "scale_demand", "factor": 1.2, "region": "norte"},
]


@pytest.fixture(scope="module")
def cmp():
    base = load_network(BASE)
    scen = apply_operations(base, OPS)
    return compare(solve(base), solve(scen), base, scen)


def test_service_level_and_unit_cost(cmp):
    b, s = cmp["kpis_base"], cmp["kpis_escenario"]
    assert b["nivel_servicio"] == pytest.approx(1.0)
    assert s["demanda_no_servida"] == pytest.approx(63.0)
    assert s["nivel_servicio"] == pytest.approx(175 / 238)
    assert s["costo_transporte_por_unidad_servida"] == pytest.approx(s["costo_transporte"] / 175)


def test_detects_closed_depot_and_bottlenecks(cmp):
    assert cmp["cds_abiertos"]["cerrados_en_escenario"] == ["CD La Serena"]
    assert set(cmp["cuellos_de_botella"]["escenario"]) == {"Planta Santiago", "Planta Concepcion"}


def test_unmet_demand_sorted_desc(cmp):
    qty = [v["no_servida"] for v in cmp["demanda_no_servida_por_cliente"].values()]
    assert qty == sorted(qty, reverse=True)


def test_table_has_all_rows(cmp):
    t = summary_table(cmp)
    assert "Nivel de servicio" in t and "-26.5 pp" in t


class FakeClient:
    def __init__(self, resp):
        self.resp, self.calls = resp, []
        self.beta = NS(messages=NS(create=lambda **kw: (self.calls.append(kw), self.resp)[1]))


def test_report_appends_code_generated_table(cmp):
    client = FakeClient(NS(stop_reason="end_turn", content=[NS(type="text", text="## Resumen\nTexto")]))
    md = write_report("¿Qué pasa si...?", cmp, client=client)
    assert md.startswith("# Reporte what-if")
    assert "## Resumen" in md and "| Costo total |" in md
    assert "<datos>" in client.calls[0]["messages"][0]["content"]


def test_report_refusal_raises(cmp):
    with pytest.raises(ReportError):
        write_report("x", cmp, client=FakeClient(NS(stop_reason="refusal", content=[])))
