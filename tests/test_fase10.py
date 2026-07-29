import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aris.api import app
from aris.embeddings import MotorEmbeddings
from aris.eventos import BusEventos, bus_eventos
from aris.grafo import GrafoConocimiento
from aris.percepcion import CanalBCI, CanalTextoSLM, RegistroPercepcion
from aris.tools import QuantumTool


@pytest.fixture
def tmp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        yield Path(tmp) / "test_fase10.db"


# ─── 10.1 GrafoConocimiento ──────────────────────────────────────────────────


def test_grafo_crear_nodos_y_aristas(tmp_db):
    g = GrafoConocimiento(tmp_db)
    n1 = g.crear_nodo("simbolico", "regla", "Saludar al usuario", {"prioridad": 8})
    n2 = g.crear_nodo("memoria", "hecho", "Sócrates es humano", {"sujeto": "Sócrates"})

    assert n1 is not None
    assert n2 is not None

    a1 = g.crear_arista(n1, n2, "inferida", peso=0.95)
    assert a1 is not None

    nodos_simb = g.nodos_por_tipo("simbolico")
    assert len(nodos_simb) == 1
    assert nodos_simb[0]["etiqueta"] == "Saludar al usuario"

    vecinos_n1 = g.vecinos(n1)
    assert len(vecinos_n1) == 1
    assert vecinos_n1[0]["id"] == n2

    json_exp = g.exportar_json()
    assert len(json_exp["nodos"]) == 2
    assert len(json_exp["aristas"]) == 1


# ─── 10.2 Percepción Multicanal ──────────────────────────────────────────────


def test_percepcion_multicanal():
    reg = RegistroPercepcion()
    assert len(reg.canales) >= 2

    # Canal Texto SLM / Patrones
    res_txt = reg.interpretar("recuerda que la Luna es un satélite", canal="texto_libre")
    assert res_txt["intencion"] == "guardar_hecho"
    assert res_txt["sujeto"] == "la Luna"

    # Canal BCI (Biométrico)
    res_bci = reg.interpretar(0.85, canal="bci_neurosity")
    assert res_bci["intencion"] == "estado_biometrico"
    assert res_bci["objeto"] == "alto"


def test_canal_bci_niveles():
    bci = CanalBCI()
    assert bci.interpretar(0.90)["objeto"] == "alto"
    assert bci.interpretar(0.50)["objeto"] == "medio"
    assert bci.interpretar(0.10)["objeto"] == "bajo"


# ─── 10.3 Embeddings Semánticos ─────────────────────────────────────────────


def test_embeddings_motor():
    me = MotorEmbeddings()
    v1 = me.vectorizar("regar las plantas el lunes")
    v2 = me.vectorizar("el lunes toca riego")
    assert len(v1) > 0
    assert len(v2) > 0

    sim = me.similitud_textos("regar plantas", "regar las plantas el lunes")
    assert sim > 0.0


# ─── 10.4 EventBus & Endpoints ───────────────────────────────────────────────


def test_bus_eventos():
    bus = BusEventos()
    eventos_recibidos = []

    def callback(evt):
        eventos_recibidos.append(evt)

    bus.suscribir_listener(callback)
    bus.publicar({"accion": "test_nodo", "id": "123"})
    assert len(eventos_recibidos) == 1
    assert eventos_recibidos[0]["id"] == "123"

    bus.desuscribir_listener(callback)
    bus.publicar({"accion": "test_nodo", "id": "456"})
    assert len(eventos_recibidos) == 1


def test_endpoint_grafo():
    client = TestClient(app)
    r = client.get("/grafo")
    assert r.status_code == 200
    data = r.json()
    assert "nodos" in data or "nodes" in data


def test_websocket_grafo():
    client = TestClient(app)
    with client.websocket_connect("/ws/grafo") as websocket:
        data = websocket.receive_json()
        assert data["accion"] == "init"
        assert "data" in data


# ─── 10.5 QuantumTool ────────────────────────────────────────────────────────


def test_quantum_tool():
    res = QuantumTool.optimizar("optimizar_ruta", n_variables=4, datos=[10.0, 20.0, 5.0, 15.0])
    assert res.success
    assert "estado_optimo" in res.output
    assert "energia_minima" in res.output

    res_exceso = QuantumTool.optimizar("gran_problema", n_variables=32)
    assert not res_exceso.success
    assert "excedido" in res_exceso.error.lower()


# ─── 10.6 Refuerzo Hebbiano y Métricas ────────────────────────────────────────


def test_refuerzo_hebbiano_y_decaimiento(tmp_db):
    g = GrafoConocimiento(tmp_db)
    n1 = g.crear_nodo("simbolico", "regla", "Regla A")
    n2 = g.crear_nodo("memoria", "hecho", "Hecho A")
    aid = g.crear_arista(n1, n2, "inferida", peso=1.0)

    nuevo_peso = g.reforzar_arista(aid, incremento=0.5)
    assert nuevo_peso == 1.5

    # Decaimiento
    g.decaer_pesos(factor=0.5, umbral_minimo=0.1)
    vecinos = g.vecinos(n1)
    assert len(vecinos) == 1
    assert vecinos[0]["peso"] == 0.75

    # Decaimiento sub-umbral (eliminación de arista inactiva)
    g.decaer_pesos(factor=0.01, umbral_minimo=0.1)
    vecinos_post = g.vecinos(n1)
    assert len(vecinos_post) == 0

    metricas = g.obtener_metricas_aprendizaje()
    assert metricas["total_nodos"] == 2
    assert metricas["total_aristas"] == 0


def test_endpoint_metricas_aprendizaje():
    client = TestClient(app)
    r = client.get("/metricas/aprendizaje")
    assert r.status_code == 200
    data = r.json()
    assert "total_nodos" in data
    assert "total_aristas" in data
    assert "peso_promedio" in data

