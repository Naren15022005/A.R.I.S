import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from aris.eventos import bus_eventos


class GrafoConocimiento:
    """Modelo de Grafo Tipado y Vivo para ARIS (Fase 10.1).
    
    Gestiona nodos (simbólico, percepción, memoria) y aristas (manual, semántica, inferida).
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodos (
                    id TEXT PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    subtipo TEXT,
                    etiqueta TEXT NOT NULL,
                    metadata TEXT,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS aristas (
                    id TEXT PRIMARY KEY,
                    origen_id TEXT NOT NULL REFERENCES nodos(id),
                    destino_id TEXT NOT NULL REFERENCES nodos(id),
                    tipo TEXT NOT NULL,
                    peso REAL DEFAULT 1.0,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_aristas_origen ON aristas(origen_id);
                CREATE INDEX IF NOT EXISTS idx_aristas_destino ON aristas(destino_id);
            """)

    def crear_nodo(self, tipo: str, subtipo: str, etiqueta: str, metadata: dict[str, Any] | None = None) -> str:
        nodo_id = str(uuid4())
        meta_str = json.dumps(metadata or {})
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO nodos (id, tipo, subtipo, etiqueta, metadata) VALUES (?, ?, ?, ?, ?)",
                (nodo_id, tipo, subtipo, etiqueta, meta_str),
            )
        
        bus_eventos.publicar({
            "accion": "nuevo_nodo",
            "data": {
                "id": nodo_id,
                "tipo": tipo,
                "subtipo": subtipo,
                "etiqueta": etiqueta,
                "metadata": metadata or {},
            }
        })
        return nodo_id

    def crear_arista(self, origen_id: str, destino_id: str, tipo: str, peso: float = 1.0) -> str:
        arista_id = str(uuid4())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO aristas (id, origen_id, destino_id, tipo, peso) VALUES (?, ?, ?, ?, ?)",
                (arista_id, origen_id, destino_id, tipo, peso),
            )
        
        bus_eventos.publicar({
            "accion": "nueva_arista",
            "data": {
                "id": arista_id,
                "origen_id": origen_id,
                "destino_id": destino_id,
                "tipo": tipo,
                "peso": peso,
            }
        })
        return arista_id

    def nodos_por_tipo(self, tipo: str) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM nodos WHERE tipo = ?", (tipo,)).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                res.append(d)
            return res

    def vecinos(self, nodo_id: str) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT n.*, a.tipo as tipo_arista, a.peso 
                FROM aristas a 
                JOIN nodos n ON (a.destino_id = n.id)
                WHERE a.origen_id = ?
                UNION
                SELECT n.*, a.tipo as tipo_arista, a.peso 
                FROM aristas a 
                JOIN nodos n ON (a.origen_id = n.id)
                WHERE a.destino_id = ?
            """, (nodo_id, nodo_id)).fetchall()
            
            res = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d["metadata"]) if d.get("metadata") else {}
                res.append(d)
            return res

    def exportar_json(self) -> dict[str, Any]:
        """Devuelve {"nodos": [...], "aristas": [...]} estructurado para D3 / Cytoscape."""
        with self._get_conn() as conn:
            n_rows = conn.execute("SELECT * FROM nodos").fetchall()
            a_rows = conn.execute("SELECT * FROM aristas").fetchall()

            nodos = []
            for r in n_rows:
                d = dict(r)
                d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                nodos.append(d)

            aristas = [dict(r) for r in a_rows]
            return {"nodos": nodos, "aristas": aristas}
