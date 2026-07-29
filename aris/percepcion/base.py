from abc import ABC, abstractmethod
from typing import Any


class CanalPercepcion(ABC):
    """Interfaz base para canales de percepción multicanal en ARIS."""

    nombre: str = "base"

    @abstractmethod
    def disponible(self) -> bool:
        """Indica si el canal/sensor está activo y disponible."""
        pass

    @abstractmethod
    def interpretar(self, entrada: Any) -> dict[str, Any]:
        """Devuelve SIEMPRE un diccionario con el esquema estructurado fijo:
        {
          "intencion": str,
          "sujeto": str | None,
          "predicado": str | None,
          "objeto": str | None,
          "comando_normalizado": str
        }
        """
        pass
