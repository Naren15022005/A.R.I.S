import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aris.api import app
from aris.config import DATA_DIR, DB_PATH, init_paths
from aris.sandbox import PermisoError, SandboxComando, SandboxRuta
from aris.tools import FileSystemTool, TerminalTool


@pytest.fixture(autouse=True)
def _aislar_workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("aris.sandbox.WORKSPACE", ws)
    monkeypatch.setattr("aris.config.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("aris.config.DATA_DIR", tmp_path / "data")


def test_config_paths():
    init_paths()
    assert DATA_DIR is not None
    assert DB_PATH is not None


def test_sandbox_ruta_crear_y_leer():
    sr = SandboxRuta()
    p = sr.resolver("ejemplo.txt")
    p.write_text("hola mundo", encoding="utf-8")
    assert sr.leer("ejemplo.txt") == "hola mundo"


def test_sandbox_ruta_path_traversal():
    sr = SandboxRuta()
    with pytest.raises(PermisoError):
        sr.resolver("../../../etc/passwd")


def test_sandbox_comando_permitido():
    assert SandboxComando.permitido("echo test")
    assert SandboxComando.permitido("ls -la")
    assert not SandboxComando.permitido("rm -rf /")
    assert not SandboxComando.permitido("cat /etc/passwd | grep root")


def test_fs_tool_escribir_y_leer():
    ft = FileSystemTool()
    res_w = ft.escribir("doc.txt", "contenido público")
    assert res_w.success
    res_r = ft.leer("doc.txt")
    assert res_r.success
    assert res_r.output == "contenido público"


def test_fs_tool_bloquea_traversal():
    ft = FileSystemTool()
    res = ft.leer("../../../secret.txt")
    assert not res.success
    assert "denegado" in res.error.lower()


def test_terminal_tool_comando_permitido():
    res = TerminalTool.ejecutar("echo hola")
    assert res.success
    assert "hola" in res.output


def test_terminal_tool_comando_prohibido():
    res = TerminalTool.ejecutar("rm -rf /")
    assert not res.success
    assert "denegado" in res.error.lower() or "no permitido" in res.error.lower()


def test_api_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["nombre"] == "ARIS"
    assert "version" in data
