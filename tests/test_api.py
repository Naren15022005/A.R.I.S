import tempfile
from pathlib import Path

import pytest

pytest.importorskip("aris.loopy")

from fastapi.testclient import TestClient



@pytest.fixture(autouse=True)
def _db_aislada(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr("aris.config.DB_PATH", Path(tmp) / "aris.db")
    monkeypatch.setattr("aris.api._loopy", None)


@pytest.fixture
def client():
    from aris.api import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["nombre"] == "ARIS"


def test_chat(client):
    r = client.post("/chat", json={"mensaje": "hola"})
    assert r.status_code == 200
    data = r.json()
    assert "respuesta" in data
    assert data["regla"] == "saludar"


def test_chat_sin_regla(client):
    r = client.post("/chat", json={"mensaje": "xyzzy_inexistente"})
    assert r.status_code == 200
    data = r.json()
    assert data["regla"] is None
    assert "no entiendo" in data["respuesta"].lower() or "enseñarme" in data["respuesta"].lower()


def test_listar_hechos(client):
    client.post("/chat", json={"mensaje": "recuerda que Sócrates es humano"})
    r = client.get("/hechos")
    assert r.status_code == 200
    hechos = r.json()
    assert isinstance(hechos, list)
    assert len(hechos) > 0


def test_crear_hecho(client):
    r = client.post("/hechos", json={"sujeto": "Platón", "predicado": "es", "objeto": "filósofo"})
    assert r.status_code == 200
    data = r.json()
    assert data["sujeto"] == "Platón"
    assert data["objeto"] == "filósofo"


def test_buscar_hechos(client):
    client.post("/hechos", json={"sujeto": "Aristóteles", "predicado": "es", "objeto": "filósofo"})
    r = client.get("/hechos/buscar?q=Arist%C3%B3teles")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["sujeto"] == "Aristóteles"


def test_eliminar_hecho(client):
    r = client.post("/hechos", json={"sujeto": "Temp", "objeto": "temporal"})
    hecho_id = r.json()["id"]
    r = client.delete(f"/hechos/{hecho_id}")
    assert r.status_code == 200

    r = client.delete("/hechos/99999")
    assert r.status_code == 404


def test_listar_reglas(client):
    r = client.get("/reglas")
    assert r.status_code == 200
    reglas = r.json()
    assert isinstance(reglas, list)
    assert len(reglas) >= 10


def test_crear_regla(client):
    r = client.post("/reglas", json={"condicion": "'ping' in input", "accion": "eco", "prioridad": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["accion"] == "eco"
    assert data["condicion"] == "'ping' in input"

    r = client.post("/chat", json={"mensaje": "ping"})
    assert r.json()["regla"] == "eco"


def test_eliminar_regla(client):
    r = client.post("/reglas", json={"condicion": "'dummy' in input", "accion": "eco"})
    rid = r.json()["id"]
    r = client.delete(f"/reglas/{rid}")
    assert r.status_code == 200

    r = client.delete("/reglas/99999")
    assert r.status_code == 404


def test_sesion(client):
    r = client.get("/sesion")
    assert r.status_code == 200
    data = r.json()
    assert "sesion_id" in data
    assert data["reglas"] >= 10


def test_chat_con_sesion(client):
    r1 = client.post("/chat", json={"mensaje": "hola"})
    assert r1.status_code == 200
    r2 = client.post("/chat", json={"mensaje": "hola"})
    assert r2.json()["respuesta"]
