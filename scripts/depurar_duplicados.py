"""Migración: elimina reglas duplicadas de arranque y suma contadores.

Busca grupos de filas con la misma (condicion, accion), conserva la de mayor
éxitos (o menor ID en caso de empate), suma los contadores de las demás a la
elegida y elimina el resto.

Ejecutar:
    python scripts/depurar_duplicados.py [--db RUTA] [--dry-run] [--yes]
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def depurar(db_path: str, dry_run: bool = True) -> dict:
    if not Path(db_path).exists():
        print(f"Base no encontrada: {db_path}")
        return {"antes": 0, "despues": 0, "eliminadas": 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reglas'"
    )
    if not cursor.fetchone():
        print("Tabla 'reglas' no existe.")
        conn.close()
        return {"antes": 0, "despues": 0, "eliminadas": 0}

    cursor.execute("SELECT COUNT(*) FROM reglas")
    antes = cursor.fetchone()[0]

    # Agrupar por (condicion, accion) y encontrar duplicados
    cursor.execute("""
        SELECT condicion, accion, COUNT(*) as cnt
        FROM reglas
        GROUP BY condicion, accion
        HAVING cnt > 1
    """)
    grupos = cursor.fetchall()

    total_eliminadas = 0
    total_sumadas = {"exitos": 0, "fallos": 0}

    for cond, acc, cnt in grupos:
        # Obtener todas las filas del grupo, ordenadas por exitos DESC, id ASC
        cursor.execute(
            "SELECT id, exitos, fallos FROM reglas WHERE condicion = ? AND accion = ? ORDER BY exitos DESC, id ASC",
            (cond, acc),
        )
        filas = cursor.fetchall()

        if len(filas) <= 1:
            continue

        conservar = filas[0]
        eliminar = filas[1:]

        exitos_extra = sum(f[1] for f in eliminar)
        fallos_extra = sum(f[2] for f in eliminar)
        ids_eliminar = [f[0] for f in eliminar]

        if not dry_run:
            # Sumar contadores a la fila conservada
            cursor.execute(
                "UPDATE reglas SET exitos = exitos + ?, fallos = fallos + ? WHERE id = ?",
                (exitos_extra, fallos_extra, conservar[0]),
            )
            # Eliminar duplicados
            placeholders = ",".join("?" for _ in ids_eliminar)
            cursor.execute(
                f"DELETE FROM reglas WHERE id IN ({placeholders})",
                ids_eliminar,
            )

        total_eliminadas += len(eliminar)
        total_sumadas["exitos"] += exitos_extra
        total_sumadas["fallos"] += fallos_extra

        print(
            f"  ({cond[:50]}..., {acc}): conservado ID {conservar[0]} "
            f"({conservar[1]} exitos, {conservar[2]} fallos), "
            f"eliminados {len(eliminar)} duplicado(s) "
            f"({exitos_extra} exitos + {fallos_extra} fallos traspasados)"
        )

    if not dry_run:
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM reglas")
    despues = cursor.fetchone()[0]
    conn.close()

    return {
        "antes": antes,
        "despues": despues,
        "eliminadas": total_eliminadas,
        "exitos_traspasados": total_sumadas["exitos"],
        "fallos_traspasados": total_sumadas["fallos"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Limpia reglas duplicadas de arranque"
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Ruta a la base de datos (default: data/aris.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Solo listar, no borrar",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Ejecutar sin dry-run"
    )
    args = parser.parse_args()

    if args.db is None:
        args.db = str(Path(__file__).resolve().parent.parent / "data" / "aris.db")

    dry_run = not args.yes
    res = depurar(args.db, dry_run=dry_run)

    print(f"\nResumen:")
    print(f"  Antes:     {res['antes']} reglas")
    print(f"  Eliminadas: {res['eliminadas']}")
    print(f"  Después:    {res['despues']} reglas")
    if res["exitos_traspasados"]:
        print(f"  Éxitos traspasados: {res['exitos_traspasados']}")
    if res["fallos_traspasados"]:
        print(f"  Fallos traspasados: {res['fallos_traspasados']}")
    if dry_run and res["eliminadas"]:
        print(f"\n(Dry-run. Repite con --yes para aplicar.)")
    sys.exit(0)
