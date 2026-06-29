from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from database.db import get_connection
from models.cuenta_bancaria import CuentaBancaria
from models.movimiento_bancario import MovimientoBancario
from models.movimiento_contable import MovimientoContable
from models.partida_conciliatoria import PartidaConciliatoria
from models.conciliacion import Conciliacion
from models.detalle_conciliacion import DetalleConciliacion
from utils.helpers import coinciden_descripciones, normalizar_descripcion


class ConciliadorBancario:
    def __init__(self, cuenta_id: int, fecha_desde: str, fecha_hasta: str,
                 saldo_final_banco: Optional[float] = None,
                 saldo_final_contable: Optional[float] = None,
                 saldo_inicial_banco: Optional[float] = None,
                 saldo_inicial_contable: Optional[float] = None):
        self.cuenta_id = cuenta_id
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        self._saldo_final_banco = saldo_final_banco
        self._saldo_final_contable = saldo_final_contable
        self._saldo_inicial_banco = saldo_inicial_banco
        self._saldo_inicial_contable = saldo_inicial_contable
        self._tolerancia = 0.01
        self._cargar_diccionario()

    def _cargar_diccionario(self):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT fuente, patron, tipo FROM diccionario_sinonimos WHERE activo=1"
            ).fetchall()
            self._diccionario = {}  # fuente -> [(patron, tipo)]
            for r in rows:
                f = r["fuente"]
                if f not in self._diccionario:
                    self._diccionario[f] = []
                self._diccionario[f].append((r["patron"].lower(), r["tipo"]))
        finally:
            conn.close()

    def _coinciden_descripciones_con_diccionario(self, desc_a: str, desc_b: str) -> bool:
        if coinciden_descripciones(desc_a, desc_b):
            return True
        da = desc_a.lower().strip()
        db = desc_b.lower().strip()
        for fuente, entries in self._diccionario.items():
            for patron, tipo in entries:
                if patron in da and patron in db:
                    return True
        return False

    def _convertir_saldo_banco_a_empresa(self, saldo_banco_vision: float) -> float:
        return saldo_banco_vision

    def _convertir_movimiento_banco_a_empresa(self, mov: dict) -> dict:
        mov_empresa = dict(mov)
        mov_empresa["debe"] = mov["haber"]
        mov_empresa["haber"] = mov["debe"]
        return mov_empresa

    def _obtener_saldo_banco(self) -> float:
        if self._saldo_final_banco is not None:
            return self._saldo_final_banco
        conn = get_connection()
        try:
            cuenta = CuentaBancaria.obtener_por_id(self.cuenta_id)
            saldo_inicial = cuenta.saldo_inicial if cuenta else 0.0
            row = conn.execute(
                """SELECT COALESCE(SUM(haber), 0) - COALESCE(SUM(debe), 0) AS saldo
                   FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchone()
            return saldo_inicial + (row["saldo"] if row else 0.0)
        finally:
            conn.close()

    def _obtener_saldo_contabilidad(self) -> float:
        if self._saldo_final_contable is not None:
            return self._saldo_final_contable
        conn = get_connection()
        try:
            cuenta = CuentaBancaria.obtener_por_id(self.cuenta_id)
            saldo_inicial = cuenta.saldo_inicial if cuenta else 0.0
            row = conn.execute(
                """SELECT COALESCE(SUM(debe), 0) - COALESCE(SUM(haber), 0) AS saldo
                   FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchone()
            return saldo_inicial + (row["saldo"] if row else 0.0)
        finally:
            conn.close()

    def _obtener_saldo_banco_hasta(self, fecha: str) -> float:
        conn = get_connection()
        try:
            cuenta = CuentaBancaria.obtener_por_id(self.cuenta_id)
            saldo_inicial = cuenta.saldo_inicial if cuenta else 0.0
            row = conn.execute(
                """SELECT COALESCE(SUM(haber), 0) - COALESCE(SUM(debe), 0) AS saldo
                   FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha <= ?""",
                (self.cuenta_id, fecha),
            ).fetchone()
            return saldo_inicial + (row["saldo"] if row else 0.0)
        finally:
            conn.close()

    def _obtener_saldo_contabilidad_hasta(self, fecha: str) -> float:
        conn = get_connection()
        try:
            cuenta = CuentaBancaria.obtener_por_id(self.cuenta_id)
            saldo_inicial = cuenta.saldo_inicial if cuenta else 0.0
            row = conn.execute(
                """SELECT COALESCE(SUM(debe), 0) - COALESCE(SUM(haber), 0) AS saldo
                   FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha <= ?""",
                (self.cuenta_id, fecha),
            ).fetchone()
            return saldo_inicial + (row["saldo"] if row else 0.0)
        finally:
            conn.close()

    def _movimientos_banco_periodo(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _movimientos_contabilidad_periodo(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _montos_coinciden(monto_a: float, monto_b: float, tolerancia: float = 0.01) -> bool:
        if monto_a == 0 and monto_b == 0:
            return True
        if max(monto_a, monto_b) == 0:
            return False
        return abs(monto_a - monto_b) / max(abs(monto_a), abs(monto_b), 0.01) <= tolerancia

    def _filtrar_no_match(self, items: list[dict], candidatos: list[dict],
                          campo_monto_item: str, campo_monto_cand: str) -> list[dict]:
        tolerancia_amplia = 0.10
        no_match = []
        for item in items:
            monto_item = abs(item.get(campo_monto_item, 0))
            desc_item = item.get("descripcion", "") or ""
            matched = False

            # Pass 1: match exacto por monto (±1%)
            for cand in candidatos:
                monto_cand = abs(cand.get(campo_monto_cand, 0))
                if ConciliadorBancario._montos_coinciden(monto_item, monto_cand):
                    matched = True
                    break

            # Pass 2: monto cercano (±10%) Y descripcion coincidente
            if not matched and desc_item.strip():
                for cand in candidatos:
                    desc_cand = cand.get("descripcion", "") or ""
                    if not desc_cand.strip():
                        continue
                    monto_cand = abs(cand.get(campo_monto_cand, 0))
                    if not ConciliadorBancario._montos_coinciden(monto_item, monto_cand, tolerancia_amplia):
                        continue
                    if self._coinciden_descripciones_con_diccionario(desc_item, desc_cand):
                        matched = True
                        break

            if not matched:
                no_match.append(item)
        return no_match

    def _identificar_partidas_empresa(self) -> dict:
        conn = get_connection()
        try:
            bancos = conn.execute(
                """SELECT * FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            bancos = [dict(r) for r in bancos]

            contables = conn.execute(
                """SELECT * FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            contables = [dict(r) for r in contables]

            cta_haber = [c for c in contables if c.get("haber", 0) > 0]
            cta_debe = [c for c in contables if c.get("debe", 0) > 0]
            banco_debe = [b for b in bancos if b.get("debe", 0) > 0]
            banco_haber = [b for b in bancos if b.get("haber", 0) > 0]

            cheques_raw = self._filtrar_no_match(cta_haber, banco_debe, "haber", "debe")
            depositos_raw = self._filtrar_no_match(cta_debe, banco_haber, "debe", "haber")
            notas_db_raw = self._filtrar_no_match(banco_debe, cta_haber, "debe", "haber")
            notas_cr_raw = self._filtrar_no_match(banco_haber, cta_debe, "haber", "debe")

            def item_to_dict(m, campo_monto):
                return {
                    "id": m["id"],
                    "fecha": m["fecha"],
                    "descripcion": m.get("descripcion", ""),
                    "monto": m.get(campo_monto, 0),
                    "comprobante": m.get("comprobante"),
                    "tipo": m.get("tipo"),
                }

            return {
                "cheques_no_debitados": [item_to_dict(c, "haber") for c in cheques_raw],
                "depositos_no_acreditados": [item_to_dict(d, "debe") for d in depositos_raw],
                "notas_debito_no_registradas": [item_to_dict(n, "debe") for n in notas_db_raw],
                "notas_credito_no_registradas": [item_to_dict(n, "haber") for n in notas_cr_raw],
            }
        finally:
            conn.close()

    def _partidas_conciliatorias_mes_anterior(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM partidas_conciliatorias
                   WHERE cuenta_id=? AND fecha < ? AND estado='pendiente'
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _limpiar_partidas_anteriores(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM partidas_conciliatorias WHERE cuenta_id=?", (self.cuenta_id,))
            conn.commit()
        finally:
            conn.close()

    def _guardar_conciliacion(self, datos: dict) -> Conciliacion:
        reg = Conciliacion(
            cuenta_id=self.cuenta_id,
            fecha_cierre=datos["fecha_cierre"],
            metodo=datos["metodo"],
            vision="empresa",
            saldo_segun_banco=datos["saldo_segun_banco"],
            saldo_segun_contabilidad=datos["saldo_segun_contabilidad"],
            saldo_ajustado_banco=datos["saldo_ajustado_banco"],
            saldo_ajustado_contabilidad=datos["saldo_ajustado_contabilidad"],
            diferencia_total=datos["diferencia"],
            estado=datos["estado"],
        )
        reg.guardar()
        return reg

    def _guardar_partida_conciliatoria(self, categoria: str, item: dict) -> PartidaConciliatoria:
        es_transitoria = categoria in ("cheques_no_debitados", "depositos_no_acreditados")
        tipo = "transitoria" if es_transitoria else "permanente"
        origen = (
            "contabilidad_no_banco"
            if categoria in ("cheques_no_debitados", "depositos_no_acreditados")
            else "banco_no_contabilizado"
        )
        saldo_afectado = "contabilidad" if origen == "banco_no_contabilizado" else "banco"
        es_contra = categoria in ("cheques_no_debitados", "notas_debito_no_registradas")
        monto = item["monto"]
        pc = PartidaConciliatoria(
            cuenta_id=self.cuenta_id,
            fecha=item["fecha"],
            descripcion=item["descripcion"],
            tipo=tipo,
            origen=origen,
            debe=monto if es_contra else 0.0,
            haber=monto if not es_contra else 0.0,
            saldo_afectado=saldo_afectado,
            estado="pendiente",
        )
        pc.guardar()
        return pc

    def _agrupar_partidas(self, partidas: dict) -> dict:
        totales = {}
        for cat in ("cheques_no_debitados", "depositos_no_acreditados",
                     "notas_debito_no_registradas", "notas_credito_no_registradas"):
            totales[cat] = sum(p["monto"] for p in partidas[cat])
        return totales

    def _guardar_todas_partidas(self, partidas: dict) -> list[PartidaConciliatoria]:
        guardadas = []
        for cat in ("cheques_no_debitados", "depositos_no_acreditados",
                     "notas_debito_no_registradas", "notas_credito_no_registradas"):
            for item in partidas[cat]:
                pc = self._guardar_partida_conciliatoria(cat, item)
                guardadas.append(pc)
        return guardadas

    def conciliar_forma_1(self) -> dict:
        """
        Forma 1: Contabilidad → Banco
        Parte del saldo contable, aplica ajustes, llega al saldo del extracto bancario.
        """
        self._limpiar_partidas_anteriores()
        saldo_contable = self._obtener_saldo_contabilidad()
        partidas = self._identificar_partidas_empresa()
        totales = self._agrupar_partidas(partidas)

        saldo_banco_calculado = (
            saldo_contable
            + totales["cheques_no_debitados"]
            - totales["depositos_no_acreditados"]
            - totales["notas_debito_no_registradas"]
            + totales["notas_credito_no_registradas"]
        )

        saldo_banco = self._obtener_saldo_banco()
        saldo_banco_empresa = self._convertir_saldo_banco_a_empresa(saldo_banco)
        diferencia = round(saldo_banco_calculado - saldo_banco_empresa, 2)
        conciliado = abs(diferencia) <= self._tolerancia
        reg = self._guardar_conciliacion({
            "fecha_cierre": self.fecha_hasta,
            "metodo": "desde_banco",
            "saldo_segun_banco": saldo_banco_empresa,
            "saldo_segun_contabilidad": saldo_contable,
            "saldo_ajustado_banco": saldo_banco_calculado,
            "saldo_ajustado_contabilidad": saldo_contable,
            "diferencia": diferencia,
            "estado": "conciliada" if conciliado else "pendiente_ajustes",
        })
        partidas_guardadas = self._guardar_todas_partidas(partidas)
        return {
            "conciliacion_id": reg.id,
            "metodo": "forma_1",
            "saldo_segun_contabilidad": saldo_contable,
            "saldo_segun_banco": saldo_banco_empresa,
            "saldo_banco_calculado": saldo_banco_calculado,
            "saldo_banco_ajustado": saldo_banco_calculado,
            "detalle_ajustes": {
                "cheques_no_debitados": +totales["cheques_no_debitados"],
                "depositos_no_acreditados": -totales["depositos_no_acreditados"],
                "notas_debito_no_registradas": -totales["notas_debito_no_registradas"],
                "notas_credito_no_registradas": +totales["notas_credito_no_registradas"],
            },
            "diferencia": diferencia,
            "conciliado": conciliado,
            "partidas_conciliatorias": [p.to_dict() for p in partidas_guardadas],
        }

    def conciliar_forma_2(self) -> dict:
        """
        Forma 2: Banco → Contabilidad
        Parte del saldo del extracto bancario, aplica ajustes, llega al saldo contable.
        """
        self._limpiar_partidas_anteriores()
        saldo_banco = self._obtener_saldo_banco()
        saldo_banco_empresa = self._convertir_saldo_banco_a_empresa(saldo_banco)
        partidas = self._identificar_partidas_empresa()
        totales = self._agrupar_partidas(partidas)

        saldo_contable_calculado = (
            saldo_banco_empresa
            - totales["cheques_no_debitados"]
            + totales["depositos_no_acreditados"]
            + totales["notas_debito_no_registradas"]
            - totales["notas_credito_no_registradas"]
        )

        saldo_contable = self._obtener_saldo_contabilidad()
        diferencia = round(saldo_contable_calculado - saldo_contable, 2)
        conciliado = abs(diferencia) <= self._tolerancia
        reg = self._guardar_conciliacion({
            "fecha_cierre": self.fecha_hasta,
            "metodo": "desde_contabilidad",
            "saldo_segun_banco": saldo_banco_empresa,
            "saldo_segun_contabilidad": saldo_contable,
            "saldo_ajustado_banco": saldo_banco_empresa,
            "saldo_ajustado_contabilidad": saldo_contable_calculado,
            "diferencia": diferencia,
            "estado": "conciliada" if conciliado else "pendiente_ajustes",
        })
        partidas_guardadas = self._guardar_todas_partidas(partidas)
        return {
            "conciliacion_id": reg.id,
            "metodo": "forma_2",
            "saldo_segun_banco": saldo_banco_empresa,
            "saldo_segun_contabilidad": saldo_contable,
            "saldo_contable_calculado": saldo_contable_calculado,
            "saldo_contable_ajustado": saldo_contable_calculado,
            "detalle_ajustes": {
                "cheques_no_debitados": -totales["cheques_no_debitados"],
                "depositos_no_acreditados": +totales["depositos_no_acreditados"],
                "notas_debito_no_registradas": +totales["notas_debito_no_registradas"],
                "notas_credito_no_registradas": -totales["notas_credito_no_registradas"],
            },
            "diferencia": diferencia,
            "conciliado": conciliado,
            "partidas_conciliatorias": [p.to_dict() for p in partidas_guardadas],
        }

    def conciliar_cuadrada(self) -> dict:
        """
        Forma 3 (Cuadrada): Ambas formas simultaneamente.
        Forma 1: Contabilidad → Banco  (saldo contable + ajustes = saldo banco)
        Forma 2: Banco → Contabilidad (saldo banco + ajustes = saldo contable)
        Si ambas se cumplen, la conciliacion esta cuadrada y no hay error.
        """
        self._limpiar_partidas_anteriores()
        cuenta = CuentaBancaria.obtener_por_id(self.cuenta_id)
        if not cuenta:
            raise ValueError(f"Cuenta {self.cuenta_id} no encontrada")

        ultima_conciliacion = Conciliacion.obtener_ultima(self.cuenta_id, antes_de=self.fecha_desde)

        saldo_banco_inicial = (
            self._saldo_inicial_banco
            if self._saldo_inicial_banco is not None
            else (
                ultima_conciliacion.saldo_ajustado_banco
                if ultima_conciliacion and ultima_conciliacion.saldo_ajustado_banco is not None
                else cuenta.saldo_inicial
            )
        )
        saldo_contable_inicial = (
            self._saldo_inicial_contable
            if self._saldo_inicial_contable is not None
            else (
                ultima_conciliacion.saldo_ajustado_contabilidad
                if ultima_conciliacion and ultima_conciliacion.saldo_ajustado_contabilidad is not None
                else cuenta.saldo_inicial
            )
        )

        partidas_anteriores = self._partidas_conciliatorias_mes_anterior()

        movs_banco = self._movimientos_banco_periodo()
        movs_contables = self._movimientos_contabilidad_periodo()
        neto_banco = sum(m["haber"] - m["debe"] for m in movs_banco)
        neto_contable = sum(m["debe"] - m["haber"] for m in movs_contables)

        saldo_banco_final = saldo_banco_inicial + neto_banco
        saldo_contable_final = saldo_contable_inicial + neto_contable
        saldo_banco_final_empresa = self._convertir_saldo_banco_a_empresa(saldo_banco_final)

        partidas = self._identificar_partidas_empresa()
        totales = self._agrupar_partidas(partidas)

        # Forma 1: Contabilidad → Banco
        saldo_banco_calculado = (
            saldo_contable_final
            + totales["cheques_no_debitados"]
            - totales["depositos_no_acreditados"]
            - totales["notas_debito_no_registradas"]
            + totales["notas_credito_no_registradas"]
        )
        dif_forma1 = round(saldo_banco_calculado - saldo_banco_final_empresa, 2)

        # Forma 2: Banco → Contabilidad
        saldo_contable_calculado = (
            saldo_banco_final_empresa
            - totales["cheques_no_debitados"]
            + totales["depositos_no_acreditados"]
            + totales["notas_debito_no_registradas"]
            - totales["notas_credito_no_registradas"]
        )
        dif_forma2 = round(saldo_contable_calculado - saldo_contable_final, 2)

        diferencia = max(abs(dif_forma1), abs(dif_forma2))
        conciliado = diferencia <= self._tolerancia
        reg = self._guardar_conciliacion({
            "fecha_cierre": self.fecha_hasta,
            "metodo": "cuadrada",
            "saldo_segun_banco": saldo_banco_final_empresa,
            "saldo_segun_contabilidad": saldo_contable_final,
            "saldo_ajustado_banco": saldo_banco_calculado,
            "saldo_ajustado_contabilidad": saldo_contable_calculado,
            "diferencia": diferencia,
            "estado": "conciliada" if conciliado else "pendiente_ajustes",
        })
        partidas_guardadas = self._guardar_todas_partidas(partidas)
        return {
            "conciliacion_id": reg.id,
            "metodo": "cuadrada",
            "conciliado": conciliado,
            "diferencia": diferencia,
            "saldos_apertura": {
                "conciliacion_id": ultima_conciliacion.id if ultima_conciliacion else None,
                "saldo_banco_inicial": saldo_banco_inicial,
                "saldo_contable_inicial": saldo_contable_inicial,
                "neto_banco": neto_banco,
                "neto_contable": neto_contable,
            },
            "saldos_finales": {
                "saldo_banco_final": saldo_banco_final_empresa,
                "saldo_contable_final": saldo_contable_final,
            },
            "partidas_mes_anterior": len(partidas_anteriores),
            "movimientos_periodo": {
                "cantidad_banco": len(movs_banco),
                "cantidad_contabilidad": len(movs_contables),
            },
            "forma_1": {
                "saldo_segun_contabilidad": saldo_contable_final,
                "ajustes": {
                    "cheques_no_debitados": +totales["cheques_no_debitados"],
                    "depositos_no_acreditados": -totales["depositos_no_acreditados"],
                    "notas_debito_no_registradas": -totales["notas_debito_no_registradas"],
                    "notas_credito_no_registradas": +totales["notas_credito_no_registradas"],
                },
                "saldo_banco_calculado": saldo_banco_calculado,
                "saldo_segun_banco": saldo_banco_final_empresa,
                "diferencia": dif_forma1,
            },
            "forma_2": {
                "saldo_segun_banco": saldo_banco_final_empresa,
                "ajustes": {
                    "cheques_no_debitados": -totales["cheques_no_debitados"],
                    "depositos_no_acreditados": +totales["depositos_no_acreditados"],
                    "notas_debito_no_registradas": +totales["notas_debito_no_registradas"],
                    "notas_credito_no_registradas": -totales["notas_credito_no_registradas"],
                },
                "saldo_contable_calculado": saldo_contable_calculado,
                "saldo_segun_contabilidad": saldo_contable_final,
                "diferencia": dif_forma2,
            },
            "saldo_banco_ajustado": saldo_banco_calculado,
            "saldo_contable_ajustado": saldo_contable_calculado,
            "partidas_conciliatorias": [p.to_dict() for p in partidas_guardadas],
        }
