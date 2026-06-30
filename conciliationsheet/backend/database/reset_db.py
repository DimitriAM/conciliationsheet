"""
Script para resetear la base de datos:
elimina todos los movimientos, partidas y conciliaciones,
dejando solo la estructura de tablas.

Uso: python backend/database/reset_db.py
"""
import sqlite3, sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "conciliationsheet.db"

if not DB.exists():
    print(f"No existe la DB en: {DB}")
    print("Ejecuta el servidor primero para crearla")
    sys.exit(1)

conn = sqlite3.connect(str(DB))
conn.execute("PRAGMA foreign_keys = OFF")

tablas = [
    "partidas_conciliatorias",
    "conciliaciones",
    "movimientos_bancarios",
    "movimientos_contables",
    "diccionario_sinonimos",
]
for t in tablas:
    conn.execute(f"DELETE FROM {t}")
    print(f"  DELETE FROM {t}")

conn.execute("DELETE FROM sqlite_sequence")
print("  DELETE FROM sqlite_sequence")

conn.execute("DELETE FROM cuentas_bancarias WHERE id <> 1")
cur = conn.execute("SELECT COUNT(*) FROM cuentas_bancarias WHERE id=1")
if cur.fetchone()[0] == 0:
    conn.execute("INSERT INTO cuentas_bancarias (id, nombre, banco) VALUES (1, 'Cuenta Principal', 'Default')")
    print("  Cuenta Principal recreada")

conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
conn.close()

print("\nBase de datos reseteada correctamente.")
