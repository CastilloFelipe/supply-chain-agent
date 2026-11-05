"""Smoke tests de la demo web (Streamlit AppTest, sin navegador ni LLM)."""

from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def run_manual(dataset_index: int):
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.sidebar.selectbox[0].set_value(at.sidebar.selectbox[0].options[dataset_index]).run()
    at.sidebar.slider[0].set_value(50)
    at.sidebar.button[0].click().run()
    return at


def test_chile_network_runs():
    at = run_manual(0)
    assert not at.exception
    assert any("Quiebre de stock" in e.value for e in at.error)


def test_orlib_instance_without_coordinates_runs():
    at = run_manual(1)  # cap101 (primera instancia OR-Library en orden alfabetico)
    assert not at.exception
    assert any("no tiene coordenadas" in i.value for i in at.info)


def test_intro_se_muestra_antes_de_simular(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert any(h.value == "¿De qué se trata?" for h in at.subheader)
    assert len(at.expander) >= 7  # conceptos clave


def test_modo_claude_sin_key_carga_el_ejemplo(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.sidebar.radio[0].set_value("Pregunta a Claude").run()
    assert not at.exception
    assert any("versión pública" in i.value for i in at.info)
    boton = next(b for b in at.button if b.label == "Cargar este escenario en el simulador")
    boton.click().run()
    assert not at.exception
    textos = " ".join(m.value for m in at.markdown)
    assert "Interpretación de Claude" in textos
    assert "Reporte what-if" in textos  # el reporte de ejemplo en su pestaña
