from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database.db import get_connection
from models.detalle_conciliacion import DetalleConciliacion


@dataclass
class Conciliacion:
    id: Optional[int] = None
    cuenta_id: int = 0
    fecha_cierre: str = ""
    metodo: Optional[str] = None
    vision: str = "empresa"
    saldo_segun_banco: Optional[float] = None
    saldo_segun_contabilidad: Optional[float] = None
    saldo_ajustado_banco: Optional[float] = None
    saldo_ajustado_contabilidad: Optional[float] = None
    diferencia_total: Optional[float] = None
    estado: str = "en_proceso"
    fecha_conciliacion: Optional[str] = None
    observaciones: Optional[str] = None

    def __post_init__(self):
        if self.fecha_conciliacion is None:
            self.fecha_conciliacion = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha_cierre": self.fecha_cierre,
            "metodo": self.metodo,
            "vision": self.vision,
            "saldo_segun_banco": self.saldo_segun_banco,
            "saldo_segun_contabilidad": self.saldo_segun_contabilidad,
            "saldo_ajustado_banco": self.saldo_ajustado_banco,
            "saldo_ajustado_contabilidad": self.saldo_ajustado_contabilidad,
            "diferencia_total": self.diferencia_total,
            "estado": self.estado,
            "fecha_conciliacion": self.fecha_conciliacion,
            "observaciones": self.observaciones,
        }

    @staticmethod
    def from_row(row: dict) -> "Conciliacion":
        return Conciliacion(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            fecha_cierre=row["fecha_cierre"],
            metodo=row["metodo"],
            vision=row.get("vision", "empresa"),
            saldo_segun_banco=row["saldo_segun_banco"],
            saldo_segun_contabilidad=row["saldo_segun_contabilidad"],
            saldo_ajustado_banco=row["saldo_ajustado_banco"],
            saldo_ajustado_contabilidad=row["saldo_ajustado_contabilidad"],
            diferencia_total=row["diferencia_total"],
            estado=row["estado"],
            fecha_conciliacion=row["fecha_conciliacion"],
            observaciones=row["observaciones"],
        )

    def guardar(self) -> int:
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO conciliaciones
                       (cuenta_id, fecha_cierre, metodo, vision, saldo_segun_banco, saldo_segun_contabilidad,
                        saldo_ajustado_banco, saldo_ajustado_contabilidad, diferencia_total, estado, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.cuenta_id, self.fecha_cierre, self.metodo, self.vision,
                     self.saldo_segun_banco, self.saldo_segun_contabilidad,
                     self.saldo_ajustado_banco, self.saldo_ajustado_contabilidad,
                     self.diferencia_total, self.estado, self.observaciones),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE conciliaciones
                       SET cuenta_id=?, fecha_cierre=?, metodo=?, vision=?, saldo_segun_banco=?, saldo_segun_contabilidad=?,
                           saldo_ajustado_banco=?, saldo_ajustado_contabilidad=?, diferencia_total=?, estado=?, observaciones=?
                       WHERE id=?""",
                    (self.cuenta_id, self.fecha_cierre, self.metodo, self.vision,
                     self.saldo_segun_banco, self.saldo_segun_contabilidad,
                     self.saldo_ajustado_banco, self.saldo_ajustado_contabilidad,
                     self.diferencia_total, self.estado, self.observaciones, self.id),
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
            conn.execute("DELETE FROM conciliaciones WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_cuenta(cuenta_id: int) -> list["Conciliacion"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM conciliaciones WHERE cuenta_id=? ORDER BY fecha_cierre DESC",
                (cuenta_id,),
            ).fetchall()
            return [Conciliacion.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_ultima(cuenta_id: int, antes_de: Optional[str] = None) -> Optional["Conciliacion"]:
        conn = get_connection()
        try:
            if antes_de:
                row = conn.execute(
                    "SELECT * FROM conciliaciones WHERE cuenta_id=? AND fecha_cierre < ? ORDER BY fecha_cierre DESC LIMIT 1",
                    (cuenta_id, antes_de),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM conciliaciones WHERE cuenta_id=? ORDER BY fecha_cierre DESC LIMIT 1",
                    (cuenta_id,),
                ).fetchone()
            return Conciliacion.from_row(dict(row)) if row else None
        finally:
            conn.close()

    def obtener_detalles(self) -> list["DetalleConciliacion"]:
        if self.id is None:
            return []
        return DetalleConciliacion.obtener_por_conciliacion(self.id)
