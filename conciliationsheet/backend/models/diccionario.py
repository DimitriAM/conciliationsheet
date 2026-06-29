from dataclasses import dataclass
from typing import Optional

from database.db import get_connection


@dataclass
class DiccionarioSinonimo:
    id: Optional[int] = None
    fuente: str = ""
    patron: str = ""
    tipo: str = ""
    autogenerado: bool = False
    activo: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fuente": self.fuente,
            "patron": self.patron,
            "tipo": self.tipo,
            "autogenerado": self.autogenerado,
            "activo": self.activo,
        }

    @staticmethod
    def from_row(row: dict) -> "DiccionarioSinonimo":
        return DiccionarioSinonimo(
            id=row["id"],
            fuente=row["fuente"],
            patron=row["patron"],
            tipo=row["tipo"],
            autogenerado=bool(row["autogenerado"]),
            activo=bool(row["activo"]),
        )

    def guardar(self) -> int:
        conn = get_connection()
        try:
            if self.id is None:
                cursor = conn.execute(
                    """INSERT INTO diccionario_sinonimos (fuente, patron, tipo, autogenerado, activo)
                       VALUES (?, ?, ?, ?, ?)""",
                    (self.fuente, self.patron, self.tipo, int(self.autogenerado), int(self.activo)),
                )
                self.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE diccionario_sinonimos
                       SET fuente=?, patron=?, tipo=?, autogenerado=?, activo=?
                       WHERE id=?""",
                    (self.fuente, self.patron, self.tipo, int(self.autogenerado), int(self.activo), self.id),
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
            conn.execute("DELETE FROM diccionario_sinonimos WHERE id=?", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_por_id(entry_id: int) -> Optional["DiccionarioSinonimo"]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM diccionario_sinonimos WHERE id=?", (entry_id,)).fetchone()
            return DiccionarioSinonimo.from_row(dict(row)) if row else None
        finally:
            conn.close()

    @staticmethod
    def listar_por_fuente(fuente: Optional[str] = None, tipo: Optional[str] = None) -> list["DiccionarioSinonimo"]:
        conn = get_connection()
        try:
            sql = "SELECT * FROM diccionario_sinonimos WHERE activo=1"
            params = []
            if fuente:
                sql += " AND fuente=?"
                params.append(fuente)
            if tipo:
                sql += " AND tipo=?"
                params.append(tipo)
            sql += " ORDER BY fuente, tipo, patron"
            rows = conn.execute(sql, params).fetchall()
            return [DiccionarioSinonimo.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def listar_todos() -> list["DiccionarioSinonimo"]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM diccionario_sinonimos WHERE activo=1 ORDER BY fuente, tipo, patron"
            ).fetchall()
            return [DiccionarioSinonimo.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def aprender(fuente: str, descripcion: str, tipo: str) -> Optional["DiccionarioSinonimo"]:
        palabras = descripcion.lower().split()
        palabras_utiles = [p for p in palabras if len(p) > 2 and not p.replace(".", "").isdigit()]
        creados = []
        for palabra in palabras_utiles:
            conn = get_connection()
            try:
                existente = conn.execute(
                    "SELECT id FROM diccionario_sinonimos WHERE fuente=? AND patron=? AND activo=1",
                    (fuente, palabra),
                ).fetchone()
                if existente:
                    continue
                cursor = conn.execute(
                    """INSERT INTO diccionario_sinonimos (fuente, patron, tipo, autogenerado, activo)
                       VALUES (?, ?, ?, 1, 1)""",
                    (fuente, palabra, tipo),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM diccionario_sinonimos WHERE id=?", (cursor.lastrowid,)).fetchone()
                if row:
                    creados.append(DiccionarioSinonimo.from_row(dict(row)))
            finally:
                conn.close()
        return creados
