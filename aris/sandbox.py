import os
import re
import subprocess
from pathlib import Path

from aris.config import DATA_DIR


WORKSPACE = DATA_DIR / "tools_workspace"
TAMANO_MAX_ARCHIVO = 1024 * 1024
COMANDOS_PERMITIDOS = {"ls", "cat", "echo", "date", "pwd", "whoami", "uname", "head", "tail", "wc", "cal"}
TIMEOUT_COMANDO = 5
TIMEOUT_WEB = 10


def init_workspace() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "notas").mkdir(exist_ok=True)


class SandboxRuta:
    def __init__(self) -> None:
        self._base = WORKSPACE.resolve()

    def resolver(self, ruta: str) -> Path:
        candidata = (self._base / ruta).resolve()
        if not str(candidata).startswith(str(self._base)):
            raise PermisoError(f"Acceso denegado: fuera del área de trabajo ({self._base})")
        return candidata

    def leer(self, ruta: str) -> str:
        archivo = self.resolver(ruta)
        if not archivo.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
        if not archivo.is_file():
            raise PermisoError(f"No es un archivo: {ruta}")
        if archivo.stat().st_size > TAMANO_MAX_ARCHIVO:
            raise PermisoError(f"Archivo demasiado grande: {ruta}")
        return archivo.read_text(encoding="utf-8")

    def escribir(self, ruta: str, contenido: str) -> int:
        archivo = self.resolver(ruta)
        if archivo.exists() and not archivo.is_file():
            raise PermisoError(f"No es un archivo: {ruta}")
        archivo.parent.mkdir(parents=True, exist_ok=True)
        return archivo.write_text(contenido, encoding="utf-8")

    def listar(self, ruta: str = "") -> list[str]:
        directorio = self.resolver(ruta) if ruta else self._base
        if not directorio.is_dir():
            raise NotADirectoryError(f"No es un directorio: {ruta or '.'}")
        return sorted(p.name for p in directorio.iterdir())

    def eliminar(self, ruta: str) -> bool:
        archivo = self.resolver(ruta)
        if not archivo.exists():
            return False
        if archivo.is_dir():
            raise PermisoError("No se puede eliminar directorios")
        archivo.unlink()
        return True


class SandboxComando:
    TOXIC = re.compile(r"[;|&$`<>()\[\]{}!#~]")

    @classmethod
    def permitido(cls, comando: str) -> bool:
        partes = comando.strip().split()
        if not partes:
            return False
        if partes[0] not in COMANDOS_PERMITIDOS:
            return False
        return not cls.TOXIC.search(comando)

    @classmethod
    def ejecutar(cls, comando: str) -> str:
        if not cls.permitido(comando):
            raise PermisoError(f"Comando no permitido: {comando}")
        try:
            import os
            use_shell = os.name == "nt"
            cmd_arg = comando if use_shell else comando.split()
            resultado = subprocess.run(
                cmd_arg, shell=use_shell, capture_output=True, text=True,
                timeout=TIMEOUT_COMANDO,
            )

            salida = resultado.stdout or ""
            if resultado.stderr:
                salida += f"\n(stderr) {resultado.stderr.strip()}"
            return salida.strip() or "(sin salida)"
        except subprocess.TimeoutExpired:
            raise PermisoError(f"Comando agotó el tiempo ({TIMEOUT_COMANDO}s): {comando}")


class PermisoError(PermissionError):
    pass
