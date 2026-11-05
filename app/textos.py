"""Textos explicativos de la app: de qué se trata, cómo leerla y el ejemplo del modo Claude."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
EJEMPLO_ESCENARIO = RAIZ / "docs" / "ejemplo_escenario.json"
EJEMPLO_REPORTE = RAIZ / "docs" / "ejemplo_reporte.md"
REPO = "https://github.com/CastilloFelipe/supply-chain-agent"

CONCEPTOS = [
    ("Red de distribución de tres niveles",
     "**Plantas** que producen → **centros de distribución (CD)** que almacenan y despachan → "
     "**clientes** con demanda. Cada tramo tiene un costo de transporte por pallet y cada nodo "
     "una capacidad. Operar un CD tiene además un **costo fijo** (arriendo, personal)."),
    ("Optimización (MILP)",
     "Un **modelo de programación lineal entera mixta** decide cuánto enviar por cada ruta y qué "
     "CDs abrir para **minimizar el costo total** respetando capacidades y demanda. Lo resuelve "
     "**Gurobi**, un solver comercial. *Entera* porque abrir un CD es una decisión sí/no."),
    ("Escenario what-if",
     "Un cambio hipotético sobre la red (capacidad, demanda, costos, cierres, rutas cortadas). El "
     "modelo se vuelve a optimizar con el cambio y se compara contra el **caso base**, la mejor "
     "red con los datos actuales."),
    ("Demanda no servida",
     "Si un escenario deja a la red sin capacidad suficiente, en vez de fallar el modelo indica "
     "**cuántas unidades no se pueden atender y dónde** (con una penalización en el costo). Así se "
     "ven los quiebres de stock en lugar de un \"sin solución\"."),
    ("Nivel de servicio y costo por unidad servida",
     "**Nivel de servicio:** porcentaje de la demanda que sí se atiende. **Costo por unidad "
     "servida:** cuánto cuesta cada pallet efectivamente entregado. Un costo de transporte menor "
     "no es una mejora si se atiende menos demanda: hay que mirar las dos cifras juntas."),
    ("Cuello de botella",
     "Una planta o CD al 100% de su capacidad. Es lo primero que limita la red cuando algo cambia, "
     "y suele ser donde conviene invertir."),
    ("Traductor con IA (modo Claude)",
     "Un modelo de lenguaje (Claude) convierte una pregunta en español en **operaciones** sobre el "
     "modelo, usando herramientas con nombres validados contra la red (no puede inventar CDs que "
     "no existen). Los números **siempre los calcula Gurobi**; la IA solo traduce e interpreta."),
]


def intro() -> None:
    """Se muestra mientras no hay un escenario simulado."""
    st.subheader("¿De qué se trata?")
    st.markdown("""
Una empresa con plantas, centros de distribución y clientes necesita responder preguntas como
*"¿qué pasa si cerramos el CD de La Serena y el diésel sube 15%?"*. Este simulador lo responde
con **optimización matemática**: vuelve a diseñar la red de menor costo con el cambio y muestra
el impacto en costos, nivel de servicio, flujos y cuellos de botella.

**Cómo usarlo:**
1. En la barra lateral elige la red (la de Chile es la más visual) y el modo.
2. **Escenario manual:** mueve los controles (capacidad, demanda, costos, cierre de CDs) y presiona
   **Simular**. No usa IA.
3. **Pregunta a Claude:** escribe la pregunta en lenguaje natural. En esta versión pública puedes ver
   un ejemplo real de pregunta traducida y su reporte, y cargarlo en el simulador.
""")
    st.subheader("Qué demuestra el proyecto")
    st.markdown("""
- **El modelo está validado contra la literatura:** reproduce exactamente los costos óptimos
  publicados de las instancias *Capacitated Warehouse Location* de la OR-Library (cap41, cap71 y
  cap101). Puedes elegirlas en la barra lateral.
- **El traductor con IA se evaluó a ciegas:** 70 preguntas en tres sets de dificultad creciente,
  traducidas por un agente que no veía las respuestas. Acertó 22/22, 22/24 y, tras corregir los dos
  fallos, 24/24 en un set nuevo.
- **La lectura de las cifras es honesta:** si un escenario deja demanda sin atender, el costo de
  transporte baja, y la app lo advierte en vez de mostrarlo como un ahorro.
""")
    st.subheader("Conceptos clave")
    for titulo, texto in CONCEPTOS:
        with st.expander(titulo):
            st.markdown(texto)
    st.caption(f"Código, formulación completa y evaluación en [GitHub]({REPO}).")


def guia_resultados() -> None:
    with st.expander("¿Cómo leer los resultados?"):
        st.markdown("""
- **Indicadores de arriba:** valor en el escenario y, en color, el cambio contra el caso base. En
  costos, rojo significa que sube; en nivel de servicio, que baja.
- **Mapa de flujos:** el caso base a la izquierda y el escenario a la derecha. El grosor de cada
  línea es el volumen enviado. Una **X roja** es un cliente con demanda sin atender; un rombo
  vacío es un CD cerrado.
- **Utilización:** qué tan llena queda cada planta y CD. La línea punteada es el 100%: lo que
  llega ahí es un cuello de botella.
- **Demanda no servida:** cuántas unidades faltan por cliente.
- **Cifras:** la tabla completa del caso base contra el escenario, y las rutas que más cambian.
- **Operaciones aplicadas:** el escenario exacto en JSON, para repetirlo o auditarlo.
""")


def ejemplo_claude() -> bool:
    """Muestra el ejemplo del modo Claude. Devuelve True si se pidió cargarlo en el simulador."""
    st.info("La versión pública no tiene una API key de Claude conectada (cada pregunta tiene un "
            "costo). Abajo está un ejemplo real: la pregunta, cómo la tradujo Claude y el reporte "
            "que redactó. Puedes cargar ese mismo escenario en el simulador. Para usar tus "
            "propias preguntas, corre la app localmente con `ANTHROPIC_API_KEY` "
            f"(instrucciones en [GitHub]({REPO})).")
    if not (EJEMPLO_ESCENARIO.exists() and EJEMPLO_REPORTE.exists()):
        return False
    import json

    if st.session_state.get("run", {}).get("ejemplo"):
        st.success("Ejemplo cargado: abajo están los resultados que calculó Gurobi, y el reporte "
                   "de Claude en la pestaña **Reporte ejecutivo**.")
        return False
    ej = json.loads(EJEMPLO_ESCENARIO.read_text(encoding="utf-8"))
    st.markdown(f"**Pregunta:** {ej['question']}")
    st.markdown(f"**Interpretación de Claude:** {ej['interpretation']}")
    if ej.get("assumptions"):
        st.markdown("**Supuestos:** " + "; ".join(ej["assumptions"]))
    with st.expander("Operaciones que generó (JSON)"):
        st.json(ej["calls"])
    with st.expander("Reporte ejecutivo que redactó"):
        st.markdown(EJEMPLO_REPORTE.read_text(encoding="utf-8"))
    return st.button("Cargar este escenario en el simulador", type="primary")
