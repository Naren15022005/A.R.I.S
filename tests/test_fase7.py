import tempfile
from pathlib import Path

import pytest

from aris.habilidades import GeneradorHabilidades, RegistroHabilidades, Habilidad
from aris.acciones import GestorAcciones
from aris.conocimiento import BaseConocimiento
from aris.memoria import MemoriaTrabajo
from aris.reglas import BaseReglas
from aris.reglas_arranque import REGLAS_INICIALES
from aris.loopy import Loopy
from aris.config import DATA_DIR


@pytest.fixture(autouse=True)
def _aislar(monkeypatch, tmp_path):
    hab_dir = tmp_path / "habilidades"
    hab_dir.mkdir()
    monkeypatch.setattr("aris.habilidades.HABILIDADES_DIR", hab_dir)
    monkeypatch.setattr("aris.acciones._REG_HABILIDADES", None)
    return hab_dir


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def gestor(db_path):
    bc = BaseConocimiento(db_path)
    mt = MemoriaTrabajo(db_path)
    mt.iniciar_sesion()
    br = BaseReglas(db_path)
    return GestorAcciones(bc, mt, br)


# ─── GeneradorHabilidades ────────────────────────────────────────────────────


def test_generar_desde_prompt_exitoso():
    r = GeneradorHabilidades.generar_desde_prompt("crea una herramienta que salude en frances")
    assert r is not None
    desc, accion = r
    assert "salude en frances" in desc
    assert "salude" in accion


def test_generar_desde_prompt_sin_match():
    assert GeneradorHabilidades.generar_desde_prompt("hola") is None


def test_generar_codigo_valido():
    h = GeneradorHabilidades.generar("di hola en frances", "saludar_frances")
    assert h is not None
    assert h.accion == "saludar_frances"
    assert h.aprobada is False
    assert "def saludar_frances" in h.codigo
    assert GeneradorHabilidades.validar_sintaxis(h.codigo) is None


def test_generar_sin_accion():
    h = GeneradorHabilidades.generar("herramienta de prueba")
    assert h is not None
    assert h.accion


def test_generar_nombre_por_defecto():
    h = GeneradorHabilidades.generar("saluda al usuario")
    assert "saluda" in h.accion or "usuario" in h.accion


def test_validar_sintaxis_con_error():
    error = GeneradorHabilidades.validar_sintaxis("def broken(")
    assert error is not None


# ─── RegistroHabilidades ─────────────────────────────────────────────────────


def test_registro_crear_y_obtener(_aislar):
    reg = RegistroHabilidades()
    h = GeneradorHabilidades.generar("di hola", "saludar_test")
    assert reg.registrar(h)
    assert reg.obtener("saludar_test") is not None
    assert not reg.registrar(h)


def test_registro_no_duplica(_aislar):
    reg = RegistroHabilidades()
    h1 = GeneradorHabilidades.generar("test", "test_accion")
    h2 = GeneradorHabilidades.generar("test2", "test_accion")
    assert reg.registrar(h1)
    assert not reg.registrar(h2)


def test_registro_aprobacion(_aislar):
    reg = RegistroHabilidades()
    h = GeneradorHabilidades.generar("di hola", "saludar_aprobada")
    reg.registrar(h)
    assert not reg.obtener("saludar_aprobada").aprobada
    assert reg.aprobar("saludar_aprobada")
    assert reg.obtener("saludar_aprobada").aprobada


def test_registro_persistencia(_aislar):
    reg1 = RegistroHabilidades()
    h = GeneradorHabilidades.generar("hola test", "persistente")
    reg1.registrar(h)
    reg1.aprobar("persistente")

    reg2 = RegistroHabilidades()
    h2 = reg2.obtener("persistente")
    assert h2 is not None
    assert h2.aprobada
    assert h2.nombre == h.nombre


def test_registro_eliminar(_aislar):
    reg = RegistroHabilidades()
    h = GeneradorHabilidades.generar("test", "eliminar_test")
    reg.registrar(h)
    assert reg.eliminar("eliminar_test")
    assert reg.obtener("eliminar_test") is None


def test_registro_listar(_aislar):
    reg = RegistroHabilidades()
    reg.registrar(GeneradorHabilidades.generar("a", "acc_a"))
    reg.registrar(GeneradorHabilidades.generar("b", "acc_b"))
    assert len(reg.listar()) == 2


# ─── Ejecución dinámica ──────────────────────────────────────────────────────


CODIGO_TEST = '''
def test_accion(entrada, conocimiento, memoria, reglas):
    return "EJECUTADO: " + entrada
'''


def test_ejecucion_dinamica(_aislar):
    reg = RegistroHabilidades()
    h = Habilidad(
        id="test_dyn", nombre="Test Dinamico", accion="test_accion",
        descripcion="test", codigo=CODIGO_TEST, aprobada=True,
    )
    reg.registrar(h)
    reg.aprobar("test_accion")
    resultado = reg.ejecutar("test_accion", "hola mundo", None, None, None)
    assert resultado == "EJECUTADO: hola mundo"


def test_ejecucion_no_aprobada(_aislar):
    reg = RegistroHabilidades()
    h = Habilidad(
        id="test_noap", nombre="No Aprobada", accion="no_aprobada",
        descripcion="test", codigo=CODIGO_TEST, aprobada=False,
    )
    reg.registrar(h)
    assert reg.ejecutar("no_aprobada", "test", None, None, None) is None


def test_ejecucion_accion_inexistente(_aislar):
    reg = RegistroHabilidades()
    assert reg.ejecutar("no_existe", "test", None, None, None) is None


# ─── Acciones (integración) ──────────────────────────────────────────────────


def test_accion_crear_habilidad(gestor):
    r = gestor.crear_habilidad("crea una herramienta que salude en frances")
    assert "salude" in r.lower() or "generada" in r.lower() or "acción" in r
    assert "aprueba" in r


def test_accion_crear_sin_descripcion(gestor):
    r = gestor.crear_habilidad("crea")
    assert "usa" in r.lower()


def test_accion_aprobar_habilidad(gestor, _aislar):
    r1 = gestor.crear_habilidad("crea una herramienta que diga hola")
    reg = RegistroHabilidades()
    habs = reg.listar()
    if habs:
        accion = habs[0].accion
        r2 = gestor.aprobar_habilidad(f"aprueba {accion}")
        assert "aprobada" in r2.lower() or "activada" in r2.lower()


def test_accion_listar_habilidades(gestor, _aislar):
    reg = RegistroHabilidades()
    h = GeneradorHabilidades.generar("test listar", "test_listar_habs")
    reg.registrar(h)
    r = gestor.listar_habilidades("habilidades")
    assert "test_listar_habs" in r


def test_ejecutar_accion_desde_gestor(gestor, _aislar):
    from aris.acciones import _reg_habs, ejecutar_accion
    reg = _reg_habs()
    h = Habilidad(
        id="test_ges", nombre="Ges", accion="accion_gestor",
        descripcion="test", codigo=CODIGO_TEST, aprobada=True,
    )
    reg.registrar(h)
    reg.aprobar("accion_gestor")

    texto, _ = ejecutar_accion("accion_gestor", "test_input", None, None, None)
    assert "EJECUTADO" in texto


# ─── Loopy (integración) ─────────────────────────────────────────────────────


def test_loopy_crear_habilidad(db_path, _aislar):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)
    loopy.iniciar()

    r = loopy.procesar("crea una herramienta que salude en frances")
    assert r["regla"] == "crear_habilidad"
    assert "generada" in r["respuesta"].lower() or "acción" in r["respuesta"].lower()


def test_loopy_listar_habilidades_vacio(db_path, _aislar):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)
    loopy.iniciar()

    r = loopy.procesar("habilidades")
    assert r["regla"] == "listar_habilidades"
    assert "no hay" in r["respuesta"].lower() or "instaladas" in r["respuesta"].lower()
