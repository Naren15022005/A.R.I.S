from typing import Any

from aris.percepcion.base import CanalPercepcion
from aris.percepcion.bci import CanalBCI
from aris.percepcion.texto import CanalTextoSLM


class RegistroPercepcion:
    """Registro central de canales de percepción multicanal para ARIS (Fase 10.2)."""

    def __init__(self) -> None:
        self.canales: list[CanalPercepcion] = [
            CanalTextoSLM(),
            CanalBCI(),
        ]

    def agregar_canal(self, canal: CanalPercepcion) -> None:
        self.canales.append(canal)

    def obtener_canal(self, nombre: str) -> CanalPercepcion | None:
        for c in self.canales:
            if c.nombre == nombre:
                return c
        return None

    def interpretar(self, entrada: Any, canal: str | None = None) -> dict[str, Any]:
        if canal:
            target = self.obtener_canal(canal)
            if target and target.disponible():
                return target.interpretar(entrada)
        
        # Selección inteligente por tipo de entrada cuando no se especifica canal
        if isinstance(entrada, (int, float)):
            bci = self.obtener_canal("bci_neurosity")
            if bci and bci.disponible():
                return bci.interpretar(entrada)

        txt = self.obtener_canal("texto_libre")
        if txt and txt.disponible():
            return txt.interpretar(entrada)

        for c in self.canales:
            if c.disponible():
                return c.interpretar(entrada)
        
        return CanalTextoSLM().interpretar(str(entrada))



class CapaPercepcion(CanalTextoSLM):
    """Alias de compatibilidad hacia atrás para CapaPercepcion pre-v0.7.0."""
    def normalizar_comando(self, texto: str) -> str:
        res = self.interpretar(texto)
        return res.get("comando_normalizado") or texto


__all__ = ["CanalPercepcion", "CanalTextoSLM", "CanalBCI", "RegistroPercepcion", "CapaPercepcion"]
