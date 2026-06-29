from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class DetalleConciliacion:
    id: Optional[int] = None
    conciliacion_id: int = 0
    movimiento_id: Optional[int] = None
    tabla_origen: Optional[str] = None
    monto_debe: float = 0.0
    monto_haber: float = 0.0
    estado: str = "coincide"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conciliacion_id": self.conciliacion_id,
            "movimiento_id": self.movimiento_id,
            "tabla_origen": self.tabla_origen,
            "monto_debe": self.monto_debe,
            "monto_haber": self.monto_haber,
            "estado": self.estado,
        }

    @staticmethod
    def from_row(row: dict) -> "DetalleConciliacion":
        return DetalleConciliacion(
            id=row["id"],
            conciliacion_id=row["conciliacion_id"],
            movimiento_id=row["movimiento_id"],
            tabla_origen=row["tabla_origen"],
            monto_debe=row["monto_debe"],
            monto_haber=row["monto_haber"],
            estado=row["estado"],
        )

    def guardar(self) -> int:
        if self.monto_debe < 0 or self.monto_haber < 0:
            raise ValueError("Los montos Debe/Haber no pueden ser negativos")
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO detalles_conciliacion
                       (conciliacion_id, movimiento_id, tabla_origen, monto_debe, monto_haber, estado)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (self.conciliacion_id, self.movimiento_id, self.tabla_origen,
                     self.monto_debe, self.monto_haber, self.estado),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE detalles_conciliacion
                       SET conciliacion_id=?, movimiento_id=?, tabla_origen=?, monto_debe=?, monto_haber=?, estado=?
                       WHERE id=?""",
                    (self.conciliacion_id, self.movimiento_id, self.tabla_origen,
                     self.monto_debe, self.monto_haber, self.estado, self.id),
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
            conn.execute("DELETE FROM detalles_conciliacion WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_conciliacion(conciliacion_id: int) -> list["DetalleConciliacion"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM detalles_conciliacion WHERE conciliacion_id=? ORDER BY id",
                (conciliacion_id,),
            ).fetchall()
            return [DetalleConciliacion.from_row(r) for r in rows]
        finally:
            conn.close()
