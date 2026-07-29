import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aris.config import DATA_DIR, DB_PATH, init_paths
from aris.eventos import bus_eventos
from aris.grafo import GrafoConocimiento
from aris.percepcion import CapaPercepcion

try:
    from aris.loopy import Loopy
except ImportError:
    Loopy = Any  # type: ignore
from aris.reglas_arranque import REGLAS_INICIALES

percepcion = CapaPercepcion()


class ChatRequest(BaseModel):
    mensaje: str
    sesion_id: str | None = None


class ChatResponse(BaseModel):
    respuesta: str
    regla: str | None = None
    regla_id: int | None = None
    desde_caso: bool = False
    sesion_id: str | None = None


class HechoCreate(BaseModel):
    sujeto: str
    predicado: str = "es"
    objeto: str


class HechoResponse(BaseModel):
    id: int
    sujeto: str
    predicado: str
    objeto: str
    timestamp: str


class ReglaCreate(BaseModel):
    condicion: str
    accion: str
    prioridad: int = 5
    descripcion: str = ""


class ReglaResponse(BaseModel):
    id: int
    condicion: str
    accion: str
    prioridad: int
    exitos: int
    fallos: int
    origen: str
    descripcion: str | None


_loopy: Loopy | None = None


def _init() -> None:
    global _loopy
    if _loopy is not None:
        return
    if Loopy is Any:
        raise RuntimeError("El módulo núcleo de ARIS (loopy.py) no está disponible.")

    init_paths()
    loopy = Loopy(DB_PATH)
    loopy.base_reglas.cargar_reglas_iniciales(REGLAS_INICIALES)
    loopy.iniciar()
    _loopy = loopy



STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="ARIS API",
    version="0.6.0",
    description="Artificial Reasoning Intelligent System — Cerebro Simbólico",
)


@app.get("/", response_class=HTMLResponse)
def _index():
    html = STATIC_DIR / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ARIS API</h1><p>Ejecuta con <code>--serve</code></p>")


def _get_loopy() -> Loopy:
    _init()
    assert _loopy is not None
    return _loopy


@app.get("/health")
def health():
    return {"status": "ok", "nombre": "ARIS", "version": "0.6.0"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    loopy = _get_loopy()
    comando_norm = percepcion.normalizar_comando(req.mensaje)
    resultado = loopy.procesar(comando_norm)
    return ChatResponse(
        respuesta=resultado["respuesta"],
        regla=resultado["regla"],
        regla_id=resultado["regla_id"],
        desde_caso=resultado.get("desde_caso", False),
        sesion_id=loopy.memoria_trabajo.sesion_id,
    )


@app.get("/hechos", response_model=list[HechoResponse])
def listar_hechos(limite: int = 20):
    loopy = _get_loopy()
    hechos = loopy.conocimiento.listar(limite=limite)
    return [HechoResponse(**h) for h in hechos]


@app.post("/hechos", response_model=HechoResponse)
def crear_hecho(body: HechoCreate):
    loopy = _get_loopy()
    hecho_id = loopy.conocimiento.agregar(body.sujeto, body.predicado, body.objeto, loopy.memoria_trabajo.sesion_id)
    resultados = loopy.conocimiento.buscar(sujeto=body.sujeto, predicado=body.predicado, objeto=body.objeto)
    for h in resultados:
        if h["id"] == hecho_id:
            return HechoResponse(**h)
    raise HTTPException(500, "Error al crear hecho")


@app.get("/hechos/buscar", response_model=list[HechoResponse])
def buscar_hechos(q: str):
    loopy = _get_loopy()
    resultados = loopy.conocimiento.buscar_texto(q)
    return [HechoResponse(**h) for h in resultados]


@app.delete("/hechos/{hecho_id}")
def eliminar_hecho(hecho_id: int):
    loopy = _get_loopy()
    if not loopy.conocimiento.eliminar(hecho_id):
        raise HTTPException(404, "Hecho no encontrado")
    return {"ok": True}


@app.get("/reglas", response_model=list[ReglaResponse])
def listar_reglas():
    loopy = _get_loopy()
    return [ReglaResponse(**r) for r in loopy.base_reglas.listar()]


@app.post("/reglas", response_model=ReglaResponse)
def crear_regla(body: ReglaCreate):
    loopy = _get_loopy()
    rid = loopy.base_reglas.agregar(body.condicion, body.accion, body.prioridad, body.descripcion)
    regla = loopy.base_reglas.obtener(rid)
    if not regla:
        raise HTTPException(500, "Error al crear regla")
    return ReglaResponse(**regla)


@app.delete("/reglas/{regla_id}")
def eliminar_regla(regla_id: int):
    loopy = _get_loopy()
    if not loopy.base_reglas.eliminar(regla_id):
        raise HTTPException(404, "Regla no encontrada")
    return {"ok": True}


@app.get("/sesion")
def estado_sesion():
    loopy = _get_loopy()
    return {
        "sesion_id": loopy.memoria_trabajo.sesion_id,
        "contador": loopy.memoria_trabajo.obtener("contador", 0),
        "reglas": loopy.base_reglas.contar(),
        "hechos": loopy.conocimiento.contar(),
        "casos": loopy.memoria_casos.contar(),
        "perfil": loopy.perfil.get("nombre", "defecto"),
    }


@app.get("/galaxia")
def galaxia():
    nodes = []
    links = []

    loopy = None
    if Loopy is not Any and _loopy is not None:
        loopy = _loopy
    else:
        try:
            loopy = _get_loopy()
        except Exception:
            loopy = None

    if loopy is not None:
        # 1. Nodos Morados (Reglas de inferencia)
        for r in loopy.base_reglas.listar():
            rid = f"regla_{r['id']}"
            nodes.append({
                "id": rid,
                "label": r.get("descripcion") or f"Regla #{r['id']}",
                "tipo": "regla",
                "grupo": "morado",
                "detalles": f"Condición: {r['condicion']} → Acción: {r['accion']}",
            })

        # 2. Nodos Teal (Hechos de la Base de Conocimiento)
        hechos = loopy.conocimiento.listar(limite=50)
        for h in hechos:
            hid = f"hecho_{h['id']}"
            nodes.append({
                "id": hid,
                "label": f"{h['sujeto']} {h['predicado']} {h['objeto']}",
                "tipo": "hecho",
                "grupo": "teal",
                "detalles": f"Sujeto: {h['sujeto']} | Predicado: {h['predicado']} | Objeto: {h['objeto']}",
            })

        # 3. Nodos Dorado (Casos en memoria)
        if hasattr(loopy, "memoria_casos"):
            casos = loopy.memoria_casos.buscar_similares("", limite=20)
            for c in casos:
                cid = f"caso_{c['id']}"
                nodes.append({
                    "id": cid,
                    "label": f"Caso #{c['id']}: {c['input_text']}",
                    "tipo": "caso",
                    "grupo": "dorado",
                    "detalles": f"Acción: {c['accion_ejecutada']}",
                })

        # 4. Nodos Esmeralda (Habilidades sintetizadas)
        if hasattr(loopy, "registro_habilidades"):
            habs = loopy.registro_habilidades.listar()
            for hb in habs:
                hbid = f"habilidad_{hb['id']}"
                nodes.append({
                    "id": hbid,
                    "label": f"Habilidad: {hb['accion']}",
                    "tipo": "habilidad",
                    "grupo": "esmeralda",
                    "detalles": hb.get("descripcion", ""),
                })

        # Aristas: Relacionar reglas con hechos coincidentes
        for r_node in [n for n in nodes if n["tipo"] == "regla"]:
            for h_node in [n for n in nodes if n["tipo"] == "hecho"]:
                suj = h_node["label"].split()[0].lower()
                if suj and len(suj) > 2 and suj in r_node["detalles"].lower():
                    links.append({
                        "source": r_node["id"],
                        "target": h_node["id"],
                        "rel": "relacionado",
                    })

    if not nodes:
        nodes = [
            {"id": "regla_1", "label": "Regla Inicial: Saludar", "tipo": "regla", "grupo": "morado"},
            {"id": "hecho_1", "label": "ARIS es Cerebro Simbólico", "tipo": "hecho", "grupo": "teal"},
        ]
        links = [{"source": "regla_1", "target": "hecho_1", "rel": "relacionado"}]

    return {"nodes": nodes, "links": links}


@app.get("/grafo")
def obtener_grafo():
    try:
        grafo = GrafoConocimiento(DB_PATH)
        data = grafo.exportar_json()
        if data["nodos"]:
            return data
    except Exception:
        pass
    return galaxia()


@app.websocket("/ws/grafo")
async def ws_grafo(websocket: WebSocket):
    await websocket.accept()
    q = bus_eventos.crear_queue()
    try:
        # Enviar estado inicial
        await websocket.send_json({"accion": "init", "data": galaxia()})
        while True:
            evento = await q.get()
            await websocket.send_json(evento)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        bus_eventos.eliminar_queue(q)


