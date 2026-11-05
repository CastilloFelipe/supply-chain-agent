"""Graficos Plotly de la demo. Colores: paleta de referencia validada (claro)."""

from __future__ import annotations

import plotly.graph_objects as go

from network_opt.data import NetworkData
from network_opt.model import SolveResult

# Roles de color (paleta categorica validada, en orden fijo; base en gris neutro)
PLANT = "#2a78d6"     # slot 1 azul
DEPOT = "#eb6834"     # slot 2 naranjo
CUSTOMER = "#1baf7a"  # slot 3 aqua
FLOW = "#2a78d6"
NEUTRAL = "#9a9893"   # caso base / CD cerrado
CRITICAL = "#d03b3b"  # estado: demanda no servida (siempre con icono + texto)
TEXT_2 = "#52514e"
GRID = "#e6e5e1"

FONT = dict(family="Inter, system-ui, sans-serif", size=13, color="#0b0b0b")


def has_coordinates(data: NetworkData) -> bool:
    nodes = [*data.factories.values(), *data.depots.values(), *data.customers.values()]
    return all("lat" in a and "lon" in a for a in nodes)


def network_map(data: NetworkData, result: SolveResult, title: str) -> go.Figure:
    pos = {n: (a["lat"], a["lon"]) for kind in (data.factories, data.depots, data.customers)
           for n, a in kind.items()}
    fig = go.Figure()
    max_flow = max(result.flows.values(), default=1.0)

    for (i, j), q in sorted(result.flows.items(), key=lambda kv: kv[1]):
        (la1, lo1), (la2, lo2) = pos[i], pos[j]
        fig.add_trace(go.Scatter(
            x=[lo1, lo2], y=[la1, la2], mode="lines",
            line=dict(width=1 + 6 * q / max_flow, color=FLOW), opacity=0.55,
            hoverinfo="text", text=f"{i} → {j}: {q:,.1f}", showlegend=False,
        ))

    def nodes(names, color, symbol, label, size, hover, labeled=False):
        if not names:
            return
        fig.add_trace(go.Scatter(
            x=[pos[n][1] for n in names], y=[pos[n][0] for n in names],
            mode="markers+text" if labeled else "markers", name=label,
            hoverinfo="text", hovertext=[hover(n) for n in names],
            text=[n.replace("Planta ", "").replace("CD ", "") for n in names] if labeled else None,
            textposition="middle right", textfont=dict(size=11, color=TEXT_2),
            marker=dict(size=size, color=color, symbol=symbol, line=dict(width=2, color="#fcfcfb")),
        ))

    pct = lambda v: f"{v:.0%}"
    nodes(list(data.factories), PLANT, "square", "Planta", 14,
          lambda n: f"<b>{n}</b><br>Utilización {pct(result.factory_utilization[n])}", labeled=True)
    open_ = [d for d in data.depots if d in result.open_depots]
    closed = [d for d in data.depots if d not in result.open_depots]
    nodes(open_, DEPOT, "diamond", "CD abierto", 14,
          lambda n: f"<b>{n}</b><br>Utilización {pct(result.depot_utilization[n])}")
    nodes(closed, NEUTRAL, "diamond-open", "CD cerrado", 12, lambda n: f"<b>{n}</b><br>Cerrado")
    served = [c for c in data.customers if c not in result.unmet_demand]
    short = [c for c in data.customers if c in result.unmet_demand]
    nodes(served, CUSTOMER, "circle", "Cliente atendido", 10,
          lambda n: f"<b>{n}</b><br>Demanda {data.customers[n]['demand']:,.1f}")
    nodes(short, CRITICAL, "x", "Cliente con quiebre", 12,
          lambda n: f"<b>{n}</b><br>No servido {result.unmet_demand[n]:,.1f} "
                    f"de {data.customers[n]['demand']:,.1f}", labeled=True)

    # Diagrama georreferenciado (lat/lon reales, sin mapa de fondo: funciona offline).
    lats = [p[0] for p in pos.values()]
    lons = [p[1] for p in pos.values()]
    fig.update_xaxes(range=[min(lons) - 1.5, max(lons) + 4.5], showgrid=False, zeroline=False,
                     showticklabels=False)
    fig.update_yaxes(range=[min(lats) - 1, max(lats) + 1], scaleanchor="x", scaleratio=1.2,
                     showgrid=True, gridcolor=GRID, zeroline=False, ticksuffix="°", dtick=5)
    fig.update_layout(plot_bgcolor="#fcfcfb",
        title=dict(text=title, font=dict(size=15)), font=FONT, height=720,
        margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="#fcfcfb",
        legend=dict(orientation="h", y=-0.02, font=dict(size=12)),
    )
    return fig


def utilization_chart(base: SolveResult, scen: SolveResult) -> go.Figure:
    util_b = {**base.factory_utilization, **base.depot_utilization}
    util_s = {**scen.factory_utilization, **scen.depot_utilization}
    names = list(util_s)[::-1]
    fig = go.Figure([
        go.Bar(y=names, x=[util_b[n] for n in names], name="Base", orientation="h",
               marker=dict(color=NEUTRAL, cornerradius=4),
               hovertemplate="%{y}: %{x:.0%}<extra>Base</extra>"),
        go.Bar(y=names, x=[util_s[n] for n in names], name="Escenario", orientation="h",
               marker=dict(color=FLOW, cornerradius=4),
               hovertemplate="%{y}: %{x:.0%}<extra>Escenario</extra>"),
    ])
    fig.add_vline(x=1, line=dict(color=TEXT_2, width=1, dash="dot"))
    fig.update_layout(
        barmode="group", bargap=0.35, bargroupgap=0.1, font=FONT, height=60 + 44 * len(names),
        xaxis=dict(tickformat=".0%", range=[0, 1.08], gridcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
        margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.08),
    )
    return fig


def unmet_chart(cmp: dict) -> go.Figure | None:
    rows = cmp["demanda_no_servida_por_cliente"]
    if not rows:
        return None
    names = list(rows)[::-1]
    fig = go.Figure(go.Bar(
        y=names, x=[rows[n]["no_servida"] for n in names], orientation="h",
        marker=dict(color=CRITICAL, cornerradius=4),
        text=[f"{rows[n]['no_servida']:,.1f} de {rows[n]['demanda']:,.1f}" for n in names],
        textposition="outside", textfont=dict(color=TEXT_2),
        hovertemplate="%{y}: %{x:,.1f}<extra>No servido</extra>",
    ))
    fig.update_layout(
        font=FONT, height=60 + 40 * len(names), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
        xaxis=dict(gridcolor=GRID, zeroline=False, title="Unidades no servidas"),
        margin=dict(l=10, r=40, t=10, b=10),
    )
    return fig
