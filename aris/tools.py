import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from aris.sandbox import (
    TIMEOUT_WEB,
    SandboxComando,
    SandboxRuta,
    init_workspace,
)


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str | None = None


class Tool:
    name: str = ""
    description: str = ""

    def ejecutar(self, **kwargs) -> ToolResult:
        raise NotImplementedError


class FileSystemTool(Tool):
    name = "filesystem"
    description = "Leer, escribir y listar archivos en el área de trabajo"

    def __init__(self) -> None:
        init_workspace()
        self._sandbox = SandboxRuta()

    def leer(self, ruta: str) -> ToolResult:
        try:
            contenido = self._sandbox.leer(ruta)
            return ToolResult(success=True, output=contenido)
        except (FileNotFoundError, PermissionError) as e:
            return ToolResult(success=False, error=str(e))

    def escribir(self, ruta: str, contenido: str) -> ToolResult:
        try:
            bytes_escritos = self._sandbox.escribir(ruta, contenido)
            return ToolResult(success=True, output=f"Escritos {bytes_escritos} bytes en {ruta}")
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))

    def listar(self, ruta: str = "") -> ToolResult:
        try:
            entradas = self._sandbox.listar(ruta)
            return ToolResult(success=True, output="\n".join(entradas) if entradas else "(directorio vacío)")
        except (NotADirectoryError, PermissionError) as e:
            return ToolResult(success=False, error=str(e))

    def eliminar(self, ruta: str) -> ToolResult:
        try:
            ok = self._sandbox.eliminar(ruta)
            if ok:
                return ToolResult(success=True, output=f"Eliminado: {ruta}")
            return ToolResult(success=False, error=f"No encontrado: {ruta}")
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))


class TerminalTool(Tool):
    name = "terminal"
    description = "Ejecutar comandos del sistema operativo (lista blanca)"

    @staticmethod
    def ejecutar(comando: str) -> ToolResult:
        try:
            salida = SandboxComando.ejecutar(comando)
            return ToolResult(success=True, output=salida)
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))


class WebTool(Tool):
    name = "web"
    description = "Obtener contenido de una URL"

    @staticmethod
    def obtener(url: str, timeout: int = TIMEOUT_WEB) -> ToolResult:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                contenido = r.read().decode("utf-8", errors="replace")
                return ToolResult(success=True, output=contenido[:5000])
        except (urllib.error.URLError, ValueError, OSError) as e:
            return ToolResult(success=False, error=str(e))
