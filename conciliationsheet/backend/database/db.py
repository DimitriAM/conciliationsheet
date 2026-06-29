import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATABASE_PATH, SCHEMA_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cuentas_bancarias'"
        ).fetchone()
        if existing:
            return
        schema = Path(SCHEMA_PATH).read_text(encoding="utf-8")
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
