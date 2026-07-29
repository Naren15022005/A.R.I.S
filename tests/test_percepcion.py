import pytest
from fastapi.testclient import TestClient

from aris.api import app
from aris.percepcion import CapaPercepcion


def test_percepcion_slm_disponible_retorna_bool():
    cp = CapaPercepcion()
    # Verifica que la comprobación no falle y retorne un booleano
    res = cp.disponible(timeout=0.1)
    assert isinstance(res, bool)



def test_percepcion_fallback_patrones():
    cp = CapaPercepcion()
    res_saludo = cp._via_patrones("Hola ARIS qué tal")
    assert res_saludo["intencion"] == "saludar"
    assert res_saludo["comando_normalizado"] == "hola"

    res_gracias = cp._via_patrones("muchas gracias")
    assert res_gracias["intencion"] == "agradecer"
    assert res_gracias["comando_normalizado"] == "gracias"

    res_hecho = cp._via_patrones("recuérdame que la Tierra es un planeta")
    assert res_hecho["intencion"] == "guardar_hecho"
    assert res_hecho["sujeto"] == "la Tierra"
    assert res_hecho["predicado"] == "es"
    assert res_hecho["objeto"] == "un planeta"
    assert res_hecho["comando_normalizado"] == "recuerda que la Tierra es un planeta"

    res_consulta = cp._via_patrones("qué sabes de Sócrates")
    assert res_consulta["intencion"] == "consultar_hecho"
    assert res_consulta["sujeto"] == "Sócrates"
    assert res_consulta["comando_normalizado"] == "qué sabes de Sócrates"


def test_percepcion_normalizar_comando():
    cp = CapaPercepcion()
    norm = cp.normalizar_comando("Hola ARIS")
    assert norm == "hola"


def test_endpoint_galaxia():
    client = TestClient(app)
    r = client.get("/galaxia")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "links" in data
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) > 0
