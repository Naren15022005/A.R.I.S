"""Migración: elimina hechos contaminados por fallbacks recursivos.

Busca tuplas (aris, respondio, X) donde X contiene texto de fallback
y las elimina de la base de conocimiento. Ejecutar con:

    python scripts/limpiar_fallbacks.py [--db RUTA] [--dry-run]

Sin --dry-run borra en firme.
"""

import argparse
import sqlite3
import sys
from pathlib import Path


FALLBACK_FRAGMENTS = [
    "No tengo una regla para eso",
    "No entiendo eso aún",
]


def limpiar(db_path: str, dry_run: bool = True) -> int:
    if not Path(db_path).exists():
        print(f"Base no encontrada: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Asegurar que la tabla existe
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='hechos'"
    )
    if not cursor.fetchone():
        print("Tabla 'hechos' no existe. Nada que limpiar.")
        conn.close()
        return 0

    lugar = " OR ".join(
        f"objeto LIKE ?" for _ in FALLBACK_FRAGMENTS
    )
    query = (
        f"SELECT id, sujeto, predicado, substr(objeto, 1, 80) FROM hechos "
        f"WHERE predicado = 'respondio' AND ({lugar})"
    )
    cursor.execute(query, [f"%{f}%" for f in FALLBACK_FRAGMENTS])
    filas = cursor.fetchall()

    if not filas:
        print("No se encontraron hechos contaminados.")
        conn.close()
        return 0

    print(f"Encontrados {len(filas)} hecho(s) contaminado(s):")
    for fid, sujeto, pred, obj in filas:
        print(f"  [{fid}] ({sujeto}, {pred}, \"{obj}...\")")
        if not dry_run:
            cursor.execute("DELETE FROM hechos WHERE id = ?", (fid,))

    if not dry_run:
        conn.commit()
        print(f"\nEliminados {len(filas)} hecho(s) en firme.")
    else:
        print(f"\n(--dry-run) No se eliminó nada. Repite sin --dry-run para borrar.")

    conn.close()
    return len(filas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Limpia hechos contaminados por fallbacks recursivos"
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Ruta a la base de datos (default: data/aris.db junto al script)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Solo listar, no borrar (default: True)",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Ejecutar sin dry-run"
    )
    args = parser.parse_args()

    if args.db is None:
        # default: data/aris.db relativo al proyecto
        args.db = str(Path(__file__).resolve().parent.parent / "data" / "aris.db")

    dry_run = not args.yes
    total = limpiar(args.db, dry_run=dry_run)
    sys.exit(0 if total == 0 else 0)
