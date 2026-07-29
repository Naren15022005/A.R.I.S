import argparse
import logging
import sys

from aris.config import DB_PATH, init_paths
try:
    from aris.loopy import Loopy
except ImportError:
    Loopy = None  # type: ignore

from aris.reglas_arranque import REGLAS_INICIALES


def setup_logging() -> None:
    init_paths()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="ARIS — Cerebro Simbólico")
    parser.add_argument("input", nargs="?", help="Entrada directa (omite para interactivo)")
    parser.add_argument("--serve", action="store_true", help="Iniciar servidor API (FastAPI)")
    parser.add_argument("--host", default="0.0.0.0", help="Host para el servidor API")
    parser.add_argument("--port", type=int, default=8000, help="Puerto para el servidor API")
    args = parser.parse_args()

    if args.serve:
        _arrancar_api(args.host, args.port)
        return

    _interfaz_cli(args.input)


def _interfaz_cli(input_directo: str | None = None) -> None:
    loopy = Loopy(DB_PATH)
    loopy.base_reglas.cargar_reglas_iniciales(REGLAS_INICIALES)

    sid = loopy.iniciar()
    logger = logging.getLogger("aris")
    logger.info("ARIS v%s listo (sesión: %s)", __import__("aris").__version__, sid[:8])
    logger.info("%d reglas cargadas", loopy.base_reglas.contar())

    if input_directo:
        resultado = loopy.procesar(input_directo)
        print(resultado["respuesta"])
        return

    print(f"\nARIS — Cerebro Simbólico (sesión: {sid[:8]})")
    print("Escribe 'salir' o 'exit' para terminar.\n")
    while True:
        try:
            entrada = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entrada:
            continue
        if entrada.lower() in ("salir", "exit", "quit"):
            print("Hasta luego.")
            break
        resultado = loopy.procesar(entrada)
        print(f"\n{resultado['respuesta']}\n")


def _arrancar_api(host: str, port: int) -> None:
    try:
        import uvicorn
        uvicorn.run("aris.api:app", host=host, port=port, log_level="info")
    except ImportError:
        print("Error: necesitas fastapi y uvicorn: pip install fastapi uvicorn")
        sys.exit(1)


if __name__ == "__main__":
    main()
