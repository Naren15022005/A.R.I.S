import asyncio
from typing import Any, Callable

Listener = Callable[[dict[str, Any]], None]


class BusEventos:
    """Event Bus mínimo en memoria usando Pub/Sub asíncrono y síncrono."""

    def __init__(self) -> None:
        self._listeners: list[Listener] = []
        self._queues: list[asyncio.Queue] = []

    def suscribir_listener(self, callback: Listener) -> None:
        """Registra un callback síncrono."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def desuscribir_listener(self, callback: Listener) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def crear_queue(self) -> asyncio.Queue:
        """Crea una cola asíncrona para consumidores tipo WebSocket."""
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def eliminar_queue(self, q: asyncio.Queue) -> None:
        if q in self._queues:
            self._queues.remove(q)

    def publicar(self, evento: dict[str, Any]) -> None:
        """Publica un evento a todos los suscriptores e inyecta en las colas."""
        for cb in self._listeners:
            try:
                cb(evento)
            except Exception:
                pass

        for q in list(self._queues):
            try:
                q.put_nowait(evento)
            except Exception:
                pass


# Instancia global por defecto
bus_eventos = BusEventos()
