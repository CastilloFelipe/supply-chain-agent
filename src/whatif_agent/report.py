"""Reporte ejecutivo: caso base vs escenario.

Division de responsabilidades:
  - compare()      -> Python calcula TODAS las cifras (deterministico, testeable).
  - write_report() -> Claude redacta la interpretacion a partir de esas cifras.
  - summary_table()-> la tabla de numeros se genera en codigo y se anexa al
                      reporte, asi ninguna cifra del reporte depende del LLM.
"""

from __future__ import annotations

import json

import anthropic

from network_opt.data import NetworkData
from network_opt.model import SolveResult

MODEL = "claude-opus-5-5"
BOTTLENECK = 0.99  # utilizacion a partir de la cual un nodo es cuello de botella
TOP_FLOW_CHANGES = 8

SYSTEM_PROMPT = """Eres un analista senior de supply chain. Recibes la comparacion
entre el caso base y un escenario what-if de una red de distribucion, ya
calculada por un optimizador (Gurobi). Redacta un reporte ejecutivo en espanol,
en Markdown, para un gerente de operaciones.

Estructura:
## Resumen
2-3 frases con la conclusion principal.
## Que cambia en la red
Flujos, CDs abiertos/cerrados, cuellos de botella.
## Riesgos y lectura correcta de las cifras
## Recomendaciones
2-4 acciones concretas.

Reglas:
- Usa solo cifras presentes en los datos; no calcules cifras nuevas complejas.
- Interpreta, no repitas la tabla: se anexara automaticamente al final.
- Un costo de transporte menor NO es una mejora si se atiende menos demanda;
  usa costo por unidad servida y nivel de servicio para juzgarlo.
- La "penalizacion" es un costo ficticio del modelo para la demanda no servida;
  explicala como ventas perdidas o quiebres de stock, no como un gasto real.
- Si hubo supuestos o partes no modelables de la pregunta, mencionalos."""


class ReportError(RuntimeError):
    pass


def compare(
    base: SolveResult, scen: SolveResult, base_data: NetworkData, scen_data: NetworkData
) -> dict:
    for name, r in (("base", base), ("escenario", scen)):
        if r.total_cost is None:
            raise ReportError(f"El caso {name} no tiene solucion (estado {r.status}).")

    def kpis(r: SolveResult, data: NetworkData) -> dict:
        demand = sum(c["demand"] for c in data.customers.values())
        unmet = sum(r.unmet_demand.values())
        served = demand - unmet
        return {
            "costo_total": r.total_cost,
            "costo_transporte": r.transport_cost,
            "costo_fijo_cds": r.fixed_cost,
            "penalizacion_demanda_no_servida": r.unmet_penalty_cost,
            "demanda_total": demand,
            "demanda_servida": served,
            "demanda_no_servida": unmet,
            "nivel_servicio": served / demand if demand else 1.0,
            "costo_transporte_por_unidad_servida": r.transport_cost / served if served else None,
            "costo_operacional_por_unidad_servida":
                (r.transport_cost + r.fixed_cost) / served if served else None,
        }

    kb, ks = kpis(base, base_data), kpis(scen, scen_data)
    deltas = {}
    for k in kb:
        b, s = kb[k], ks[k]
        if b is None or s is None:
            continue
        deltas[k] = {"abs": s - b, "pct": (s - b) / b if b else None}

    arcs = set(base.flows) | set(scen.flows)
    flow_changes = sorted(
        (
            {"desde": i, "hacia": j, "base": base.flows.get((i, j), 0.0),
             "escenario": scen.flows.get((i, j), 0.0)}
            for i, j in arcs
        ),
        key=lambda f: -abs(f["escenario"] - f["base"]),
    )
    flow_changes = [f for f in flow_changes if abs(f["escenario"] - f["base"]) > 1e-6][:TOP_FLOW_CHANGES]

    def bottlenecks(r: SolveResult) -> list[str]:
        util = {**r.factory_utilization, **r.depot_utilization}
        return sorted(n for n, u in util.items() if u >= BOTTLENECK)

    return {
        "kpis_base": kb,
        "kpis_escenario": ks,
        "variacion": deltas,
        "cds_abiertos": {
            "base": base.open_depots,
            "escenario": scen.open_depots,
            "cerrados_en_escenario": sorted(set(base.open_depots) - set(scen.open_depots)),
            "abiertos_en_escenario": sorted(set(scen.open_depots) - set(base.open_depots)),
        },
        "demanda_no_servida_por_cliente": {
            c: {"no_servida": q, "demanda": scen_data.customers[c]["demand"],
                "region": scen_data.customers[c]["region"]}
            for c, q in sorted(scen.unmet_demand.items(), key=lambda kv: -kv[1])
        },
        "utilizacion": {
            "plantas": {f: {"base": base.factory_utilization[f], "escenario": scen.factory_utilization[f]}
                        for f in scen.factory_utilization},
            "cds": {d: {"base": base.depot_utilization[d], "escenario": scen.depot_utilization[d]}
                    for d in scen.depot_utilization},
        },
        "cuellos_de_botella": {"base": bottlenecks(base), "escenario": bottlenecks(scen)},
        "mayores_cambios_de_flujo": flow_changes,
    }


def summary_table(cmp: dict, units: dict | None = None) -> str:
    units = units or {"flow": "unidades", "cost": "$"}
    rows = [
        ("Costo total", "costo_total", "money"),
        ("Transporte", "costo_transporte", "money"),
        ("Costo fijo CDs", "costo_fijo_cds", "money"),
        ("Penalización demanda no servida", "penalizacion_demanda_no_servida", "money"),
        (f"Demanda servida ({units['flow']})", "demanda_servida", "num"),
        (f"Demanda no servida ({units['flow']})", "demanda_no_servida", "num"),
        ("Nivel de servicio", "nivel_servicio", "pct"),
        ("Transporte por unidad servida", "costo_transporte_por_unidad_servida", "money2"),
        ("Costo operacional por unidad servida", "costo_operacional_por_unidad_servida", "money2"),
    ]

    def fmt(v, kind):
        if v is None:
            return "n/a"
        return {
            "money": f"{v:,.0f}", "money2": f"{v:,.2f}", "num": f"{v:,.1f}", "pct": f"{v:.1%}",
        }[kind]

    out = [f"| Indicador ({units['cost']}) | Base | Escenario | Variación |", "|---|---:|---:|---:|"]
    for label, key, kind in rows:
        b, s = cmp["kpis_base"][key], cmp["kpis_escenario"][key]
        d = cmp["variacion"].get(key)
        if d is None:
            var = "n/a"
        elif kind == "pct":
            var = f"{d['abs'] * 100:+.1f} pp"
        elif d["pct"] is None:
            var = "nuevo" if d["abs"] else "0"
        else:
            var = f"{d['pct']:+.1%}"
        out.append(f"| {label} | {fmt(b, kind)} | {fmt(s, kind)} | {var} |")
    return "\n".join(out)


def write_report(
    question: str,
    cmp: dict,
    scenario_info: dict | None = None,
    units: dict | None = None,
    client: anthropic.Anthropic | None = None,
    model: str = MODEL,
) -> str:
    client = client or anthropic.Anthropic()
    payload = {
        "pregunta": question,
        "escenario": scenario_info or {},
        "unidades": units or {},
        "comparacion": cmp,
    }
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{
            "role": "user",
            "content": "<datos>\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n</datos>",
        }],
    )
    if response.stop_reason == "refusal":
        raise ReportError("El modelo rechazo la solicitud.")
    if response.stop_reason == "max_tokens":
        raise ReportError("Reporte truncado (max_tokens).")

    narrative = "\n".join(b.text for b in response.content if b.type == "text").strip()
    return compose_report(question, narrative, cmp, units)


def compose_report(question: str, narrative: str, cmp: dict, units: dict | None = None) -> str:
    """Une la narrativa (escrita por un LLM) con la tabla de cifras (generada en codigo)."""
    narrative = narrative.strip()
    if not narrative:
        raise ReportError("La narrativa del reporte esta vacia.")
    return (
        f"# Reporte what-if\n\n**Pregunta:** {question}\n\n{narrative}\n\n"
        f"## Cifras (calculadas por el optimizador)\n\n{summary_table(cmp, units)}\n"
    )
