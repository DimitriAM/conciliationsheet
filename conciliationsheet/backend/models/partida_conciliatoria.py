from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class PartidaConciliatoria:
    id: Optional[int] = None
    cuenta_id: int = 0
    fecha: str = ""
    descripcion: str = ""
    tipo: Optional[str] = None
    origen: Optional[str] = None
    debe: float = 0.0
    haber: float = 0.0
    saldo_afectado: Optional[str] = None
    estado: str = "pendiente"
    fecha_resolucion: Optional[str] = None
    observaciones: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "tipo": self.tipo,
            "origen": self.origen,
            "debe": self.debe,
            "haber": self.haber,
            "saldo_afectado": self.saldo_afectado,
            "estado": self.estado,
            "fecha_resolucion": self.fecha_resolucion,
            "observaciones": self.observaciones,
        }

    @staticmethod
    def from_row(row: dict) -> "PartidaConciliatoria":
        return PartidaConciliatoria(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            fecha=row["fecha"],
            descripcion=row["descripcion"],
            tipo=row["tipo"],
            origen=row["origen"],
            debe=row["debe"],
            haber=row["haber"],
            saldo_afectado=row["saldo_afectado"],
            estado=row["estado"],
            fecha_resolucion=row["fecha_resolucion"],
            observaciones=row["observaciones"],
        )

    def guardar(self) -> int:
        if self.debe < 0 or self.haber < 0:
            raise ValueError("Los montos Debe/Haber no pueden ser negativos")
        if self.tipo == "transitoria" and self.estado not in ("pendiente", "resuelta"):
            raise ValueError("Estado invalido para partida transitoria. Use: pendiente, resuelta")
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO partidas_conciliatorias
                       (cuenta_id, fecha, descripcion, tipo, origen, debe, haber, saldo_afectado, estado, fecha_resolucion, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.tipo, self.origen,
                     self.debe, self.haber, self.saldo_afectado, self.estado, self.fecha_resolucion, self.observaciones),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE partidas_conciliatorias
                       SET cuenta_id=?, fecha=?, descripcion=?, tipo=?, origen=?, debe=?, haber=?,
                           saldo_afectado=?, estado=?, fecha_resolucion=?, observaciones=?
                       WHERE id=?""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.tipo, self.origen,
                     self.debe, self.haber, self.saldo_afectado, self.estado, self.fecha_resolucion, self.observaciones, self.id),
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
            conn.execute("DELETE FROM partidas_conciliatorias WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_cuenta(cuenta_id: int) -> list["PartidaConciliatoria"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM partidas_conciliatorias WHERE cuenta_id=? ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [PartidaConciliatoria.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_pendientes(cuenta_id: int) -> list["PartidaConciliatoria"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM partidas_conciliatorias WHERE cuenta_id=? AND estado='pendiente' ORDER BY fecha, id",
                (cuenta_id,),
            ).fetchall()
            return [PartidaConciliatoria.from_row(r) for r in rows]
        finally:
            conn.close()

    def marcar_como_resuelta(self, fecha_resolucion: str, observaciones: Optional[str] = None) -> None:
        if self.id is None:
            return
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE partidas_conciliatorias SET estado='resuelta', fecha_resolucion=?, observaciones=? WHERE id=?",
                (fecha_resolucion, observaciones, self.id),
            )
            conn.commit()
            self.estado = "resuelta"
            self.fecha_resolucion = fecha_resolucion
            if observaciones:
                self.observaciones = observaciones
        finally:
            conn.close()
