import logging

from aris.acciones import ACCIONES_NO_REUTILIZABLES, PREDICADOS_DE_INTERACCION, ejecutar_accion
from aris.casos import MemoriaCasos
from aris.conocimiento import BaseConocimiento
from aris.grafo import GrafoConocimiento
from aris.induccion import MotorInduccion
from aris.memoria import MemoriaTrabajo
from aris.perfil import cargar_perfil
from aris.reglas import BaseReglas, MotorInferencia


class Loopy:
    def __init__(self, db_path: str, perfil: dict | None = None) -> None:
        self._logger = logging.getLogger("aris.loopy")
        self.conocimiento = BaseConocimiento(db_path)
        self.base_reglas = BaseReglas(db_path)
        self.memoria_trabajo = MemoriaTrabajo(db_path)
        self.memoria_casos = MemoriaCasos(db_path)
        self.grafo = GrafoConocimiento(db_path)
        self.perfil = perfil or cargar_perfil()
        self.motor = MotorInferencia(self.base_reglas, perfil=self.perfil)
        self.inductor = MotorInduccion(self.memoria_casos, self.base_reglas)
        self._ciclo = 0
        self._logger.info("Loopy inicializado")

    def iniciar(self, sesion_id: str | None = None) -> str:
        sid = self.memoria_trabajo.iniciar_sesion(sesion_id)
        self._logger.info("Sesión iniciada: %s", sid[:8])
        return sid

    def procesar(self, entrada: str) -> dict:
        entrada_plana = entrada.strip()
        if not entrada_plana:
            return {"respuesta": "", "regla": None, "regla_id": None, "candidatas": 0, "inducida": False}

        self._ciclo += 1
        self.memoria_trabajo.actualizar("ultimo_input", entrada_plana)
        self.memoria_trabajo.actualizar("contador", self._ciclo)

        candidatas = self.motor.buscar_coincidencias(entrada_plana, self.memoria_trabajo.estado)
        regla_ganadora = self.motor.priorizar(candidatas) if candidatas else None
        desde_caso = False

        if regla_ganadora is None:
            caso_similar = self._buscar_caso_similar(entrada_plana)
            if caso_similar:
                respuesta, accion_exitosa = ejecutar_accion(
                    caso_similar["regla_accion"], entrada_plana,
                    self.conocimiento, self.memoria_trabajo, self.base_reglas,
                )
                regla_id = None
                regla_accion = caso_similar["regla_accion"]
                desde_caso = True
                self._logger.info("Reutilizando caso #%d: %s", caso_similar["id"], regla_accion)
            else:
                respuesta = self._manejar_desconocido(entrada_plana)
                regla_id = None
                regla_accion = None
                accion_exitosa = False
        else:
            respuesta, accion_exitosa = ejecutar_accion(
                regla_ganadora["accion"], entrada_plana,
                self.conocimiento, self.memoria_trabajo, self.base_reglas,
            )
            self.base_reglas.actualizar_exito(regla_ganadora["id"])
            regla_id = regla_ganadora["id"]
            regla_accion = regla_ganadora["accion"]

        # Alimentar el grafo vivo con este ciclo cognitivo
        nodo_hecho = self.grafo.obtener_o_crear_nodo(
            tipo="memoria", subtipo="entrada",
            etiqueta=entrada_plana[:80],
            metadata={"sesion_id": self.memoria_trabajo.sesion_id, "ciclo": self._ciclo},
        )
        if regla_accion:
            nodo_regla = self.grafo.obtener_o_crear_nodo(
                tipo="simbolico", subtipo="regla",
                etiqueta=regla_accion,
                metadata={"regla_id": regla_id},
            )
            tipo_arista = "semantica" if desde_caso else "inferida"
            self.grafo.reforzar_o_crear_arista(nodo_hecho, nodo_regla, tipo=tipo_arista, incremento=0.15)

        self.memoria_casos.registrar(
            input_texto=entrada_plana,
            respuesta=respuesta,
            regla_id=regla_id,
            regla_accion=regla_accion,
            exitoso=accion_exitosa,
            sesion_id=self.memoria_trabajo.sesion_id,
        )

        self.conocimiento.agregar(
            "usuario", "dijo", entrada_plana[:100], self.memoria_trabajo.sesion_id
        )

        self.memoria_trabajo.actualizar("ultima_respuesta", respuesta)
        self.memoria_trabajo.actualizar("ultima_regla", regla_accion or "desconocido")

        inducidas = []
        if self._ciclo % 5 == 0:
            inducidas = self.inductor.evaluar()
            for regla in inducidas:
                nodo_inducida = self.grafo.crear_nodo(
                    tipo="simbolico", subtipo="regla",
                    etiqueta=regla.get("accion", "regla_inducida"),
                    metadata={"origen": "inducida", "regla_id": regla.get("id")},
                )
                self.grafo.crear_arista(nodo_hecho, nodo_inducida, tipo="inferida", peso=1.0)

        return {
            "respuesta": respuesta,
            "regla": regla_accion,
            "regla_id": regla_id,
            "candidatas": len(candidatas),
            "desde_caso": desde_caso,
            "inducidas": inducidas,
        }


    def _buscar_caso_similar(self, entrada: str) -> dict | None:
        similares = self.memoria_casos.buscar_similares(entrada, limite=3, umbral=0.3)
        for caso in similares:
            if not caso.get("regla_accion"):
                continue
            if not caso.get("exitoso"):
                continue
            if caso["regla_accion"] in ACCIONES_NO_REUTILIZABLES:
                continue
            return caso
        return None

    def _manejar_desconocido(self, entrada: str) -> str:
        self._logger.info("Input desconocido: %s", entrada[:60])
        hechos = self.conocimiento.buscar_texto(entrada, limite=5)
        hechos_declarativos = [
            h for h in hechos
            if h["predicado"] not in PREDICADOS_DE_INTERACCION
        ]
        if hechos_declarativos:
            h = hechos_declarativos[0]
            return (
                f"No tengo una regla para eso, pero sé que: "
                f"{h['sujeto']} {h['predicado']} {h['objeto']}."
            )
        return (
            "No entiendo eso aún. "
            "Puedes enseñarme usando 'recuerda que X es Y' "
            "o escribe 'ayuda' para ver lo que sé hacer."
        )

    def cerrar_sesion(self) -> None:
        self.memoria_trabajo.cerrar_sesion()
        self._logger.info("Sesión cerrada")
