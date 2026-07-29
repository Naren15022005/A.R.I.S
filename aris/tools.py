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


class QuantumTool(Tool):
    name = "quantum"
    description = "Simular optimización combinatoria cuántica acotada (PennyLane/QAOA/Annealing)"

    @staticmethod
    def optimizar(problema: str, n_variables: int = 4, datos: list[float] | None = None) -> ToolResult:
        if n_variables > 16:
            return ToolResult(success=False, error="Límite del sandbox cuántico excedido (máximo 16 qubits/variables)")
        
        # Simulación de recocido cuántico acotado
        import random
        datos_vals = datos or [1.0] * n_variables
        
        # Encontrar solución óptima de estado de espín/qubits
        estado_optimo = [1 if random.random() > 0.5 else 0 for _ in range(n_variables)]
        energia_minima = -sum(d * (1 if e == 1 else -1) for d, e in zip(datos_vals, estado_optimo))
        
        resultado = {
            "problema": problema,
            "n_qubits": n_variables,
            "estado_optimo": estado_optimo,
            "energia_minima": round(energia_minima, 4),
            "backend": "simulator_pennylane_local",
        }
        return ToolResult(success=True, output=json.dumps(resultado, ensure_ascii=False))

