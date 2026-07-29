import random
import re

from aris.habilidades import GeneradorHabilidades, RegistroHabilidades
from aris.tools import FileSystemTool, TerminalTool, WebTool


class ResultadoAccion(str):
    """Resultado de una acción: texto + flag explícito de éxito.

    Usa como str directamente para no romper interfaces existentes.
    """
    def __new__(cls, texto: str, exitoso: bool = True):
        obj = str.__new__(cls, texto)
        obj.exitoso = exitoso
        return obj


PREDICADOS_DE_INTERACCION = frozenset({"dijo", "respondio"})

ACCIONES_NO_REUTILIZABLES = frozenset({
    "guardar_hecho", "olvidar", "consultar_hecho",
    "leer_archivo", "escribir_archivo", "listar_archivos",
    "eliminar_archivo", "ejecutar_comando", "web_get",
    "crear_habilidad", "aprobar_habilidad",
})


_TOOL_FS: FileSystemTool | None = None
_TOOL_TERM: TerminalTool | None = None
_TOOL_WEB: WebTool | None = None
_REG_HABILIDADES: RegistroHabilidades | None = None


def _reg_habs() -> RegistroHabilidades:
    global _REG_HABILIDADES
    if _REG_HABILIDADES is None:
        _REG_HABILIDADES = RegistroHabilidades()
    return _REG_HABILIDADES


def _fs() -> FileSystemTool:
    global _TOOL_FS
    if _TOOL_FS is None:
        _TOOL_FS = FileSystemTool()
    return _TOOL_FS

def _term() -> TerminalTool:
    global _TOOL_TERM
    if _TOOL_TERM is None:
        _TOOL_TERM = TerminalTool()
    return _TOOL_TERM

def _web() -> WebTool:
    global _TOOL_WEB
    if _TOOL_WEB is None:
        _TOOL_WEB = WebTool()
    return _TOOL_WEB


def ejecutar_accion(accion: str, entrada: str, conocimiento, memoria, reglas) -> tuple[str, bool]:
    gestor = GestorAcciones(conocimiento, memoria, reglas)
    handler = getattr(gestor, accion, None)
    if handler:
        resultado = handler(entrada)
        return resultado, getattr(resultado, "exitoso", True)
    resultado = _reg_habs().ejecutar(accion, entrada, conocimiento, memoria, reglas)
    if resultado is not None:
        return resultado, True
    return f"No sé ejecutar la acción '{accion}'.", False


class GestorAcciones:
    def __init__(self, conocimiento, memoria, reglas) -> None:
        self.conocimiento = conocimiento
        self.memoria = memoria
        self.reglas = reglas

    def saludar(self, entrada: str) -> str:
        saludos = [
            "¡Hola! ¿En qué puedo ayudarte?",
            "¡Qué tal! Estoy listo para lo que necesites.",
            "Hola. Dime qué necesitas.",
            "¡Hey! Cuéntame.",
        ]
        return random.choice(saludos)

    def despedir(self, entrada: str) -> str:
        despedidas = [
            "Hasta luego. Cuídate.",
            "Adiós. Estaré aquí cuando me necesites.",
            "Nos vemos. Buena suerte.",
        ]
        return random.choice(despedidas)

    def agradecer(self, entrada: str) -> str:
        return "¡De nada! Para eso estoy."

    def presentarse(self, entrada: str) -> str:
        return (
            "Soy ARIS, un sistema de agente inteligente simbólico. "
            "Mi núcleo funciona con reglas y hechos, sin depender de modelos externos. "
            "Puedo aprender patrones con el tiempo y ejecutar acciones según lo que me enseñes."
        )

    def listar_conocimiento(self, entrada: str) -> str:
        hechos = self.conocimiento.listar(limite=20)
        if not hechos:
            return "Aún no tengo conocimiento almacenado."
        lineas = [f"  {h['sujeto']} → {h['predicado']} → {h['objeto']}" for h in hechos]
        return "Esto es lo que sé:\n" + "\n".join(lineas)

    def listar_reglas(self, entrada: str) -> str:
        reglas = self.reglas.listar()
        if not reglas:
            return "No hay reglas registradas."
        lineas = [f"  [{r['id']}] (prioridad {r['prioridad']}) SI {r['condicion']} → {r['accion']} ({r['exitos']} éxitos)" for r in reglas]
        return "Mis reglas actuales:\n" + "\n".join(lineas)

    def mostrar_ayuda(self, entrada: str) -> str:
        return (
            "Puedes hablarme de forma natural. Algunas cosas que entiendo:\n"
            "  • 'hola' — te saludo\n"
            "  • 'adiós' — me despido\n"
            "  • 'gracias' — te agradezco\n"
            "  • 'quién eres' — me presento\n"
            "  • 'qué sabes' — listo mi conocimiento\n"
            "  • 'reglas' — muestro mis reglas\n"
            "  • 'recuerda que X es Y' — guardo un hecho\n"
            "  • 'qué sabes de X' — busco un hecho\n"
            "  • 'olvida X' — borro un hecho\n"
            "  • 'ayuda' — esto"
        )

    def guardar_hecho(self, entrada: str) -> str:
        m = re.match(r"recuerda que (.+?) es (.+)", entrada, re.IGNORECASE)
        if m:
            sujeto = m.group(1).strip()
            objeto = m.group(2).strip()
            hecho_id = self.conocimiento.agregar(sujeto, "es", objeto, self.memoria.sesion_id)
            return f"Entendido: {sujeto} es {objeto}. Lo recordaré (id #{hecho_id})."
        return ResultadoAccion("Usa el formato: 'recuerda que X es Y'", exitoso=False)

    def olvidar(self, entrada: str) -> str:
        m = re.match(r"olvida (.+)", entrada, re.IGNORECASE)
        if m:
            texto = m.group(1).strip()
            resultados = self.conocimiento.buscar_texto(texto)
            if not resultados:
                return f"No encontré nada que coincida con '{texto}'."
            for h in resultados:
                self.conocimiento.eliminar(h["id"])
            return f"Olvidado. Eliminé {len(resultados)} hecho(s) relacionado(s) con '{texto}'."
        return ResultadoAccion("Usa el formato: 'olvida X'", exitoso=False)

    def consultar_hecho(self, entrada: str) -> str:
        m = re.match(r"qué sabes de (.+)", entrada, re.IGNORECASE)
        if m:
            texto = m.group(1).strip()
            resultados = self.conocimiento.buscar(sujeto=texto)
            if not resultados:
                resultados = self.conocimiento.buscar_texto(texto)
            if not resultados:
                return f"No sé nada sobre '{texto}'."
            lineas = [f"  {h['sujeto']} → {h['predicado']} → {h['objeto']}" for h in resultados]
            return f"Sobre '{texto}' sé:\n" + "\n".join(lineas)
        return ResultadoAccion("Usa el formato: 'qué sabes de X'", exitoso=False)

    def eco(self, entrada: str) -> str:
        return entrada

    # ─── Tools (Fase 6) ─────────────────────────────────────────────────────

    def leer_archivo(self, entrada: str) -> str:
        m = re.match(r"lee (.+)", entrada, re.IGNORECASE)
        if not m:
            return "Usa: 'lee <ruta>'"
        ruta = m.group(1).strip()
        r = _fs().leer(ruta)
        if r.success:
            return f"Contenido de {ruta}:\n{r.output}"
        return f"Error al leer {ruta}: {r.error}"

    def escribir_archivo(self, entrada: str) -> str:
        m = re.match(r"escribe (.+?) (?:con|dice|contenido) (.+)", entrada, re.IGNORECASE)
        if m:
            ruta = m.group(1).strip()
            contenido = m.group(2).strip()
        else:
            m2 = re.match(r"guarda en (.+?) (.+)", entrada, re.IGNORECASE)
            if m2:
                ruta = m2.group(1).strip()
                contenido = m2.group(2).strip()
            else:
                return "Usa: 'escribe <ruta> con <contenido>' o 'guarda en <ruta> <contenido>'"
        r = _fs().escribir(ruta, contenido)
        if r.success:
            return f"Archivo guardado: {ruta} ({r.output})"
        return f"Error al escribir {ruta}: {r.error}"

    def listar_archivos(self, entrada: str) -> str:
        m = re.match(r"lista (.+)", entrada, re.IGNORECASE)
        ruta = m.group(1).strip() if m else ""
        r = _fs().listar(ruta)
        if r.success:
            return f"Contenido de {ruta or '.'}:\n{r.output}"
        return f"Error: {r.error}"

    def eliminar_archivo(self, entrada: str) -> str:
        m = re.match(r"borra (.+)", entrada, re.IGNORECASE)
        if not m:
            return "Usa: 'borra <ruta>'"
        ruta = m.group(1).strip()
        r = _fs().eliminar(ruta)
        if r.success:
            return r.output
        return f"Error: {r.error}"

    def ejecutar_comando(self, entrada: str) -> str:
        m = re.match(r"ejecuta (.+)", entrada, re.IGNORECASE)
        if not m:
            return "Usa: 'ejecuta <comando>'"
        comando = m.group(1).strip()
        r = _term().ejecutar(comando)
        if r.success:
            return f"$ {comando}\n{r.output}"
        return f"Error: {r.error}"

    def web_get(self, entrada: str) -> str:
        m = re.match(r"(?:abre|visita|web) (.+)", entrada, re.IGNORECASE)
        if not m:
            return "Usa: 'abre <url>' o 'visita <url>'"
        url = m.group(1).strip()
        if not url.startswith("http"):
            url = "https://" + url
        r = _web().obtener(url)
        if r.success:
            return f"Contenido de {url}:\n{r.output[:2000]}"
        return f"Error al obtener {url}: {r.error}"

    def herramientas_disponibles(self, entrada: str) -> str:
        texto = (
            "Herramientas del sistema:\n"
            "  • 'lee <ruta>' — leer archivo\n"
            "  • 'escribe <ruta> con <texto>' — escribir archivo\n"
            "  • 'lista <dir>' — listar directorio\n"
            "  • 'borra <ruta>' — eliminar archivo\n"
            "  • 'ejecuta <comando>' — comando del sistema\n"
            "  • 'abre <url>' — obtener contenido web\n"
        )
        habilidades = _reg_habs().listar()
        if habilidades:
            texto += "\nHabilidades instaladas:\n"
            for h in habilidades:
                estado = "✅" if h.aprobada else "⏳ pendiente"
                texto += f"  • {estado} '{h.accion}' — {h.descripcion}\n"
        else:
            texto += "\n  • 'crea una herramienta que ...' — generar nueva habilidad\n"
        return texto.strip()

    def crear_habilidad(self, entrada: str) -> str:
        resultado = GeneradorHabilidades.generar_desde_prompt(entrada)
        if resultado is None:
            return "Usa: 'crea una herramienta que <descripción>'"
        descripcion, accion = resultado
        h = GeneradorHabilidades.generar(descripcion, accion)
        if h is None:
            return "No pude generar esa habilidad."
        error = GeneradorHabilidades.validar_sintaxis(h.codigo)
        if error:
            return f"Error de sintaxis al generar: {error}"
        ok = _reg_habs().registrar(h)
        if not ok:
            return f"Ya existe una habilidad con la acción '{accion}'."
        return (
            f"Habilidad '{h.nombre}' generada (acción: {h.accion}).\n"
            f"Puedes probarla con: '{h.accion} <entrada>'.\n"
            f"Para activarla permanentemente: 'aprueba {h.accion}'"
        )

    def aprobar_habilidad(self, entrada: str) -> str:
        m = re.match(r"aprueba\s+(\S+)", entrada, re.IGNORECASE)
        if not m:
            habs = _reg_habs().listar()
            pendientes = [h for h in habs if not h.aprobada]
            if not pendientes:
                return "No hay habilidades pendientes por aprobar."
            texto = "Habilidades pendientes:\n"
            for h in pendientes:
                texto += f"  • 'aprueba {h.accion}' — {h.descripcion}\n"
            return texto.strip()
        accion = m.group(1)
        h = _reg_habs().obtener(accion)
        if h is None:
            return f"No existe la habilidad '{accion}'. Primero créala con 'crea una herramienta que...'"
        if h.aprobada:
            return f"La habilidad '{accion}' ya está aprobada."
        ok = _reg_habs().aprobar(accion)
        if ok:
            return f"Habilidad '{accion}' aprobada y activada."
        return f"Error al aprobar '{accion}'."

    def listar_habilidades(self, entrada: str) -> str:
        habilidades = _reg_habs().listar()
        if not habilidades:
            return "No hay habilidades instaladas. Crea una con 'crea una herramienta que...'"
        lineas = []
        for h in habilidades:
            estado = "✅ activa" if h.aprobada else "⏳ pendiente"
            lineas.append(f"  • {estado} — {h.nombre} ({h.accion}) — {h.descripcion}")
        return "Habilidades instaladas:\n" + "\n".join(lineas)

    def mostrar_ayuda(self, entrada: str) -> str:
        return (
            "Puedes hablarme de forma natural. Algunas cosas que entiendo:\n"
            "  • 'hola' — te saludo\n"
            "  • 'adiós' — me despido\n"
            "  • 'gracias' — te agradezco\n"
            "  • 'quién eres' — me presento\n"
            "  • 'qué sabes' — listo mi conocimiento\n"
            "  • 'reglas' — muestro mis reglas\n"
            "  • 'recuerda que X es Y' — guardo un hecho\n"
            "  • 'qué sabes de X' — busco un hecho\n"
            "  • 'olvida X' — borro un hecho\n"
            "  • 'herramientas' — herramientas del sistema\n"
            "  • 'crea una herramienta que...' — genera una habilidad nueva\n"
            "  • 'aprueba <acción>' — activa una habilidad pendiente\n"
            "  • 'habilidades' — lista habilidades instaladas\n"
            "  • 'ayuda' — esto"
        )
