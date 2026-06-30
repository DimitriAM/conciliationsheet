from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class PartidaConciliatoria:
    id: Optional[int] = None
    cuenta_id: int = 0
    fecha: str = ""
    descripcion: str = ""
    monto: float = 0.0
    signo: int = 1
    origen: str = ""
    tipo: str = ""
    afecta: str = ""
    clasificacion: str = ""
    estado: str = "pendiente"
    fecha_resolucion: Optional[str] = None
    observaciones: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cuenta_id": self.cuenta_id,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "monto": self.monto,
            "signo": self.signo,
            "origen": self.origen,
            "tipo": self.tipo,
            "afecta": self.afecta,
            "clasificacion": self.clasificacion,
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
            monto=row["monto"],
            signo=row["signo"],
            origen=row["origen"],
            tipo=row["tipo"],
            afecta=row["afecta"],
            clasificacion=row["clasificacion"],
            estado=row["estado"],
            fecha_resolucion=row["fecha_resolucion"],
            observaciones=row["observaciones"],
        )

    def guardar(self) -> int:
        if self.monto < 0:
            raise ValueError("El monto no puede ser negativo")
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO partidas_conciliatorias
                       (cuenta_id, fecha, descripcion, monto, signo, origen, tipo, afecta, clasificacion, estado, fecha_resolucion, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.monto, self.signo,
                     self.origen, self.tipo, self.afecta, self.clasificacion,
                     self.estado, self.fecha_resolucion, self.observaciones),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE partidas_conciliatorias
                       SET cuenta_id=?, fecha=?, descripcion=?, monto=?, signo=?, origen=?, tipo=?,
                           afecta=?, clasificacion=?, estado=?, fecha_resolucion=?, observaciones=?
                       WHERE id=?""",
                    (self.cuenta_id, self.fecha, self.descripcion, self.monto, self.signo,
                     self.origen, self.tipo, self.afecta, self.clasificacion,
                     self.estado, self.fecha_resolucion, self.observaciones, self.id),
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
