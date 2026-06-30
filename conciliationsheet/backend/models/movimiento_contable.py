from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class MovimientoContable:
    """Campos debe/haber en VISION EMPRESA (debe=ingreso, haber=egreso)."""
    id: Optional[int] = None
    cuenta_id: int = 0
    fecha: str = ""
    descripcion: str = ""
    debe: float = 0.0
    haber: float = 0.0
    saldo: Optional[float] = None
    comprobante: Optional[str] = None
    conciliado: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "debe": self.debe,
            "haber": self.haber,
            "saldo": self.saldo,
            "comprobante": self.comprobante,
            "conciliado": bool(self.conciliado),
        }

    @staticmethod
    def from_row(row: dict) -> "MovimientoContable":
        return MovimientoContable(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            fecha=row["fecha"],
            descripcion=row["descripcion"],
            debe=row["debe"],
            haber=row["haber"],
            saldo=row.get("saldo"),
            comprobante=row["comprobante"],
            conciliado=bool(row["conciliado"]),
        )

    def guardar(self) -> int:
        if self.debe < 0 or self.haber < 0:
            raise ValueError("Los montos Debe/Haber no pueden ser negativos")
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO movimientos_contables (cuenta_id, fecha, descripcion, debe, haber, saldo, comprobante, conciliado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.debe, self.haber,
                     self.saldo, self.comprobante, int(self.conciliado)),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE movimientos_contables
                       SET cuenta_id=?, fecha=?, descripcion=?, debe=?, haber=?, saldo=?, comprobante=?, conciliado=?
                       WHERE id=?""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.debe, self.haber,
                     self.saldo, self.comprobante, int(self.conciliado), self.id),
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
            conn.execute("DELETE FROM movimientos_contables WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_cuenta(cuenta_id: int) -> list["MovimientoContable"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM movimientos_contables WHERE cuenta_id=? ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [MovimientoContable.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_no_conciliados(cuenta_id: int) -> list["MovimientoContable"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM movimientos_contables WHERE cuenta_id=? AND conciliado=0 ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [MovimientoContable.from_row(r) for r in rows]
        finally:
            conn.close()
