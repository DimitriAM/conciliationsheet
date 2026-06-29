from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class MovimientoBancario:
    id: Optional[int] = None
    cuenta_id: int = 0
    fecha: str = ""
    descripcion: str = ""
    debe: float = 0.0
    haber: float = 0.0
    saldo: Optional[float] = None
    tipo: Optional[str] = None
    conciliado: bool = False

    def to_vision_empresa(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "debe_empresa": self.haber,
            "haber_empresa": self.debe,
            "saldo": self.saldo,
            "tipo": self.tipo,
            "conciliado": bool(self.conciliado),
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "debe": self.debe,
            "haber": self.haber,
            "saldo": self.saldo,
            "tipo": self.tipo,
            "conciliado": bool(self.conciliado),
        }

    @staticmethod
    def from_row(row: dict) -> "MovimientoBancario":
        return MovimientoBancario(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            fecha=row["fecha"],
            descripcion=row["descripcion"],
            debe=row["debe"],
            haber=row["haber"],
            saldo=row["saldo"],
            tipo=row["tipo"],
            conciliado=bool(row["conciliado"]),
        )

    def guardar(self) -> int:
        if self.debe < 0 or self.haber < 0:
            raise ValueError("Los montos Debe/Haber no pueden ser negativos")
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO movimientos_bancarios (cuenta_id, fecha, descripcion, debe, haber, saldo, tipo, conciliado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.debe, self.haber, self.saldo, self.tipo, int(self.conciliado)),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE movimientos_bancarios
                       SET cuenta_id=?, fecha=?, descripcion=?, debe=?, haber=?, saldo=?, tipo=?, conciliado=?
                       WHERE id=?""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.debe, self.haber, self.saldo, self.tipo, int(self.conciliado), self.id),
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
            conn.execute("DELETE FROM movimientos_bancarios WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_cuenta(cuenta_id: int) -> list["MovimientoBancario"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM movimientos_bancarios WHERE cuenta_id=? ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [MovimientoBancario.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_no_conciliados(cuenta_id: int) -> list["MovimientoBancario"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM movimientos_bancarios WHERE cuenta_id=? AND conciliado=0 ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [MovimientoBancario.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def calcular_saldo_periodo(cuenta_id: int, fecha_desde: str, fecha_hasta: str) -> float:
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT COALESCE(SUM(haber), 0) - COALESCE(SUM(debe), 0) AS saldo
                   FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?""",
                (cuenta_id, fecha_desde, fecha_hasta),
            ).fetchone()
            return row["saldo"] if row else 0.0
        finally:
            conn.close()
