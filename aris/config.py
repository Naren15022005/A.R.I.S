from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "aris.db"
REGLA_POR_DEFECTO_PRIORIDAD = 5


def init_paths() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
