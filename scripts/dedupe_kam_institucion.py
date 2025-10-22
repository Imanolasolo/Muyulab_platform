"""
Script para detectar y eliminar filas duplicadas en la tabla `kam_institucion`.

Precauciones:
- HACE UN BACKUP de la base de datos antes de modificarla.
- Por defecto realiza un "dry-run" que sólo reporta las duplicaciones.

Uso:
    python scripts/dedupe_kam_institucion.py --db database/muyulab.db [--run] [--keep first|last] [--add-index]

Opciones:
    --run        : Ejecuta la eliminación (si no se especifica, se realiza dry-run)
    --keep       : "first" (por defecto) o "last" — define qué fila conservar cuando hay duplicados
    --add-index  : Después de limpiar, crea un índice único (kam_id, institucion_id)

"""
import sqlite3
import argparse
import shutil
import os
import sys
from datetime import datetime


def backup_db(db_path):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def find_duplicates(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT kam_id, institucion_id, COUNT(*) as cnt
        FROM kam_institucion
        GROUP BY kam_id, institucion_id
        HAVING cnt > 1
    """)
    return cur.fetchall()


def get_rows_for_pair(conn, kam_id, institucion_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, kam_id, institucion_id FROM kam_institucion WHERE kam_id = ? AND institucion_id = ? ORDER BY id",
        (kam_id, institucion_id)
    )
    return cur.fetchall()


def delete_rows(conn, ids_to_delete):
    cur = conn.cursor()
    cur.executemany("DELETE FROM kam_institucion WHERE id = ?", [(i,) for i in ids_to_delete])
    conn.commit()


def create_unique_index(conn):
    cur = conn.cursor()
    # Si ya existe, usar CREATE UNIQUE INDEX IF NOT EXISTS
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_kam_institucion_unique ON kam_institucion (kam_id, institucion_id)")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Dedupe kam_institucion y opcionalmente crear índice único")
    parser.add_argument('--db', default='database/muyulab.db', help='Ruta al archivo de la base de datos sqlite')
    parser.add_argument('--run', action='store_true', help='Ejecutar las eliminaciones (por defecto solo dry-run)')
    parser.add_argument('--keep', choices=['first', 'last'], default='first', help='Qué fila conservar cuando hay duplicados')
    parser.add_argument('--add-index', action='store_true', help='Crear índice único (kam_id, institucion_id) después de la limpieza')
    args = parser.parse_args()

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"ERROR: No existe la base de datos en {db_path}")
        sys.exit(1)

    print(f"Usando DB: {db_path}")
    backup_path = backup_db(db_path)
    print(f"Backup creado en: {backup_path}")

    conn = sqlite3.connect(db_path)

    dups = find_duplicates(conn)
    if not dups:
        print("No se encontraron pares (kam_id, institucion_id) duplicados.")
        conn.close()
        return

    total_pairs = len(dups)
    print(f"Encontrados {total_pairs} pares duplicados (kam_id, institucion_id) con cnt > 1:\n")

    for kam_id, inst_id, cnt in dups:
        print(f"- kam_id={kam_id}, institucion_id={inst_id} -> {cnt} filas")
        rows = get_rows_for_pair(conn, kam_id, inst_id)
        print("  Filas: ", [r[0] for r in rows])

        # Decidir cuál eliminar
        if args.keep == 'first':
            ids_keep = rows[0][0]
            ids_delete = [r[0] for r in rows[1:]]
        else:
            ids_keep = rows[-1][0]
            ids_delete = [r[0] for r in rows[:-1]]

        print(f"  Conservar id: {ids_keep}")
        print(f"  A eliminar: {ids_delete}")

        if args.run and ids_delete:
            delete_rows(conn, ids_delete)
            print("  Eliminadas las filas indicadas.")

    if args.add_index:
        if args.run:
            create_unique_index(conn)
            print("Índice único creado: idx_kam_institucion_unique (kam_id, institucion_id)")
        else:
            print("--add-index se pasó pero no se está ejecutando (usa --run para aplicar cambios)")

    conn.close()
    print("Hecho.")


if __name__ == '__main__':
    main()
