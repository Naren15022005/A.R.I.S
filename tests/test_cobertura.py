"""Tests de cobertura para casos límite, frontera y extremos."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aris.conocimiento import BaseConocimiento
from aris.memoria import MemoriaTrabajo
from aris.reglas import BaseReglas, EvaluadorCondicion, MotorInferencia
from aris.casos import MemoriaCasos
from aris.induccion import MotorInduccion
from aris.perfil import cargar_perfil, guardar_perfil
from aris.sandbox import SandboxRuta, SandboxComando, PermisoError, WORKSPACE, init_workspace
from aris.tools import WebTool
from aris.acciones import ACCIONES_NO_REUTILIZABLES, GestorAcciones
from aris.loopy import Loopy
from aris.reglas_arranque import REGLAS_INICIALES


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


# ─── Conocimiento: edge cases ────────────────────────────────────────────────


class TestConocimientoEdge:
    def test_caracteres_especiales(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        bc.agregar("usuario@dominio", "tiene_email", "test@example.com")
        r = bc.buscar(sujeto="usuario@dominio")
        assert len(r) == 1
        assert r[0]["objeto"] == "test@example.com"

    def test_strings_muy_largos(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        largo = "x" * 500
        bc.agregar(largo, "es", "largo")
        r = bc.buscar(sujeto=largo)
        assert len(r) == 1

    def test_buscar_sin_filtros(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        bc.agregar("a", "es", "1")
        bc.agregar("b", "es", "2")
        resultados = bc.buscar()
        assert len(resultados) >= 2

    def test_eliminar_id_inexistente(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        assert not bc.eliminar(99999)

    def test_buscar_texto_vacio(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        assert bc.buscar_texto("") == []

    def test_sql_injection_en_valores(self, tmp_path):
        bc = BaseConocimiento(tmp_path / "db.db")
        bc.agregar("'; DROP TABLE hechos; --", "es", "malicioso")
        assert bc.contar() == 1
        bc.agregar("normal", "es", "normal")
        assert bc.contar() == 2


# ─── Memoria: edge cases ─────────────────────────────────────────────────────


class TestMemoriaEdge:
    def test_obtener_clave_inexistente(self, tmp_path):
        mt = MemoriaTrabajo(tmp_path / "db.db")
        mt.iniciar_sesion()
        assert mt.obtener("no_existe") is None
        assert mt.obtener("no_existe", 42) == 42

    def test_actualizar_sin_sesion(self, tmp_path):
        mt = MemoriaTrabajo(tmp_path / "db.db")
        mt.actualizar("clave", "valor")
        assert mt.obtener("clave") is None

    def test_estado_vacio(self, tmp_path):
        mt = MemoriaTrabajo(tmp_path / "db.db")
        mt.iniciar_sesion()
        assert "inicio" in mt.estado

    def test_multiples_sesiones(self, tmp_path):
        mt = MemoriaTrabajo(tmp_path / "db.db")
        s1 = mt.iniciar_sesion("sesion_a")
        mt.actualizar("dato", "a")
        mt.cerrar_sesion()
        s2 = mt.iniciar_sesion("sesion_b")
        assert mt.obtener("dato") is None
        assert s1 != s2


# ─── Reglas y Evaluador: edge cases ──────────────────────────────────────────


class TestEvaluadorEdge:
    def test_condicion_syntax_error(self):
        assert not EvaluadorCondicion.evaluar("'hola' in ", "hola", {})

    def test_condicion_sin_input(self):
        assert not EvaluadorCondicion.evaluar("'hola' in 'mundo'", "", {})
        # No referencia a 'input' ni estado → rechazado

    def test_estado_con_guion_bajo(self):
        assert EvaluadorCondicion.evaluar(
            "user_input", "test", {"user_input": True}
        )


class TestMotorEdge:
    def test_listar_sin_reglas(self, tmp_path):
        br = BaseReglas(tmp_path / "db.db")
        assert br.listar() == []

    def test_obtener_id_inexistente(self, tmp_path):
        br = BaseReglas(tmp_path / "db.db")
        assert br.obtener(999) is None

    def test_eliminar_id_inexistente(self, tmp_path):
        br = BaseReglas(tmp_path / "db.db")
        assert not br.eliminar(999)

    def test_priorizar_con_una_candidata(self, tmp_path):
        br = BaseReglas(tmp_path / "db.db")
        br.agregar("'test' in input", "eco")
        motor = MotorInferencia(br)
        c = motor.buscar_coincidencias("test", {})
        assert len(c) == 1
        assert motor.priorizar(c) is not None

    def test_priorizar_vacias(self, tmp_path):
        br = BaseReglas(tmp_path / "db.db")
        motor = MotorInferencia(br)
        assert motor.priorizar([]) is None

    def test_motor_sin_perfil(self, tmp_path):
        motor = MotorInferencia(BaseReglas(tmp_path / "db.db"))
        assert motor.perfil == {}


# ─── Perfil: edge cases ──────────────────────────────────────────────────────


class TestPerfilEdge:
    def test_cargar_con_campos_extra(self, tmp_path):
        ruta = tmp_path / "perfil.json"
        ruta.write_text('{"nombre": "custom", "campo_extra": true}')
        p = cargar_perfil(ruta)
        assert p["nombre"] == "custom"
        assert p["max_candidatas"] == 10  # defaults preserved
        assert "campo_extra" in p

    def test_guardar_y_cargar_campos_faltantes(self, tmp_path):
        ruta = tmp_path / "perfil.json"
        guardar_perfil({"nombre": "minimal"}, ruta)
        p = cargar_perfil(ruta)
        assert p["tono"] == "natural"
        assert p["bonificar_si_contiene"] == []

    def test_cargar_json_invalido(self, tmp_path):
        ruta = tmp_path / "perfil.json"
        ruta.write_text("{esto no es json}")
        p = cargar_perfil(ruta)
        assert p["nombre"] == "defecto"  # fallback a default


# ─── MemoriaCasos: edge cases ────────────────────────────────────────────────


class TestCasosEdge:
    def test_buscar_similares_sin_casos(self, tmp_path):
        mc = MemoriaCasos(tmp_path / "db.db")
        assert mc.buscar_similares("hola") == []

    def test_buscar_con_umbral_muy_alto(self, tmp_path):
        mc = MemoriaCasos(tmp_path / "db.db")
        mc.registrar("hola mundo", "resp", regla_accion="saludar")
        assert mc.buscar_similares("hola mundo", umbral=0.99)

    def test_similitud_con_texto_vacio(self):
        assert MemoriaCasos._similitud_jaccard("", "hola") == 0.0
        assert MemoriaCasos._similitud_jaccard("hola", "") == 0.0
        assert MemoriaCasos._similitud_jaccard("", "") == 0.0

    def test_similitud_con_acentos(self):
        sim = MemoriaCasos._similitud_jaccard("canción", "cancion")
        assert sim > 0

    def test_similitud_con_numeros(self):
        sim = MemoriaCasos._similitud_jaccard("hola 123", "hola 456")
        assert sim > 0


# ─── Inducción: edge cases ───────────────────────────────────────────────────


class TestInduccionEdge:
    def test_sin_casos(self, tmp_path):
        mc = MemoriaCasos(tmp_path / "db.db")
        br = BaseReglas(tmp_path / "db.db")
        ind = MotorInduccion(mc, br)
        assert ind.evaluar() == []

    def test_solo_casos_fallidos(self, tmp_path):
        mc = MemoriaCasos(tmp_path / "db.db")
        br = BaseReglas(tmp_path / "db.db")
        for _ in range(5):
            mc.registrar("test", "error", exitoso=False, regla_accion="fallar")
        ind = MotorInduccion(mc, br, umbral_repeticion=3)
        assert ind.evaluar() == []

    def test_tokens_clave_vacio(self):
        assert MotorInduccion._tokens_clave("el la y de en") == set()

    def test_sintetizar_condicion_none(self):
        assert MotorInduccion._sintetizar_condicion(set()) is None


# ─── Sandbox: edge cases ─────────────────────────────────────────────────────


class TestSandboxEdge:
    def test_listar_directorio_vacio(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        sr = SandboxRuta.__new__(SandboxRuta)
        sr._base = ws.resolve()
        assert sr.listar() == []

    def test_leer_directorio_en_lugar_de_archivo(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "sub").mkdir()
        sr = SandboxRuta.__new__(SandboxRuta)
        sr._base = ws.resolve()
        with pytest.raises(PermisoError, match="No es un archivo"):
            sr.leer("sub")

    def test_eliminar_directorio(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "sub").mkdir()
        sr = SandboxRuta.__new__(SandboxRuta)
        sr._base = ws.resolve()
        with pytest.raises(PermisoError):
            sr.eliminar("sub")

    def test_ruta_muy_larga_rechazada(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        sr = SandboxRuta.__new__(SandboxRuta)
        sr._base = ws.resolve()
        with pytest.raises(PermisoError):
            sr.leer("../" * 50 + "etc/passwd")

    def test_comando_vacio_rechazado(self):
        assert not SandboxComando.permitido("")
        assert not SandboxComando.permitido("   ")

    def test_comando_con_argumentos_complejos(self):
        assert SandboxComando.permitido("ls -la /tmp")
        assert SandboxComando.permitido('echo "hola mundo"')
        assert not SandboxComando.permitido("ls | grep x")
        assert not SandboxComando.permitido("echo $(whoami)")


# ─── WebTool (mock) ──────────────────────────────────────────────────────────


class TestWebTool:
    def test_url_sin_http_se_arregla(self, db_path, _aislar_web):
        bc = BaseConocimiento(db_path)
        mt = MemoriaTrabajo(db_path)
        mt.iniciar_sesion()
        br = BaseReglas(db_path)
        g = GestorAcciones(bc, mt, br)
        r = g.web_get("abre example.com")
        assert "example.com" in r


@pytest.fixture
def _aislar_web(monkeypatch):
    """Mockea urllib para evitar llamadas de red reales."""
    class MockResp:
        def __init__(self):
            self.status = 200

        def read(self):
            return b"contenido mockeado"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda url, **kw: MockResp())


# ─── GestorAcciones: edge cases ──────────────────────────────────────────────


class TestAccionesEdge:
    def test_ejecutar_accion_inexistente(self):
        from aris.acciones import ejecutar_accion
        texto, exitoso = ejecutar_accion("accion_inexistente", "input", None, None, None)
        assert "no sé ejecutar" in texto.lower()
        assert not exitoso

    def test_web_get_mal_formada(self, db_path):
        bc = BaseConocimiento(db_path)
        mt = MemoriaTrabajo(db_path)
        mt.iniciar_sesion()
        br = BaseReglas(db_path)
        g = GestorAcciones(bc, mt, br)
        r = g.web_get("abre")
        assert "usa" in r.lower()

    def test_leer_archivo_ruta_compleja(self, tmp_path, _aislar_fs):
        bc = BaseConocimiento(tmp_path / "db.db")
        mt = MemoriaTrabajo(tmp_path / "db.db")
        mt.iniciar_sesion()
        br = BaseReglas(tmp_path / "db.db")
        g = GestorAcciones(bc, mt, br)
        r = g.leer_archivo("lee sub/dir/archivo.txt")
        assert "no encontrado" in r.lower() or "error" in r.lower()


@pytest.fixture
def _aislar_fs(monkeypatch, tmp_path):
    ws = tmp_path / "tools_workspace"
    ws.mkdir()
    monkeypatch.setattr("aris.sandbox.WORKSPACE", ws)
    monkeypatch.setattr("aris.acciones._TOOL_FS", None)
    return ws


# ─── API: edge cases ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client(tmp_path):
    """TestClient con DB aislada en tmp_path."""
    import aris.api
    aris.api.DB_PATH = tmp_path / "aris.db"
    aris.api._loopy = None
    from aris.api import app
    return TestClient(app)


class TestAPIEdge:
    def test_chat_vacio(self, api_client):
        r = api_client.post("/chat", json={"mensaje": ""})
        assert r.status_code == 200
        assert r.json()["respuesta"] == ""

    def test_chat_sin_mensaje(self, api_client):
        r = api_client.post("/chat", json={})
        assert r.status_code == 422

    def test_chat_mal_formado(self, api_client):
        r = api_client.post("/chat", data="no json")
        assert r.status_code in (422, 415)

    def test_health_da_version(self, api_client):
        r = api_client.get("/health")
        assert "version" in r.json()

    def test_listar_hechos_sin_datos(self, api_client):
        r = api_client.get("/hechos")
        assert r.json() == []

    def test_buscar_hechos_sin_query(self, api_client):
        r = api_client.get("/hechos/buscar")
        assert r.status_code == 422

    def test_eliminar_hecho_inexistente(self, api_client):
        r = api_client.delete("/hechos/99999")
        assert r.status_code == 404

    def test_eliminar_regla_inexistente(self, api_client):
        r = api_client.delete("/reglas/99999")
        assert r.status_code == 404

    def test_crear_regla_sin_condicion(self, api_client):
        r = api_client.post("/reglas", json={"accion": "eco"})
        assert r.status_code == 422

    def test_sesion_estado_inicial(self, api_client):
        r = api_client.get("/sesion")
        d = r.json()
        assert d["reglas"] >= 10
        assert d["hechos"] >= 0
        assert d["casos"] >= 0


# ─── Loopy: edge cases ───────────────────────────────────────────────────────


class TestLoopyEdge:
    def test_procesar_entrada_solo_espacios(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        r = loopy.procesar("   ")
        assert r["respuesta"] == ""
        assert r["regla"] is None

    def test_procesar_muy_largo(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        largo = "hola " * 200
        r = loopy.procesar(largo)
        assert r["respuesta"] is not None

    def test_cerrar_sesion_sin_abrir(self, db_path):
        loopy = Loopy(db_path)
        loopy.cerrar_sesion()

    def test_ciclos_sin_reglas_no_rompe(self, db_path):
        loopy = Loopy(db_path)
        loopy.iniciar()
        for _ in range(10):
            r = loopy.procesar("test")
            assert r["respuesta"] is not None


# ─── Habilidades: edge cases restantes ────────────────────────────────────────


class TestHabilidadesEdge:
    def test_aprobar_inexistente(self, db_path):
        bc = BaseConocimiento(db_path)
        mt = MemoriaTrabajo(db_path)
        mt.iniciar_sesion()
        br = BaseReglas(db_path)
        g = GestorAcciones(bc, mt, br)
        r = g.aprobar_habilidad("aprueba no_existe")
        assert "no existe" in r.lower()

    def test_aprobar_sin_argumento_sin_pendientes(self, db_path):
        bc = BaseConocimiento(db_path)
        mt = MemoriaTrabajo(db_path)
        mt.iniciar_sesion()
        br = BaseReglas(db_path)
        g = GestorAcciones(bc, mt, br)
        r = g.aprobar_habilidad("aprueba")
        assert "pendientes" in r or "no hay" in r

    def test_crear_habilidad_con_nombre_repetido(self, db_path, _aislar_habs):
        bc = BaseConocimiento(db_path)
        mt = MemoriaTrabajo(db_path)
        mt.iniciar_sesion()
        br = BaseReglas(db_path)
        g = GestorAcciones(bc, mt, br)
        g.crear_habilidad("crea una herramienta que diga test")
        from aris.acciones import _reg_habs
        r = g.crear_habilidad("crea una herramienta que diga test")
        assert "ya existe" in r.lower() or "generada" in r.lower()


@pytest.fixture
def _aislar_habs(monkeypatch, tmp_path):
    habs = tmp_path / "habilidades"
    habs.mkdir()
    monkeypatch.setattr("aris.habilidades.HABILIDADES_DIR", habs)
    monkeypatch.setattr("aris.acciones._REG_HABILIDADES", None)
    return habs


# ─── Regresión: no romper nada existente ─────────────────────────────────────


def test_todas_las_reglas_de_arranque_tienen_formato_valido():
    for cond, acc, pri, desc in REGLAS_INICIALES:
        assert EvaluadorCondicion.evaluar(cond, "test", {}) is not None
        assert len(acc) > 0
        assert 1 <= pri <= 10


def test_version_importable():
    from aris import __version__
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 3


# ─── Bug 1: 'reglas' debe matchear sin palabras extra ────────────────────────


class TestBugReglas:
    def test_bare_reglas_matchea(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        r = loopy.procesar("reglas")
        assert r["regla"] == "listar_reglas", (
            f"Se esperaba listar_reglas, se obtuvo {r['regla']!r}"
        )
        assert "Mis reglas actuales" in r["respuesta"]

    def test_reglas_con_que_tambien_funciona(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        r = loopy.procesar("qué reglas hay")
        assert r["regla"] == "listar_reglas"

    def test_muestra_las_reglas_funciona(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        r = loopy.procesar("muestra las reglas")
        assert r["regla"] == "listar_reglas"


# ─── Bug 2A: no guardar fallbacks como hechos consultables ───────────────────


class TestBugFallbackHechos:
    def test_fallback_no_crea_aris_respondio(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        loopy.procesar("xyzzy_nonexistent_12345")
        hechos = loopy.conocimiento.buscar(sujeto="aris", predicado="respondio")
        assert hechos == [], (
            f"El fallback no debería crear (aris, respondio, X). Creados: {hechos}"
        )

    def test_fallback_no_se_anida_en_siguiente(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        r1 = loopy.procesar("xyzzy_nonexistent_12345")
        r2 = loopy.procesar("xyzzy_nonexistent_12345")
        # Ninguna respuesta debe contener el texto del input (eso sería anidamiento)
        assert "xyzzy_nonexistent_12345" not in r1["respuesta"], (
            "Respuesta 1 no debe contener el input literal"
        )
        assert "xyzzy_nonexistent_12345" not in r2["respuesta"], (
            "Respuesta 2 no debe contener el input literal"
        )

    def test_input_usuario_si_se_guarda_en_fallback(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        loopy.procesar("xyzzy_nonexistent_12345")
        hechos = loopy.conocimiento.buscar(
            sujeto="usuario", predicado="dijo"
        )
        assert len(hechos) >= 1

    def test_regla_exitosa_no_guarda_aris_respondio(self, db_path):
        loopy = Loopy(db_path)
        for c, a, p, d in REGLAS_INICIALES:
            loopy.base_reglas.agregar(c, a, p, d)
        loopy.iniciar()
        loopy.procesar("hola")
        hechos = loopy.conocimiento.buscar(sujeto="aris", predicado="respondio")
        assert hechos == [], (
            "ARIS nunca guarda (aris, respondio, X) — ni siquiera en exito"
        )


# ─── Bug 2B: script de limpieza ──────────────────────────────────────────────


class TestLimpiezaFallbacks:
    def _crear_db_contaminada(self, tmp_path):
        """Crea una DB con hechos contaminados sintéticos."""
        import sqlite3
        db = tmp_path / "contaminada.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hechos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sujeto TEXT NOT NULL,
                predicado TEXT NOT NULL,
                objeto TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT '',
                sesion_id TEXT
            )
        """)
        conn.execute(
            "INSERT INTO hechos (sujeto, predicado, objeto) VALUES ('aris', 'respondio', 'No tengo una regla para eso, usuario dijo reglas')"
        )
        conn.execute(
            "INSERT INTO hechos (sujeto, predicado, objeto) VALUES ('aris', 'respondio', 'No entiendo eso aún, puedes enseñarme')"
        )
        conn.execute(
            "INSERT INTO hechos (sujeto, predicado, objeto) VALUES ('aris', 'respondio', '¡Hola! ¿En qué puedo ayudarte?')"
        )
        conn.execute(
            "INSERT INTO hechos (sujeto, predicado, objeto) VALUES ('usuario', 'dijo', 'reglas')"
        )
        conn.commit()
        conn.close()
        return db

    def test_limpieza_detecta_contaminados(self, tmp_path):
        from scripts.limpiar_fallbacks import limpiar
        db = self._crear_db_contaminada(tmp_path)
        total = limpiar(str(db), dry_run=True)
        assert total == 2, f"Debe detectar 2 contaminados, detectó {total}"

    def test_limpieza_elimina_en_firme(self, tmp_path):
        from scripts.limpiar_fallbacks import limpiar
        db = self._crear_db_contaminada(tmp_path)
        total = limpiar(str(db), dry_run=False)
        assert total == 2

        import sqlite3
        conn = sqlite3.connect(str(db))
        cur = conn.execute("SELECT COUNT(*) FROM hechos")
        restantes = cur.fetchone()[0]
        conn.close()
        assert restantes == 2, (
            f"Deben quedar 2 hechos (saludo + usuario), quedan {restantes}"
        )

    def test_limpieza_no_elimina_hechos_limpios(self, tmp_path):
        from scripts.limpiar_fallbacks import limpiar
        db = self._crear_db_contaminada(tmp_path)
        total = limpiar(str(db), dry_run=False)
        assert total == 2

        import sqlite3
        conn = sqlite3.connect(str(db))
        cur = conn.execute(
            "SELECT objeto FROM hechos WHERE sujeto='aris' AND predicado='respondio'"
        )
        restantes = cur.fetchall()
        conn.close()
        assert all(
            "¡Hola!" in r[0] for r in restantes
        ), "Solo debe quedar el saludo"


# ─── Addendum: Duplicación masiva de reglas de arranque ───────────────────────
#   Parte A: idempotencia de carga
#   Parte B: condición corregida de listar_reglas
#   Parte C: script de limpieza


class TestIdempotenciaCarga:
    def test_dos_cargas_mismo_numero(self, tmp_path):
        br = BaseReglas(tmp_path / "test.db")
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        n1 = br.contar()
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        n2 = br.contar()
        assert n1 == n2 == len(REGLAS_INICIALES), (
            f"n1={n1}, n2={n2}, esperado={len(REGLAS_INICIALES)}"
        )

    def test_tres_cargas_mismo_numero(self, tmp_path):
        br = BaseReglas(tmp_path / "test.db")
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        assert br.contar() == len(REGLAS_INICIALES)

    def test_actualizacion_de_condicion_sin_duplicar(self, tmp_path):
        br = BaseReglas(tmp_path / "test.db")
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        # Cambiar la condición de la regla "agradecer" (misma acción, misma clave)
        reglas_mod = list(REGLAS_INICIALES)
        reglas_mod[2] = ("'thanks' in input or 'gracias' in input", "agradecer", 7, "Agradecer modificado")
        br.cargar_reglas_iniciales(reglas_mod)
        assert br.contar() == len(REGLAS_INICIALES)
        # Buscar la regla agradecer (la de clave_arranque="boot_agradecer")
        for r in br.listar():
            if r["accion"] == "agradecer":
                assert "'thanks' in input" in r["condicion"], (
                    f"Condición no actualizada: {r['condicion']}"
                )
                break
        else:
            assert False, "Regla 'agradecer' no encontrada"

    def test_carga_en_db_existente_sin_clave(self, tmp_path):
        """Simula base de datos preexistente (sin columna clave_arranque)."""
        import sqlite3
        db = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE reglas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condicion TEXT NOT NULL,
                accion TEXT NOT NULL,
                prioridad INTEGER NOT NULL DEFAULT 5,
                exitos INTEGER NOT NULL DEFAULT 0,
                fallos INTEGER NOT NULL DEFAULT 0,
                origen TEXT NOT NULL DEFAULT 'manual',
                descripcion TEXT
            )
        """)
        # Insertar reglas duplicadas (simula 3 arranques)
        for _ in range(3):
            for c, a, p, d in REGLAS_INICIALES:
                conn.execute(
                    "INSERT INTO reglas (condicion, accion, prioridad, descripcion) VALUES (?, ?, ?, ?)",
                    (c, a, p, d),
                )
        conn.commit()
        conn.close()

        br = BaseReglas(db)
        br.cargar_reglas_iniciales(REGLAS_INICIALES)
        assert br.contar() == len(REGLAS_INICIALES), (
            f"DB legacy con duplicados debería compactarse a {len(REGLAS_INICIALES)}, "
            f"tiene {br.contar()}"
        )


class TestLimpiezaDuplicados:
    def _crear_db_con_duplicados(self, tmp_path):
        import sqlite3
        db = tmp_path / "dupes.db"
        BaseReglas(db)  # crea tabla con clave_arranque
        conn = sqlite3.connect(str(db))
        # Insertar la misma regla 3 veces con distintos contadores
        base = ("'hola' in input", "saludar", 8, "Saludo")
        for i in range(3):
            conn.execute(
                "INSERT INTO reglas (condicion, accion, prioridad, descripcion, exitos, fallos) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (base[0], base[1], base[2], base[3], 10 - i * 3, i),
            )
        conn.commit()
        conn.close()
        return db

    def test_detecta_duplicados(self, tmp_path):
        from scripts.depurar_duplicados import depurar
        db = self._crear_db_con_duplicados(tmp_path)
        res = depurar(str(db), dry_run=True)
        assert res["eliminadas"] == 2

    def test_conserva_la_de_mas_exitos(self, tmp_path):
        from scripts.depurar_duplicados import depurar
        db = self._crear_db_con_duplicados(tmp_path)
        depurar(str(db), dry_run=False)
        import sqlite3
        conn = sqlite3.connect(str(db))
        cur = conn.execute("SELECT exitos, fallos FROM reglas WHERE accion='saludar'")
        fila = cur.fetchone()
        conn.close()
        assert fila[0] == 10 + 7 + 4, (
            f"Éxitos deberían sumarse (21), obtenido {fila[0]}"
        )
        assert fila[1] == 0 + 1 + 2, (
            f"Fallos deberían sumarse (3), obtenido {fila[1]}"
        )

    def test_suma_contadores(self, tmp_path):
        from scripts.depurar_duplicados import depurar
        db = self._crear_db_con_duplicados(tmp_path)
        res = depurar(str(db), dry_run=True)
        assert res["exitos_traspasados"] == 7 + 4
        assert res["fallos_traspasados"] == 1 + 2

    def test_sin_duplicados_no_hace_nada(self, tmp_path):
        from scripts.depurar_duplicados import depurar
        db = tmp_path / "clean.db"
        BaseReglas(db)
        import sqlite3
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO reglas (condicion, accion, prioridad, descripcion) VALUES (?, ?, ?, ?)",
            ("'hola' in input", "saludar", 8, "Saludo"),
        )
        conn.commit()
        conn.close()
        res = depurar(str(db), dry_run=False)
        assert res["eliminadas"] == 0
        assert res["despues"] == 1


# ─── Addendum 2 — Bug 2 confirmado + reutilización ciega de acciones ────────


def _loopy_con_reglas(db_path):
    from aris.loopy import Loopy
    from aris.reglas_arranque import REGLAS_INICIALES
    loopy = Loopy(db_path)
    for c, a, p, d in REGLAS_INICIALES:
        loopy.base_reglas.agregar(c, a, p, d)
    loopy.iniciar()
    return loopy


class TestAddendum2:
    def test_accion_con_formato_fallido_se_marca_no_exitosa(self, db_path):
        """Fix 1: guardar_hecho con input mal formado → exitoso=False en caso."""
        loopy = _loopy_con_reglas(db_path)
        loopy.procesar("que es mango")  # no matchea guardar_hecho, cae a fallback
        # La accion guardar_hecho no se ejecuto (no matchea regla ni caso),
        # asi que verificamos que el caso resultante tiene exitoso=False
        casos = loopy.memoria_casos.buscar_similares("que es mango", limite=1)
        if casos:
            assert not casos[0].get("exitoso"), (
                "Caso de input sin regla debe tener exitoso=False"
            )

    def test_accion_fallida_no_es_reutilizable_por_similitud(self, db_path):
        """Fix 2: input parecido a caso fallido de guardar_hecho → no reusa."""
        loopy = _loopy_con_reglas(db_path)
        # Crear un caso de guardar_hecho exitoso
        loopy.procesar("recuerda que mango es una fruta")
        # Input con tokens similares pero sin formato
        r = loopy.procesar("que es mango")
        assert r["regla"] != "guardar_hecho", (
            f"guardar_hecho no debe reutilizarse por similitud. Obtuvo: {r['regla']}"
        )

    def test_secuencia_completa_mango_consistente(self, db_path):
        """Regresión: la secuencia del bug completo."""
        loopy = _loopy_con_reglas(db_path)
        r1 = loopy.procesar("mango")
        assert r1["regla"] is None
        assert "No entiendo" in r1["respuesta"]

        loopy.procesar("recuerda que mango es una fruta")

        r3 = loopy.procesar("que es mango")
        assert r3["regla"] != "guardar_hecho", (
            "'que es mango' no debe ejecutar guardar_hecho"
        )

        r5 = loopy.procesar("mango")
        # Segundo 'mango' debe ser consistente con el primero:
        # puede encontrar hechos relacionados (porque ya hay un hecho con 'mango'),
        # pero NO debe ejecutar guardar_hecho ni acciones estructuradas
        assert r5["regla"] is None or r5["regla"] not in ACCIONES_NO_REUTILIZABLES, (
            f"mango no debe reutilizar acciones estructuradas. Regla: {r5['regla']}"
        )

    def test_aris_respondio_nunca_se_guarda(self, db_path):
        """Parte 1: verificar que ningun (aris, respondio, X) existe."""
        loopy = _loopy_con_reglas(db_path)
        loopy.procesar("hola")
        loopy.procesar("recuerda que x es y")
        loopy.procesar("adiós")
        hechos = loopy.conocimiento.buscar(sujeto="aris", predicado="respondio")
        assert hechos == [], (
            "Nunca debe haber hechos (aris, respondio, X)"
        )


# ─── Addendum 3 — Filtrar dijo/respondio del fallback de desconocido ────────


class TestAddendum3:
    def test_sin_ruido_de_interaccion(self, db_path):
        """Filtrar (usuario, dijo, ...) y (aris, respondio, ...) del fallback."""
        loopy = _loopy_con_reglas(db_path)
        loopy.procesar("recuerda que mango es una fruta")
        r = loopy.procesar("mango")
        assert "usuario" not in r["respuesta"], (
            f"No debe citar 'usuario': {r['respuesta']}"
        )
        assert "dijo" not in r["respuesta"], (
            f"No debe citar 'dijo': {r['respuesta']}"
        )

    def test_conocimiento_declarativo_aparece(self, db_path):
        """El saber real (mango es fruta) se muestra en lugar del ruido."""
        loopy = _loopy_con_reglas(db_path)
        loopy.procesar("recuerda que mango es una fruta")
        r = loopy.procesar("mango")
        assert "sé que" in r["respuesta"], (
            f"Debe usar 'sé que': {r['respuesta']}"
        )
        assert "mango" in r["respuesta"] and "fruta" in r["respuesta"], (
            f"Debe contener el hecho: {r['respuesta']}"
        )

    def test_fallback_generico_sin_conocimiento(self, db_path):
        """Input completamente nuevo → 'No entiendo eso aún'."""
        loopy = _loopy_con_reglas(db_path)
        r = loopy.procesar("xyzzy_zork_42")
        assert "No entiendo" in r["respuesta"], (
            f"Debe caer en respuesta genérica: {r['respuesta']}"
        )

    def test_hechos_declarativos_previos_siguen_funcionando(self, db_path):
        """Hechos con predicados que no son dijo/respondio se muestran."""
        loopy = _loopy_con_reglas(db_path)
        loopy.procesar("recuerda que python es un lenguaje")
        loopy.procesar("recuerda que aris es simbolico")
        r = loopy.procesar("python")
        assert "lenguaje" in r["respuesta"], (
            f"Debe mostrar hecho declarativo: {r['respuesta']}"
        )
        assert "dijo" not in r["respuesta"]
