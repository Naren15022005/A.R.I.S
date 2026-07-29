import tempfile
from pathlib import Path

import pytest

from aris.sandbox import SandboxRuta, SandboxComando, PermisoError
from aris.tools import FileSystemTool, TerminalTool, ToolResult
from aris.acciones import GestorAcciones
from aris.conocimiento import BaseConocimiento
from aris.memoria import MemoriaTrabajo
from aris.reglas import BaseReglas
from aris.reglas_arranque import REGLAS_INICIALES
from aris.loopy import Loopy


@pytest.fixture(autouse=True)
def _aislar(monkeypatch, tmp_path):
    ws = tmp_path / "tools_workspace"
    ws.mkdir()
    monkeypatch.setattr("aris.sandbox.WORKSPACE", ws)
    monkeypatch.setattr("aris.acciones._TOOL_FS", None)
    monkeypatch.setattr("aris.acciones._TOOL_TERM", None)
    monkeypatch.setattr("aris.acciones._TOOL_WEB", None)
    return ws


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


# ─── SandboxRuta ─────────────────────────────────────────────────────────────


def test_sandbox_ruta_crea_y_lee(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    (ws / "hola.txt").write_text("mundo")
    assert sr.leer("hola.txt") == "mundo"


def test_sandbox_ruta_fuera_de_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    with pytest.raises(PermisoError):
        sr.leer("/etc/passwd")


def test_sandbox_ruta_escribir_y_leer(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    sr.escribir("prueba.txt", "contenido de prueba")
    assert sr.leer("prueba.txt") == "contenido de prueba"


def test_sandbox_ruta_listar(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.txt").touch()
    (ws / "b.txt").touch()
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    entradas = sr.listar()
    assert "a.txt" in entradas
    assert "b.txt" in entradas


def test_sandbox_ruta_eliminar(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "tmp.txt").write_text("algo")
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    assert sr.eliminar("tmp.txt")
    assert not sr.eliminar("no_existe.txt")


def test_sandbox_ruta_path_traversal(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    sr = SandboxRuta.__new__(SandboxRuta)
    sr._base = ws.resolve()
    with pytest.raises(PermisoError):
        sr.leer("../etc/passwd")


# ─── SandboxComando ──────────────────────────────────────────────────────────


def test_comando_permitido():
    assert SandboxComando.permitido("ls -la")
    assert SandboxComando.permitido("echo hola")
    assert not SandboxComando.permitido("rm -rf /")


def test_comando_toxic_rechazado():
    assert not SandboxComando.permitido("ls; rm -rf /")
    assert not SandboxComando.permitido("cat /etc/passwd | grep root")
    assert not SandboxComando.permitido("echo $HOME")


def test_comando_ejecutar_exitoso():
    r = SandboxComando.ejecutar("echo hola mundo")
    assert "hola mundo" in r


def test_comando_ejecutar_no_permitido():
    with pytest.raises(PermisoError):
        SandboxComando.ejecutar("rm -rf /")


# ─── FileSystemTool ──────────────────────────────────────────────────────────


def test_fs_leer_exitoso(_aislar):
    (_aislar / "test.txt").write_text("contenido")
    ft = FileSystemTool()
    r = ft.leer("test.txt")
    assert r.success
    assert r.output == "contenido"


def test_fs_leer_inexistente(_aislar):
    ft = FileSystemTool()
    r = ft.leer("no_existe.txt")
    assert not r.success
    assert "no encontrado" in r.error.lower()


def test_fs_escribir_y_listar(_aislar):
    ft = FileSystemTool()
    ft.escribir("a.txt", "AAA")
    ft.escribir("b.txt", "BBB")
    r = ft.listar()
    assert r.success
    assert "a.txt" in r.output
    assert "b.txt" in r.output


def test_fs_eliminar(_aislar):
    ft = FileSystemTool()
    ft.escribir("temp.txt", "tmp")
    assert ft.eliminar("temp.txt").success
    assert not ft.leer("temp.txt").success


def test_fs_fuera_de_workspace(_aislar):
    ft = FileSystemTool()
    r = ft.leer("../../../etc/passwd")
    assert not r.success
    assert "denegado" in r.error.lower()


def test_fs_escribir_subdirectorio(_aislar):
    ft = FileSystemTool()
    r = ft.escribir("sub/archivo.txt", "contenido")
    assert r.success


# ─── TerminalTool ────────────────────────────────────────────────────────────


def test_terminal_echo():
    r = TerminalTool.ejecutar("echo hola")
    assert r.success
    assert "hola" in r.output


def test_terminal_no_permitido():
    r = TerminalTool.ejecutar("rm -rf /")
    assert not r.success
    assert "permitido" in r.error.lower()


# ─── Acciones ────────────────────────────────────────────────────────────────


@pytest.fixture
def gestor(db_path):
    bc = BaseConocimiento(db_path)
    mt = MemoriaTrabajo(db_path)
    mt.iniciar_sesion()
    br = BaseReglas(db_path)
    return GestorAcciones(bc, mt, br)


def test_accion_leer_exitoso(gestor, _aislar):
    (_aislar / "test.txt").write_text("hola mundo")
    r = gestor.leer_archivo("lee test.txt")
    assert "hola mundo" in r


def test_accion_leer_sin_argumento(gestor):
    r = gestor.leer_archivo("lee")
    assert "usa" in r.lower()


def test_accion_escribir(gestor):
    r = gestor.escribir_archivo("escribe prueba.txt con contenido de prueba")
    assert "guardado" in r.lower() or "escritos" in r.lower()


def test_accion_listar(gestor, _aislar):
    (_aislar / "a.txt").touch()
    (_aislar / "b.txt").touch()
    r = gestor.listar_archivos("lista .")
    assert "a.txt" in r
    assert "b.txt" in r


def test_accion_ejecutar(gestor):
    r = gestor.ejecutar_comando("ejecuta echo hola mundo")
    assert "hola mundo" in r


def test_accion_ejecutar_no_permitido(gestor):
    r = gestor.ejecutar_comando("ejecuta rm -rf /")
    assert "permitido" in r.lower() or "error" in r.lower()


def test_accion_eliminar(gestor, _aislar):
    (_aislar / "temp.txt").write_text("x")
    r = gestor.eliminar_archivo("borra temp.txt")
    assert "eliminado" in r.lower()


def test_accion_herramientas(gestor):
    r = gestor.herramientas_disponibles("herramientas")
    assert "lee" in r
    assert "escribe" in r
    assert "ejecuta" in r


# ─── Loopy (integración) ─────────────────────────────────────────────────────


def test_loopy_lee_archivo(db_path, _aislar):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)
    loopy.iniciar()

    (_aislar / "test.txt").write_text("contenido de prueba")
    r = loopy.procesar("lee test.txt")
    assert r["regla"] == "leer_archivo"
    assert "contenido de prueba" in r["respuesta"]


def test_loopy_ejecuta_comando(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)
    loopy.iniciar()

    r = loopy.procesar("ejecuta echo hola")
    assert r["regla"] == "ejecutar_comando"
    assert "hola" in r["respuesta"]


def test_loopy_herramientas(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)
    loopy.iniciar()

    r = loopy.procesar("herramientas")
    assert r["regla"] == "herramientas_disponibles"
    assert "lee" in r["respuesta"]
