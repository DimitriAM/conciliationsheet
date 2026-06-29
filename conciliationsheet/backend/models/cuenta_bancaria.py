from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class CuentaBancaria:
    id: Optional[int] = None
    nombre: str = ""
    cbu: Optional[str] = None
    banco: str = ""
    saldo_inicial: float = 0.0
    fecha_apertura: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cbu": self.cbu,
            "banco": self.banco,
            "saldo_inicial": self.saldo_inicial,
            "fecha_apertura": self.fecha_apertura,
        }

    @staticmethod
    def from_row(row: dict) -> "CuentaBancaria":
        return CuentaBancaria(
            id=row["id"],
            nombre=row["nombre"],
            cbu=row["cbu"],
            banco=row["banco"],
            saldo_inicial=row["saldo_inicial"],
            fecha_apertura=row["fecha_apertura"],
        )

    def guardar(self) -> int:
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO cuentas_bancarias (nombre, cbu, banco, saldo_inicial, fecha_apertura)
                       VALUES (?, ?, ?, ?, ?)""",
                    (self.nombre, self.cbu, self.banco, self.saldo_inicial, self.fecha_apertura),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE cuentas_bancarias
                       SET nombre=?, cbu=?, banco=?, saldo_inicial=?, fecha_apertura=?
                       WHERE id=?""",
                    (self.nombre, self.cbu, self.banco, self.saldo_inicial, self.fecha_apertura, self.id),
                )
            conn.commit()
            return self.id
        finally:
            conn.close()

    def eliminar(self) -> None:
        if self.id is None:
            return
        conn = get_connection()
        try:
            conn.execute("DELETE FROM cuentas_bancarias WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_id(cuenta_id: int) -> Optional["CuentaBancaria"]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM cuentas_bancarias WHERE id=?", (cuenta_id,)).fetchone()
            return CuentaBancaria.from_row(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def listar_todas() -> list["CuentaBancaria"]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM cuentas_bancarias ORDER BY nombre").fetchall()
            return [CuentaBancaria.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_saldo_actual(cuenta_id: int) -> float:
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT COALESCE(SUM(haber), 0) - COALESCE(SUM(debe), 0) AS saldo
                   FROM movimientos_bancarios WHERE cuenta_id=?""",
                (cuenta_id,),
            ).fetchone()
            return row["saldo"] if row else 0.0
        finally:
            conn.close()
