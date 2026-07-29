import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class MemoriaTrabajo:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._estado: dict = {}
        self._sesion_id: str | None = None
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sesiones (
                    sesion_id TEXT PRIMARY KEY,
                    estado TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def iniciar_sesion(self, sesion_id: str | None = None) -> str:
        self._sesion_id = sesion_id or str(uuid4())
        self._estado = {"inicio": datetime.now(timezone.utc).isoformat()}

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sesiones (sesion_id, estado, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (self._sesion_id, json.dumps(self._estado), datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return self._sesion_id

    def actualizar(self, clave: str, valor: object) -> None:
        if not self._sesion_id:
            return
        self._estado[clave] = valor
        self._persistir()

    def obtener(self, clave: str, default: object = None) -> object:
        return self._estado.get(clave, default)

    @property
    def estado(self) -> dict:
        return dict(self._estado)

    @property
    def sesion_id(self) -> str | None:
        return self._sesion_id

    def _persistir(self) -> None:
        if not self._sesion_id:
            return
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE sesiones SET estado = ?, updated_at = ? WHERE sesion_id = ?",
                (json.dumps(self._estado), datetime.now(timezone.utc).isoformat(), self._sesion_id),
            )
            conn.commit()

    def cerrar_sesion(self) -> None:
        self._persistir()
        self._estado = {}
        self._sesion_id = None
