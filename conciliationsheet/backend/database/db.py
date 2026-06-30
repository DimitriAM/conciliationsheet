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


def get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("PRAGMA user_version").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def _migrate_v1(conn: sqlite3.Connection):
    conn.executescript("""
        DROP TABLE IF EXISTS detalles_conciliacion;
        DROP TABLE IF EXISTS partidas_conciliatorias;
        DROP TABLE IF EXISTS conciliaciones;
        CREATE TABLE partidas_conciliatorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL DEFAULT 0,
            signo INTEGER NOT NULL DEFAULT 1 CHECK(signo IN (1, -1)),
            origen TEXT NOT NULL CHECK(origen IN ('contabilidad', 'banco')),
            tipo TEXT NOT NULL CHECK(tipo IN ('cheque_no_debitado', 'deposito_no_acreditado', 'nota_debito_no_registrada', 'nota_credito_no_registrada', 'diferencia_contabilidad', 'diferencia_banco')),
            afecta TEXT NOT NULL CHECK(afecta IN ('banco', 'contabilidad')),
            clasificacion TEXT NOT NULL CHECK(clasificacion IN ('transitoria', 'permanente')),
            estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'ajustada', 'resuelta')),
            fecha_resolucion DATE,
            observaciones TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
        );
        CREATE TABLE conciliaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER NOT NULL,
            fecha_cierre DATE NOT NULL,
            metodo TEXT CHECK(metodo IN ('desde_contabilidad')),
            vision TEXT DEFAULT 'empresa' CHECK(vision IN ('empresa','banco')),
            saldo_segun_banco REAL,
            saldo_segun_contabilidad REAL,
            saldo_ajustado_banco REAL,
            saldo_ajustado_contabilidad REAL,
            diferencia_total REAL,
            estado TEXT DEFAULT 'en_proceso' CHECK(estado IN ('en_proceso','conciliada','pendiente_ajustes')),
            fecha_conciliacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            observaciones TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_partidas_conciliatorias_cuenta ON partidas_conciliatorias(cuenta_id);
        CREATE INDEX IF NOT EXISTS idx_conciliaciones_cuenta ON conciliaciones(cuenta_id);
        PRAGMA user_version = 1;
    """)


def _migrate_v2(conn: sqlite3.Connection):
    conn.executescript("""
        ALTER TABLE movimientos_contables ADD COLUMN saldo REAL;
        DROP TABLE IF EXISTS partidas_conciliatorias;
        DROP TABLE IF EXISTS conciliaciones;
        CREATE TABLE partidas_conciliatorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL DEFAULT 0,
            signo INTEGER NOT NULL DEFAULT 1 CHECK(signo IN (1, -1)),
            origen TEXT NOT NULL CHECK(origen IN ('contabilidad', 'banco')),
            tipo TEXT NOT NULL CHECK(tipo IN ('cheque_no_debitado', 'deposito_no_acreditado', 'nota_debito_no_registrada', 'nota_credito_no_registrada', 'diferencia_contabilidad', 'diferencia_banco')),
            afecta TEXT NOT NULL CHECK(afecta IN ('banco', 'contabilidad')),
            clasificacion TEXT NOT NULL CHECK(clasificacion IN ('transitoria', 'permanente')),
            estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'ajustada', 'resuelta')),
            fecha_resolucion DATE,
            observaciones TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
        );
        CREATE TABLE conciliaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER NOT NULL,
            fecha_cierre DATE NOT NULL,
            metodo TEXT CHECK(metodo IN ('desde_contabilidad')),
            vision TEXT DEFAULT 'empresa' CHECK(vision IN ('empresa','banco')),
            saldo_segun_banco REAL,
            saldo_segun_contabilidad REAL,
            saldo_ajustado_banco REAL,
            saldo_ajustado_contabilidad REAL,
            diferencia_total REAL,
            estado TEXT DEFAULT 'en_proceso' CHECK(estado IN ('en_proceso','conciliada','pendiente_ajustes')),
            fecha_conciliacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            observaciones TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_partidas_conciliatorias_cuenta ON partidas_conciliatorias(cuenta_id);
        CREATE INDEX IF NOT EXISTS idx_conciliaciones_cuenta ON conciliaciones(cuenta_id);
        PRAGMA user_version = 2;
    """)


def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        version = get_schema_version(conn)
        if version == 0:
            schema = Path(SCHEMA_PATH).read_text(encoding="utf-8")
            conn.executescript(schema)
            conn.execute("PRAGMA user_version = 2")
            conn.commit()
        elif version == 1:
            _migrate_v2(conn)
            conn.commit()
    finally:
        conn.close()
