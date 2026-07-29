import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("aris.conocimiento")
pytest.importorskip("aris.reglas")
pytest.importorskip("aris.loopy")

from aris.conocimiento import BaseConocimiento
from aris.memoria import MemoriaTrabajo
from aris.reglas import BaseReglas, EvaluadorCondicion, MotorInferencia
from aris.acciones import GestorAcciones
from aris.loopy import Loopy
from aris.reglas_arranque import REGLAS_INICIALES



@pytest.fixture
def db_path():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        yield Path(tmp) / "test_aris.db"



# ─── BaseConocimiento ────────────────────────────────────────────────────────


def test_conocimiento_agregar_y_buscar(db_path):
    bc = BaseConocimiento(db_path)
    hecho_id = bc.agregar("Sócrates", "es", "humano")
    assert hecho_id is not None
    assert bc.contar() == 1

    resultados = bc.buscar(sujeto="Sócrates")
    assert len(resultados) == 1
    assert resultados[0]["objeto"] == "humano"

    resultados = bc.buscar(predicado="es")
    assert len(resultados) >= 1


def test_conocimiento_buscar_texto(db_path):
    bc = BaseConocimiento(db_path)
    bc.agregar("Gato", "es", "mamífero")
    bc.agregar("Perro", "es", "mamífero")
    bc.agregar("Gato", "come", "pescado")

    resultados = bc.buscar_texto("Gato")
    assert len(resultados) == 2

    resultados = bc.buscar_texto("mamífero")
    assert len(resultados) == 2


def test_conocimiento_eliminar(db_path):
    bc = BaseConocimiento(db_path)
    hecho_id = bc.agregar("X", "es", "Y")
    assert bc.eliminar(hecho_id)
    assert bc.contar() == 0


def test_conocimiento_sin_resultados(db_path):
    bc = BaseConocimiento(db_path)
    assert bc.buscar(sujeto="inexistente") == []


# ─── MemoriaTrabajo ──────────────────────────────────────────────────────────


def test_memoria_iniciar_y_actualizar(db_path):
    mt = MemoriaTrabajo(db_path)
    sid = mt.iniciar_sesion()
    assert sid is not None
    assert len(sid) > 0

    mt.actualizar("clave1", "valor1")
    assert mt.obtener("clave1") == "valor1"

    mt.actualizar("edad", 25)
    assert mt.obtener("edad") == 25

    estado = mt.estado
    assert estado["clave1"] == "valor1"
    assert estado["edad"] == 25


def test_memoria_cerrar_sesion(db_path):
    mt = MemoriaTrabajo(db_path)
    mt.iniciar_sesion()
    mt.actualizar("x", 1)
    mt.cerrar_sesion()
    assert mt.obtener("x") is None
    assert mt.sesion_id is None


def test_memoria_sesion_id_personalizado(db_path):
    mt = MemoriaTrabajo(db_path)
    sid = mt.iniciar_sesion("mi-sesion-test")
    assert sid == "mi-sesion-test"
    assert mt.sesion_id == "mi-sesion-test"


# ─── EvaluadorCondicion ──────────────────────────────────────────────────────


def test_evaluador_condicion_simple():
    assert EvaluadorCondicion.evaluar("'hola' in input", "hola mundo", {})
    assert not EvaluadorCondicion.evaluar("'hola' in input", "adios mundo", {})

def test_evaluador_condicion_con_estado():
    estado = {"tiene_permiso": True}
    assert EvaluadorCondicion.evaluar("tiene_permiso", "cualquier cosa", estado)

def test_evaluador_condicion_sql_injection_protegida():
    assert not EvaluadorCondicion.evaluar("1 == 1", "entrada maliciosa", {})


# ─── BaseReglas ──────────────────────────────────────────────────────────────


def test_reglas_agregar_y_listar(db_path):
    br = BaseReglas(db_path)
    rid = br.agregar("'test' in input", "eco", prioridad=5, descripcion="Regla de prueba")
    assert rid is not None
    assert br.contar() == 1

    reglas = br.listar()
    assert len(reglas) == 1
    assert reglas[0]["descripcion"] == "Regla de prueba"


def test_reglas_obtener_y_eliminar(db_path):
    br = BaseReglas(db_path)
    rid = br.agregar("'algo' in input", "eco")
    regla = br.obtener(rid)
    assert regla is not None
    assert regla["accion"] == "eco"

    assert br.eliminar(rid)
    assert br.obtener(rid) is None


def test_reglas_contadores(db_path):
    br = BaseReglas(db_path)
    rid = br.agregar("'x' in input", "eco")
    br.actualizar_exito(rid)
    br.actualizar_exito(rid)
    br.actualizar_fallo(rid)

    regla = br.obtener(rid)
    assert regla["exitos"] == 2
    assert regla["fallos"] == 1


# ─── PerfilRazonamiento ──────────────────────────────────────────────────────


from aris.perfil import cargar_perfil, guardar_perfil, PERFIL_DEFAULT


def test_perfil_cargar_sin_archivo(tmp_path):
    ruta = tmp_path / "no_existe.json"
    perfil = cargar_perfil(ruta)
    assert perfil["nombre"] == "defecto"
    assert perfil["max_candidatas"] == 10


def test_perfil_guardar_y_cargar(tmp_path):
    ruta = tmp_path / "perfil.json"
    perfil = {"nombre": "test", "bonificar_si_contiene": ["saludar"]}
    guardar_perfil(perfil, ruta)
    cargado = cargar_perfil(ruta)
    assert cargado["nombre"] == "test"
    assert "saludar" in cargado["bonificar_si_contiene"]


def test_perfil_default_no_sobrescribe_existentes(tmp_path):
    ruta = tmp_path / "perfil.json"
    guardar_perfil({"nombre": "test"}, ruta)
    cargado = cargar_perfil(ruta)
    assert cargado["nombre"] == "test"
    assert cargado["max_candidatas"] == 10
    assert cargado["tono"] == "natural"


# ─── MotorInferencia con perfil ──────────────────────────────────────────────


def test_motor_perfil_bonifica_accion(db_path):
    br = BaseReglas(db_path)
    br.agregar("'test' in input", "saludar", prioridad=5)
    br.agregar("'test' in input", "listar_reglas", prioridad=5)
    perfil = {"bonificar_si_contiene": ["saludar"]}
    motor = MotorInferencia(br, perfil=perfil)

    candidatas = motor.buscar_coincidencias("test", {})
    assert len(candidatas) == 2
    ganadora = motor.priorizar(candidatas)
    assert ganadora["accion"] == "saludar"


def test_motor_perfil_penaliza_accion(db_path):
    br = BaseReglas(db_path)
    br.agregar("'test' in input", "saludar", prioridad=5)
    br.agregar("'test' in input", "despedir", prioridad=5)
    perfil = {"penalizar_si_contiene": ["saludar"]}
    motor = MotorInferencia(br, perfil=perfil)

    candidatas = motor.buscar_coincidencias("test", {})
    ganadora = motor.priorizar(candidatas)
    assert ganadora["accion"] == "despedir"


def test_motor_perfil_bonifica_vence_a_prioridad(db_path):
    br = BaseReglas(db_path)
    br.agregar("'test' in input", "baja_pero_bonificada", prioridad=1)
    br.agregar("'test' in input", "alta_sin_bonus", prioridad=10)
    perfil = {"bonificar_si_contiene": ["baja_pero_bonificada"]}
    motor = MotorInferencia(br, perfil=perfil)

    candidatas = motor.buscar_coincidencias("test", {})
    ganadora = motor.priorizar(candidatas)
    assert ganadora["accion"] == "baja_pero_bonificada"


def test_motor_perfil_sin_efecto_si_no_coincide(db_path):
    br = BaseReglas(db_path)
    br.agregar("'test' in input", "accion_a", prioridad=8)
    br.agregar("'test' in input", "accion_b", prioridad=3)
    perfil = {"bonificar_si_contiene": ["inexistente"]}
    motor = MotorInferencia(br, perfil=perfil)

    candidatas = motor.buscar_coincidencias("test", {})
    ganadora = motor.priorizar(candidatas)
    assert ganadora["accion"] == "accion_a"


def test_loopy_con_perfil_personalizado(db_path):
    perfil = {"bonificar_si_contiene": ["despedir"]}
    loopy = Loopy(db_path, perfil=perfil)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()
    loopy.procesar("hola")
    r = loopy.procesar("adiós")
    assert r["regla"] == "despedir"


# ─── MotorInferencia ─────────────────────────────────────────────────────────


def test_motor_inferencia_coincidencia(db_path):
    br = BaseReglas(db_path)
    br.agregar("'hola' in input", "saludar", prioridad=8)
    motor = MotorInferencia(br)

    candidatas = motor.buscar_coincidencias("hola mundo", {})
    assert len(candidatas) == 1
    assert candidatas[0]["accion"] == "saludar"

    # Priorización
    ganadora = motor.priorizar(candidatas)
    assert ganadora is not None
    assert ganadora["accion"] == "saludar"


def test_motor_inferencia_sin_coincidencias(db_path):
    br = BaseReglas(db_path)
    br.agregar("'hola' in input", "saludar")
    motor = MotorInferencia(br)

    candidatas = motor.buscar_coincidencias("adios", {})
    assert len(candidatas) == 0
    assert motor.priorizar(candidatas) is None


def test_motor_inferencia_prioridad(db_path):
    br = BaseReglas(db_path)
    br.agregar("'test' in input", "baja", prioridad=1)
    br.agregar("'test' in input", "alta", prioridad=10)
    motor = MotorInferencia(br)

    candidatas = motor.buscar_coincidencias("test", {})
    assert len(candidatas) == 2
    ganadora = motor.priorizar(candidatas)
    assert ganadora["accion"] == "alta"


# ─── GestorAcciones ──────────────────────────────────────────────────────────


@pytest.fixture
def gestor(db_path):
    bc = BaseConocimiento(db_path)
    mt = MemoriaTrabajo(db_path)
    mt.iniciar_sesion()
    br = BaseReglas(db_path)
    return GestorAcciones(bc, mt, br)


def test_saludar(gestor):
    r = gestor.saludar("hola")
    assert "hola" in r.lower() or "Hola" in r or "Hey" in r or "¡Qué tal" in r


def test_despedir(gestor):
    r = gestor.despedir("adiós")
    assert any(p in r.lower() for p in ("hasta", "adiós", "cuídate", "nos vemos"))


def test_presentarse(gestor):
    r = gestor.presentarse("quién eres")
    assert "ARIS" in r
    assert "simbólico" in r


def test_agradecer(gestor):
    assert "nada" in gestor.agradecer("gracias").lower()


def test_guardar_hecho(gestor):
    r = gestor.guardar_hecho("recuerda que Sócrates es humano")
    assert "Sócrates" in r
    assert "humano" in r

    hechos = gestor.conocimiento.buscar(sujeto="Sócrates")
    assert len(hechos) == 1
    assert hechos[0]["objeto"] == "humano"


def test_consultar_hecho(gestor):
    gestor.conocimiento.agregar("Aristóteles", "es", "filósofo")
    r = gestor.consultar_hecho("qué sabes de Aristóteles")
    assert "Aristóteles" in r
    assert "filósofo" in r


def test_consultar_hecho_sin_resultado(gestor):
    r = gestor.consultar_hecho("qué sabes de Platón")
    assert "Platón" in r
    assert "no sé" in r.lower()


def test_ayuda(gestor):
    r = gestor.mostrar_ayuda("ayuda")
    assert "hola" in r.lower()
    assert "adiós" in r.lower()
    assert "recuerda" in r.lower()


# ─── Loopy (ciclo completo) ──────────────────────────────────────────────────


def test_loopy_ciclo_completo(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()

    r = loopy.procesar("hola")
    assert r["respuesta"] is not None
    assert r["regla"] == "saludar"
    assert loopy.conocimiento.contar() >= 1

    r = loopy.procesar("adiós")
    assert r["regla"] == "despedir"


def test_loopy_input_desconocido(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()
    r = loopy.procesar("xyzzy_que_no_existe")
    assert r["regla"] is None
    assert "no entiendo" in r["respuesta"].lower()


def test_loopy_ensenanza_y_recuerdo(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()

    r1 = loopy.procesar("recuerda que ARIS es agente")
    assert r1["regla"] == "guardar_hecho"
    assert loopy.conocimiento.contar() >= 2

    r2 = loopy.procesar("qué sabes de ARIS")
    assert r2["regla"] == "consultar_hecho"
    assert "ARIS" in r2["respuesta"]
    assert "agente" in r2["respuesta"]


def test_loopy_memoria_contador(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()

    loopy.procesar("hola")
    assert loopy.memoria_trabajo.obtener("contador") == 1
    loopy.procesar("hola")
    assert loopy.memoria_trabajo.obtener("contador") == 2


def test_loopy_sin_reglas(db_path):
    loopy = Loopy(db_path)
    loopy.iniciar()
    r = loopy.procesar("hola")
    assert r["respuesta"] is not None
    assert r["regla"] is None


def test_loopy_input_vacio(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()
    r = loopy.procesar("")
    assert r["respuesta"] == ""


# ─── Reglas de arranque ──────────────────────────────────────────────────────


def test_reglas_iniciales_tienen_todo():
    for cond, acc, pri, desc in REGLAS_INICIALES:
        assert isinstance(cond, str), f"Falta condición en {acc}"
        assert isinstance(acc, str), f"Falta nombre de acción en {cond}"
        assert isinstance(pri, int), f"Prioridad no es int en {acc}"
        assert isinstance(desc, str), f"Falta descripción en {acc}"


# ─── Fase 2: MemoriaCasos ────────────────────────────────────────────────────


from aris.casos import MemoriaCasos


def test_casos_registrar_y_contar(db_path):
    mc = MemoriaCasos(db_path)
    cid = mc.registrar("hola", "¡Hola!", regla_id=1, regla_accion="saludar")
    assert cid is not None
    assert mc.contar() == 1
    assert mc.contar_exitosos() == 1


def test_casos_registrar_fallido(db_path):
    mc = MemoriaCasos(db_path)
    mc.registrar("xyz", "no entiendo", exitoso=False)
    assert mc.contar() == 1
    assert mc.contar_exitosos() == 0


def test_casos_similitud_jaccard():
    assert MemoriaCasos._similitud_jaccard("hola mundo", "hola mundo") == 1.0
    assert MemoriaCasos._similitud_jaccard("hola mundo", "adiós mundo") > 0
    assert MemoriaCasos._similitud_jaccard("hola", "adiós") == 0.0
    assert MemoriaCasos._similitud_jaccard("", "hola") == 0.0


def test_casos_buscar_similares(db_path):
    mc = MemoriaCasos(db_path)
    mc.registrar("hola cómo estás", "¡Hola!", regla_accion="saludar")
    mc.registrar("dime la hora", "son las 3", regla_accion="decir_hora")
    mc.registrar("hola buenos días", "Buenos días", regla_accion="saludar")

    similares = mc.buscar_similares("hola qué tal", umbral=0.2)
    assert len(similares) >= 1
    assert similares[0]["regla_accion"] == "saludar"


def test_casos_buscar_similares_sin_coincidencia(db_path):
    mc = MemoriaCasos(db_path)
    mc.registrar("esto es una prueba", "ok", regla_accion="eco")
    similares = mc.buscar_similares("xyzzy completamente diferente", umbral=0.5)
    assert len(similares) == 0


def test_casos_solo_exitosos(db_path):
    mc = MemoriaCasos(db_path)
    mc.registrar("hola", "respuesta", regla_accion="saludar", exitoso=True)
    mc.registrar("fallo", "error", regla_accion="fallar", exitoso=False)

    similares = mc.buscar_similares("hola", solo_exitosos=True)
    assert len(similares) == 1
    assert similares[0]["regla_accion"] == "saludar"


def test_loopy_usa_casos_cuando_no_hay_regla(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()

    loopy.procesar("dime la hora por favor")
    assert loopy.memoria_casos.contar() >= 1

    loopy.base_reglas.agregar("'hora' in input", "eco", prioridad=100)
    loopy.base_reglas.eliminar(1)
    loopy.base_reglas.eliminar(2)
    loopy.base_reglas.eliminar(3)
    loopy.base_reglas.eliminar(4)
    loopy.base_reglas.eliminar(5)

    r = loopy.procesar("dime la hora exacta por favor")
    assert r["respuesta"] is not None


# ─── Fase 3: MotorInduccion ──────────────────────────────────────────────────


from aris.induccion import MotorInduccion


def test_induccion_tokens_clave():
    tokens = MotorInduccion._tokens_clave("hola cómo estás amigo")
    assert "hola" in tokens
    assert "amigo" in tokens
    assert "cómo" not in tokens
    assert "estás" not in tokens


def test_induccion_sintetizar_condicion_simple():
    cond = MotorInduccion._sintetizar_condicion({"hola", "mundo"})
    assert "hola" in cond
    assert "mundo" in cond
    assert "and" in cond


def test_induccion_sintetizar_condicion_un_token():
    cond = MotorInduccion._sintetizar_condicion({"hola"})
    assert cond == "'hola' in input"


def test_induccion_no_genera_con_pocos_casos(db_path):
    mc = MemoriaCasos(db_path)
    br = BaseReglas(db_path)
    inductor = MotorInduccion(mc, br, umbral_repeticion=3)

    mc.registrar("hola amigo", "saludo", regla_accion="saludar")
    mc.registrar("hola colega", "saludo", regla_accion="saludar")

    resultado = inductor.evaluar()
    assert len(resultado) == 0


def test_induccion_genera_regla_con_repeticion(db_path):
    mc = MemoriaCasos(db_path)
    br = BaseReglas(db_path)
    inductor = MotorInduccion(mc, br, umbral_repeticion=2, prioridad_inicial=1)

    for _ in range(3):
        mc.registrar("hola cómo estás", "¡Hola!", regla_accion="saludar")

    resultado = inductor.evaluar()
    assert len(resultado) >= 1
    assert resultado[0]["accion"] == "saludar"

    regla = br.obtener(resultado[0]["id"])
    assert regla is not None
    assert regla["origen"] == "inducida"
    assert regla["prioridad"] == 1


def test_induccion_no_duplica_reglas(db_path):
    mc = MemoriaCasos(db_path)
    br = BaseReglas(db_path)
    br.agregar("('quiero' in input and 'saludar' in input)", "saludar", origen="manual")
    inductor = MotorInduccion(mc, br, umbral_repeticion=2)

    for _ in range(3):
        mc.registrar("quiero saludar", "saludo", regla_accion="saludar")

    resultado = inductor.evaluar()
    assert len(resultado) == 0


def test_induccion_en_loopy_integracion(db_path):
    loopy = Loopy(db_path)
    loopy.iniciar()

    for i in range(8):
        loopy.procesar("hola")

    inducidas = loopy.inductor.evaluar()
    if inducidas:
        regla = loopy.base_reglas.obtener(inducidas[0]["id"])
        assert regla is not None

    assert loopy.memoria_casos.contar() >= 8


def test_loopy_return_incluye_campos_fase2_3(db_path):
    loopy = Loopy(db_path)
    for cond, acc, pri, desc in REGLAS_INICIALES:
        loopy.base_reglas.agregar(cond, acc, pri, desc)

    loopy.iniciar()
    r = loopy.procesar("hola")
    assert "desde_caso" in r
    assert "inducidas" in r
    assert r["desde_caso"] is False
