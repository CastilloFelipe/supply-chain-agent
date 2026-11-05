"""Demo web del simulador what-if.

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "app")]

from charts import has_coordinates, network_map, unmet_chart, utilization_chart  # noqa: E402
from manual import ManualInputs, build_operations  # noqa: E402
from network_opt import load_network, solve  # noqa: E402
from network_opt.scenario import apply_operations  # noqa: E402
from whatif_agent.report import compare, summary_table  # noqa: E402

DATASETS = {
    "Red de distribución Chile (caso de estudio)": ROOT / "data" / "base_network.json",
    **{f"OR-Library {p.stem} (benchmark)": p for p in sorted((ROOT / "data" / "orlib").glob("*.json"))},
}
EXAMPLES = [
    "¿Qué pasa con el costo si la planta de Santiago reduce su capacidad a la mitad "
    "y la demanda en el norte aumenta un 20%?",
    "¿Y si cerramos el CD de La Serena y el diésel sube 15%?",
    "¿Conviene consolidar la red en solo 2 centros de distribución?",
    "¿Qué pasa si se corta la ruta hacia Arica?",
]
HAS_KEY = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

st.set_page_config(page_title="Simulador What-If de Red Logística", page_icon="🚚", layout="wide")


@st.cache_data(show_spinner=False)
def load(path: str):
    return load_network(path)


@st.cache_data(show_spinner="Optimizando con Gurobi...")
def solve_cached(path: str, ops_json: str):
    data = load(path)
    scen_data = apply_operations(data, json.loads(ops_json)) if ops_json != "[]" else data
    return scen_data, solve(scen_data)


# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("Configuración")
    dataset_label = st.selectbox("Red", list(DATASETS))
    path = str(DATASETS[dataset_label])
    data = load(path)
    mode = st.radio("Modo", ["Escenario manual", "Pregunta a Claude"],
                    help="El modo manual no usa el LLM ni gasta créditos.")

    if mode == "Escenario manual":
        with st.form("manual"):
            st.caption("100% = sin cambio respecto del caso base")
            st.subheader("Capacidad de plantas")
            fac = {f: st.slider(f, 0, 150, 100, 5, format="%d%%") for f in data.factories}
            regions = sorted({a["region"] for a in data.customers.values()})
            st.subheader("Demanda por región")
            dem = {r: st.slider(r.capitalize(), 50, 200, 100, 5, format="%d%%") for r in regions}
            st.subheader("Costos")
            transport = st.slider("Transporte (diésel, peajes)", 50, 200, 100, 5, format="%d%%")
            fixed = st.slider("Costo fijo de CDs (arriendos)", 50, 200, 100, 5, format="%d%%")
            st.subheader("Estructura")
            closed = st.multiselect("Cerrar CDs", list(data.depots))
            limit = st.checkbox("Limitar número de CDs abiertos")
            max_d = st.number_input("Máximo de CDs", 0, len(data.depots), min(2, len(data.depots)))
            submitted = st.form_submit_button("Simular", type="primary", use_container_width=True)
        if submitted:
            st.session_state.run = {
                "path": path, "question": None, "translated": None,
                "ops": build_operations(ManualInputs(fac, dem, transport, fixed, closed,
                                                     int(max_d) if limit else None)),
            }

# ---------------------------------------------------------------- Main
st.title("Simulador What-If de Red Logística")
st.caption("Optimización MILP con Gurobi + traducción de preguntas de negocio con Claude · "
           f"Red: **{dataset_label}** · {len(data.factories)} plantas, {len(data.depots)} CDs, "
           f"{len(data.customers)} clientes")

if mode == "Pregunta a Claude":
    if not HAS_KEY:
        st.warning("Para este modo define la variable de entorno `ANTHROPIC_API_KEY` antes de "
                   "lanzar la app. El modo manual funciona sin ella.")
    example = st.selectbox("Ejemplos", ["(escribe tu propia pregunta)", *EXAMPLES])
    question = st.text_area("Pregunta de negocio",
                            value="" if example.startswith("(") else example, height=90)
    if st.button("Simular", type="primary", disabled=not (HAS_KEY and question.strip())):
        from whatif_agent import TranslationError, translate

        try:
            with st.spinner("Claude está traduciendo la pregunta..."):
                scenario = translate(question, data)
            st.session_state.run = {"path": path, "question": question,
                                    "translated": scenario.to_dict(), "ops": scenario.operations}
        except TranslationError as e:
            st.error(f"No se pudo traducir la pregunta: {e}")

run = st.session_state.get("run")
if not run or run["path"] != path:
    st.info("Configura un escenario en la barra lateral (o haz una pregunta) y presiona **Simular**.")
    st.stop()

try:
    _, base = solve_cached(path, "[]")
    scen_data, scen = solve_cached(path, json.dumps(run["ops"], sort_keys=True))
except ValueError as e:
    st.error(f"Escenario inválido: {e}")
    st.stop()

cmp = compare(base, scen, data, scen_data)
units = data.meta.get("units", {"flow": "unidades", "cost": "$"})

if run["translated"]:
    t = run["translated"]
    st.markdown(f"**Interpretación de Claude:** {t['interpretation']}")
    if t["assumptions"]:
        st.markdown("**Supuestos:** " + "; ".join(t["assumptions"]))
    if t["unsupported"]:
        st.warning(f"No modelable con las herramientas actuales: {t['unsupported']}")
with st.expander("Operaciones aplicadas (JSON auditable)"):
    st.json(run["ops"] or [])

# KPIs
kb, ks = cmp["kpis_base"], cmp["kpis_escenario"]
c1, c2, c3, c4 = st.columns(4)


def metric(col, label, key, fmt, inverse=True, absolute=False):
    b, s = kb[key], ks[key]
    if absolute:
        delta = f"{s - b:+,.1f}" if abs(s - b) > 1e-6 else None
    else:
        delta = None if b in (None, 0) or s is None else f"{(s - b) / b:+.1%}"
    col.metric(label, fmt(s) if s is not None else "n/a", delta,
               delta_color="inverse" if inverse else "normal", border=True)


money = lambda v: f"{units['cost']} {v:,.0f}"
metric(c1, "Costo total", "costo_total", money)
metric(c2, "Costo de transporte", "costo_transporte", money)
metric(c3, "Nivel de servicio", "nivel_servicio", lambda v: f"{v:.1%}", inverse=False)
# Demanda no servida y no "costo por unidad": un costo unitario que baja porque se
# atiende menos se veria como mejora (en verde). Ese indicador queda en "Cifras".
metric(c4, f"Demanda no servida ({units['flow']})", "demanda_no_servida",
       lambda v: f"{v:,.1f}", absolute=True)

if ks["demanda_no_servida"] > 1e-6:
    st.error(f"⚠️ Quiebre de stock: {ks['demanda_no_servida']:,.1f} {units['flow']} sin atender "
             f"({1 - ks['nivel_servicio']:.1%} de la demanda). Un costo de transporte menor en este "
             "escenario no es una mejora: refleja menos unidades despachadas.")

tab_map, tab_util, tab_unmet, tab_num, tab_report = st.tabs(
    ["Mapa de flujos", "Utilización", "Demanda no servida", "Cifras", "Reporte ejecutivo"])

with tab_map:
    if has_coordinates(data):
        a, b = st.columns(2)
        a.plotly_chart(network_map(data, base, "Caso base"), use_container_width=True)
        b.plotly_chart(network_map(scen_data, scen, "Escenario"), use_container_width=True)
    else:
        st.info("Esta red no tiene coordenadas (las instancias de OR-Library son abstractas). "
                "Revisa los cambios de flujo en la pestaña **Cifras**.")

with tab_util:
    st.caption("Utilización de capacidad por planta y CD. La línea punteada marca el 100%.")
    st.plotly_chart(utilization_chart(base, scen), use_container_width=True)

with tab_unmet:
    fig = unmet_chart(cmp)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("Toda la demanda se atiende en este escenario.")

with tab_num:
    st.markdown(summary_table(cmp, units))
    st.subheader("Mayores cambios de flujo")
    st.dataframe(
        [{"Desde": f["desde"], "Hacia": f["hacia"], "Base": round(f["base"], 1),
          "Escenario": round(f["escenario"], 1), "Cambio": round(f["escenario"] - f["base"], 1)}
         for f in cmp["mayores_cambios_de_flujo"]],
        hide_index=True, use_container_width=True,
    )
    cds = cmp["cds_abiertos"]
    if cds["cerrados_en_escenario"] or cds["abiertos_en_escenario"]:
        st.markdown(f"**CDs que cierran:** {', '.join(cds['cerrados_en_escenario']) or '—'} · "
                    f"**CDs que abren:** {', '.join(cds['abiertos_en_escenario']) or '—'}")

with tab_report:
    if not HAS_KEY:
        st.info("El reporte ejecutivo lo redacta Claude: define `ANTHROPIC_API_KEY` para activarlo.")
    elif st.button("Generar reporte ejecutivo"):
        from whatif_agent.report import ReportError, write_report

        question = run["question"] or "Escenario manual: " + json.dumps(run["ops"], ensure_ascii=False)
        try:
            with st.spinner("Claude está redactando el reporte..."):
                st.session_state.report = write_report(question, cmp, run["translated"] or {}, units)
        except ReportError as e:
            st.error(str(e))
    if st.session_state.get("report"):
        st.markdown(st.session_state.report)
        st.download_button("Descargar reporte (.md)", st.session_state.report, "reporte.md")
