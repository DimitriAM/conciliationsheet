import difflib

from database.db import get_connection
from models.conciliacion import Conciliacion
from models.partida_conciliatoria import PartidaConciliatoria
from utils.helpers import coinciden_descripciones


class ConciliadorBancario:
    def __init__(self):
        self.cuenta_id = None
        self.fecha_desde = None
        self.fecha_hasta = None
        self._tolerancia = 0.01

    STOPWORDS = frozenset({
        "de", "la", "el", "en", "del", "con", "por", "para", "un", "una",
        "al", "lo", "los", "las", "su", "se", "no", "es", "y", "e", "a",
        "que", "le", "x", "s", "p", "c", "d",
    })

    @staticmethod
    def _clasificar_por_tipo(tipo: str) -> str:
        return "transitoria" if tipo in ("cheque_no_debitado", "deposito_no_acreditado") else "permanente"

    @staticmethod
    def _comparten_palabras_clave(a: str, b: str) -> bool:
        if not a or not b:
            return False
        tokens_a = {w for w in a.lower().split() if len(w) > 2}
        tokens_b = {w for w in b.lower().split() if len(w) > 2}
        tokens_a -= ConciliadorBancario.STOPWORDS
        tokens_b -= ConciliadorBancario.STOPWORDS
        return bool(tokens_a & tokens_b)

    def _descripciones_similares(self, a: str, b: str) -> bool:
        if coinciden_descripciones(a, b):
            return True
        if not a or not b:
            return False
        if self._comparten_palabras_clave(a, b):
            return True
        ratio = difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()
        return ratio > 0.6

    def _obtener_saldo_banco(self) -> float:
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT saldo FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha <= ?
                   ORDER BY fecha DESC, id DESC LIMIT 1""",
                (self.cuenta_id, self.fecha_hasta),
            ).fetchone()
            if row is None:
                return 0.0
            saldo = row["saldo"]
            if saldo is not None and isinstance(saldo, (int, float)):
                return float(saldo)
            fallback = conn.execute(
                """SELECT COALESCE(SUM(haber), 0) - COALESCE(SUM(debe), 0) AS saldo
                   FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha <= ?""",
                (self.cuenta_id, self.fecha_hasta),
            ).fetchone()
            return round(fallback["saldo"], 2) if fallback else 0.0
        finally:
            conn.close()

    def _obtener_saldo_contabilidad(self) -> float:
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT saldo FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha <= ?
                   ORDER BY fecha DESC, id DESC LIMIT 1""",
                (self.cuenta_id, self.fecha_hasta),
            ).fetchone()
            if row is None:
                return 0.0
            saldo = row["saldo"]
            if saldo is not None and isinstance(saldo, (int, float)):
                return float(saldo)
            fallback = conn.execute(
                """SELECT COALESCE(SUM(debe), 0) - COALESCE(SUM(haber), 0) AS saldo
                   FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha <= ?""",
                (self.cuenta_id, self.fecha_hasta),
            ).fetchone()
            return round(fallback["saldo"], 2) if fallback else 0.0
        finally:
            conn.close()

    def _identificar_partidas(self) -> list[dict]:
        conn = get_connection()
        try:
            # Obtener todos los registros del periodo
            contables = conn.execute(
                """SELECT * FROM movimientos_contables
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            contables = [dict(r) for r in contables]

            bancos = conn.execute(
                """SELECT * FROM movimientos_bancarios
                   WHERE cuenta_id=? AND fecha BETWEEN ? AND ?
                   ORDER BY fecha, id""",
                (self.cuenta_id, self.fecha_desde, self.fecha_hasta),
            ).fetchall()
            bancos = [dict(r) for r in bancos]

            partidas = []
            ids_contable_usados = set()
            ids_banco_usados = set()

            # ─── FASE 1: diferencias por monto (misma fecha, desc similar, monto distinto) ───

            for mc in contables:
                if mc["id"] in ids_contable_usados:
                    continue
                for mb in bancos:
                    if mb["id"] in ids_banco_usados:
                        continue
                    if mc["fecha"] != mb["fecha"]:
                        continue
                    if not self._descripciones_similares(mc["descripcion"] or "", mb["descripcion"] or ""):
                        continue

                    def _agregar_diferencia(tipo, monto, signo, fecha, desc, origen,
                                              monto_cont=None, signo_cont=None,
                                              monto_banco=None, signo_banco=None):
                        if abs(monto) >= self._tolerancia:
                            ids_contable_usados.add(mc["id"])
                            ids_banco_usados.add(mb["id"])
                            partida = {
                                "fecha": fecha,
                                "descripcion": desc,
                                "monto": round(abs(monto), 2),
                                "signo": signo,
                                "origen": origen,
                                "tipo": tipo,
                                "afecta": "banco" if origen == "contabilidad" else "contabilidad",
                            }
                            if monto_cont is not None:
                                partida["_monto_cont"] = round(monto_cont, 2)
                                partida["_signo_cont"] = signo_cont
                                partida["_monto_banco"] = round(monto_banco, 2)
                                partida["_signo_banco"] = signo_banco
                            partidas.append(partida)
                            return True
                        return False

                    diff = 0
                    # HABER <-> DEBE: egreso/cargo (ambos reducen saldo)
                    if mc["haber"] > 0 and mb["debe"] > 0:
                        diff = mc["haber"] - mb["debe"]
                        if abs(diff) >= self._tolerancia:
                            mc_amt = mc["haber"]
                            mb_amt = mb["debe"]
                            if diff > 0:
                                _agregar_diferencia("diferencia_contabilidad", diff, 1, mc["fecha"], mc["descripcion"], "contabilidad",
                                    monto_cont=mc_amt, signo_cont=1, monto_banco=mb_amt, signo_banco=-1)
                            else:
                                _agregar_diferencia("diferencia_banco", diff, -1, mb["fecha"], mb["descripcion"], "banco",
                                    monto_cont=mc_amt, signo_cont=1, monto_banco=mb_amt, signo_banco=-1)
                            break

                    # DEBE <-> HABER: ingreso/abono (ambos aumentan saldo)
                    elif mc["debe"] > 0 and mb["haber"] > 0:
                        diff = mc["debe"] - mb["haber"]
                        if abs(diff) >= self._tolerancia:
                            mc_amt = mc["debe"]
                            mb_amt = mb["haber"]
                            if diff > 0:
                                _agregar_diferencia("diferencia_contabilidad", diff, -1, mc["fecha"], mc["descripcion"], "contabilidad",
                                    monto_cont=mc_amt, signo_cont=-1, monto_banco=mb_amt, signo_banco=1)
                            else:
                                _agregar_diferencia("diferencia_banco", diff, 1, mb["fecha"], mb["descripcion"], "banco",
                                    monto_cont=mc_amt, signo_cont=-1, monto_banco=mb_amt, signo_banco=1)
                            break

                    # DEBE <-> DEBE: ambos cargos/debitos
                    if mc["debe"] > 0 and mb["debe"] > 0:
                        diff = mc["debe"] - mb["debe"]
                        if abs(diff) >= self._tolerancia:
                            mc_amt = mc["debe"]
                            mb_amt = mb["debe"]
                            if diff > 0:
                                _agregar_diferencia("diferencia_contabilidad", diff, 1, mc["fecha"], mc["descripcion"], "contabilidad",
                                    monto_cont=mc_amt, signo_cont=1, monto_banco=mb_amt, signo_banco=-1)
                            else:
                                _agregar_diferencia("diferencia_banco", diff, -1, mb["fecha"], mb["descripcion"], "banco",
                                    monto_cont=mc_amt, signo_cont=1, monto_banco=mb_amt, signo_banco=-1)
                            break

                    # HABER <-> HABER: ambos ingresos/acreditaciones
                    if mc["haber"] > 0 and mb["haber"] > 0:
                        diff = mc["haber"] - mb["haber"]
                        if abs(diff) >= self._tolerancia:
                            mc_amt = mc["haber"]
                            mb_amt = mb["haber"]
                            if diff > 0:
                                _agregar_diferencia("diferencia_contabilidad", diff, -1, mc["fecha"], mc["descripcion"], "contabilidad",
                                    monto_cont=mc_amt, signo_cont=-1, monto_banco=mb_amt, signo_banco=1)
                            else:
                                _agregar_diferencia("diferencia_banco", diff, 1, mb["fecha"], mb["descripcion"], "banco",
                                    monto_cont=mc_amt, signo_cont=-1, monto_banco=mb_amt, signo_banco=1)
                            break

            # ─── FASE 2: registros NO MATCH (sin contrapartida exacta por fecha+monto) ───

            # Construir sets para matching exacto (fecha, monto_redondeado)
            banco_exact_haber = set()
            banco_exact_debe = set()
            for mb in bancos:
                if mb["id"] not in ids_banco_usados:
                    if mb["haber"] > 0:
                        banco_exact_haber.add((mb["fecha"], round(mb["haber"], 2)))
                    if mb["debe"] > 0:
                        banco_exact_debe.add((mb["fecha"], round(mb["debe"], 2)))

            contable_exact_haber = set()
            contable_exact_debe = set()
            for mc in contables:
                if mc["id"] not in ids_contable_usados:
                    if mc["haber"] > 0:
                        contable_exact_haber.add((mc["fecha"], round(mc["haber"], 2)))
                    if mc["debe"] > 0:
                        contable_exact_debe.add((mc["fecha"], round(mc["debe"], 2)))

            # 2a. Cheques no debitados: contabilidad HABER sin match en banco DEBE
            for mc in contables:
                if mc["id"] in ids_contable_usados:
                    continue
                if mc["haber"] <= 0:
                    continue
                key = (mc["fecha"], round(mc["haber"], 2))
                if key not in banco_exact_debe:
                    partidas.append({
                        "fecha": mc["fecha"],
                        "descripcion": mc["descripcion"],
                        "monto": mc["haber"],
                        "signo": 1,
                        "origen": "contabilidad",
                        "tipo": "cheque_no_debitado",
                        "afecta": "banco",
                    })

            # 2b. Depositos no acreditados: contabilidad DEBE sin match en banco HABER
            for mc in contables:
                if mc["id"] in ids_contable_usados:
                    continue
                if mc["debe"] <= 0:
                    continue
                key = (mc["fecha"], round(mc["debe"], 2))
                if key not in banco_exact_haber:
                    partidas.append({
                        "fecha": mc["fecha"],
                        "descripcion": mc["descripcion"],
                        "monto": mc["debe"],
                        "signo": -1,
                        "origen": "contabilidad",
                        "tipo": "deposito_no_acreditado",
                        "afecta": "banco",
                    })

            # 2c. Notas de debito no registradas: banco DEBE sin match en contabilidad HABER
            for mb in bancos:
                if mb["id"] in ids_banco_usados:
                    continue
                if mb["debe"] <= 0:
                    continue
                key = (mb["fecha"], round(mb["debe"], 2))
                if key not in contable_exact_haber:
                    partidas.append({
                        "fecha": mb["fecha"],
                        "descripcion": mb["descripcion"],
                        "monto": mb["debe"],
                        "signo": -1,
                        "origen": "banco",
                        "tipo": "nota_debito_no_registrada",
                        "afecta": "contabilidad",
                    })

            # 2d. Notas de credito no registradas: banco HABER sin match en contabilidad DEBE
            for mb in bancos:
                if mb["id"] in ids_banco_usados:
                    continue
                if mb["haber"] <= 0:
                    continue
                key = (mb["fecha"], round(mb["haber"], 2))
                if key not in contable_exact_debe:
                    partidas.append({
                        "fecha": mb["fecha"],
                        "descripcion": mb["descripcion"],
                        "monto": mb["haber"],
                        "signo": 1,
                        "origen": "banco",
                        "tipo": "nota_credito_no_registrada",
                        "afecta": "contabilidad",
                    })

            for p in partidas:
                p["clasificacion"] = self._clasificar_por_tipo(p["tipo"])

            return partidas
        finally:
            conn.close()

    def _limpiar_partidas_anteriores(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM partidas_conciliatorias WHERE cuenta_id=?", (self.cuenta_id,))
            conn.commit()
        finally:
            conn.close()

    def _conciliar(self, cuenta_id: int, fecha_desde: str, fecha_hasta: str, metodo: str) -> dict:
        self.cuenta_id = cuenta_id
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta

        self._limpiar_partidas_anteriores()

        saldo_contable = self._obtener_saldo_contabilidad()
        saldo_banco = self._obtener_saldo_banco()
        partidas = self._identificar_partidas()

        total_transitorias = sum(p["monto"] * p["signo"] for p in partidas if p["clasificacion"] == "transitoria")
        total_permanentes = sum(p["monto"] * p["signo"] for p in partidas if p["clasificacion"] == "permanente")
        total_positivas = sum(p["monto"] * p["signo"] for p in partidas if p["signo"] == 1)
        total_negativas = sum(p["monto"] * p["signo"] for p in partidas if p["signo"] == -1)

        desde_contabilidad = metodo == "desde_contabilidad"
        signo_factor = 1 if desde_contabilidad else -1

        if desde_contabilidad:
            saldo_ajustado = round(saldo_contable + total_transitorias + total_permanentes, 2)
            diferencia = round(saldo_banco - saldo_ajustado, 2)
            label_inicio = "SALDO CONTABLE"
            label_final = "SALDO BANCO (segun extracto)"
            saldo_ajustado_banco = saldo_ajustado
            saldo_ajustado_contabilidad = saldo_contable
        else:
            saldo_ajustado = round(saldo_banco - total_transitorias - total_permanentes, 2)
            diferencia = round(saldo_contable - saldo_ajustado, 2)
            label_inicio = "SALDO BANCO (segun extracto)"
            label_final = "SALDO CONTABLE (segun libros)"
            saldo_ajustado_banco = saldo_banco
            saldo_ajustado_contabilidad = saldo_ajustado

        conciliado = abs(diferencia) <= self._tolerancia

        conciliacion = Conciliacion(
            cuenta_id=self.cuenta_id,
            fecha_cierre=self.fecha_hasta,
            metodo=metodo,
            vision="empresa",
            saldo_segun_banco=saldo_banco,
            saldo_segun_contabilidad=saldo_contable,
            saldo_ajustado_banco=saldo_ajustado_banco,
            saldo_ajustado_contabilidad=saldo_ajustado_contabilidad,
            diferencia_total=diferencia,
            estado="conciliada" if conciliado else "pendiente_ajustes",
        )
        conciliacion.guardar()

        partidas_guardadas = []
        for p in partidas:
            pc = PartidaConciliatoria(
                cuenta_id=self.cuenta_id,
                fecha=p["fecha"],
                descripcion=p["descripcion"],
                monto=p["monto"],
                signo=p["signo"],
                origen=p["origen"],
                tipo=p["tipo"],
                afecta=p["afecta"],
                clasificacion=p["clasificacion"],
                estado="pendiente",
            )
            pc.guardar()
            partidas_guardadas.append(pc)

        estado = "CONCILIADO" if conciliado else "PENDIENTE"

        partidas_ordenadas = sorted(partidas, key=lambda p: (p.get("fecha", ""), p.get("descripcion", "")))
        desarrollo = []
        saldo_inicial = saldo_contable if desde_contabilidad else saldo_banco
        saldo_parcial = saldo_inicial
        desarrollo.append({
            "fecha": "-",
            "descripcion": label_inicio,
            "monto": "-",
            "efecto": "-",
            "saldo_parcial": saldo_parcial,
        })
        for p in partidas_ordenadas:
            if "_monto_cont" in p:
                mc_monto = round(p["_monto_cont"] * p["_signo_cont"] * signo_factor, 2)
                saldo_parcial = round(saldo_parcial + mc_monto, 2)
                desarrollo.append({
                    "fecha": p["fecha"],
                    "descripcion": p["descripcion"] + " (Contabilidad)",
                    "monto": mc_monto,
                    "efecto": "Suma" if mc_monto > 0 else "Resta",
                    "saldo_parcial": saldo_parcial,
                })
                mb_monto = round(p["_monto_banco"] * p["_signo_banco"] * signo_factor, 2)
                saldo_parcial = round(saldo_parcial + mb_monto, 2)
                desarrollo.append({
                    "fecha": p["fecha"],
                    "descripcion": p["descripcion"] + " (Banco)",
                    "monto": mb_monto,
                    "efecto": "Suma" if mb_monto > 0 else "Resta",
                    "saldo_parcial": saldo_parcial,
                })
            else:
                monto_con_signo = round(p["monto"] * p["signo"] * signo_factor, 2)
                saldo_parcial = round(saldo_parcial + monto_con_signo, 2)
                desarrollo.append({
                    "fecha": p["fecha"],
                    "descripcion": p["descripcion"],
                    "monto": monto_con_signo,
                    "efecto": "Suma" if monto_con_signo > 0 else "Resta",
                    "saldo_parcial": saldo_parcial,
                })
        desarrollo.append({
            "fecha": "-",
            "descripcion": "SALDO CALCULADO",
            "monto": "-",
            "efecto": "-",
            "saldo_parcial": round(saldo_inicial + sum(p["monto"] * p["signo"] * signo_factor for p in partidas_ordenadas), 2),
        })
        desarrollo.append({
            "fecha": "-",
            "descripcion": label_final,
            "monto": "-",
            "efecto": "-",
            "saldo_parcial": saldo_contable if not desde_contabilidad else saldo_banco,
        })

        if desde_contabilidad:
            verificacion = round(saldo_contable + total_transitorias + total_permanentes, 2)
            check_ok = abs(verificacion - saldo_banco) <= self._tolerancia
            formula_label = "saldo_contable + total_transitorias + total_permanentes"
            verificacion_saldo_banco = saldo_banco
            diferencia_sobrante = round(saldo_banco - verificacion, 2)
        else:
            verificacion = round(saldo_banco - total_transitorias - total_permanentes, 2)
            check_ok = abs(verificacion - saldo_contable) <= self._tolerancia
            formula_label = "saldo_banco - total_transitorias - total_permanentes"
            verificacion_saldo_banco = saldo_contable
            diferencia_sobrante = round(saldo_contable - verificacion, 2)

        return {
            "conciliacion_id": conciliacion.id,
            "metodo": metodo,
            "saldo_segun_contabilidad": saldo_contable,
            "saldo_segun_banco": saldo_banco,
            "saldo_ajustado": round(saldo_ajustado, 2),
            "diferencia": diferencia,
            "conciliado": conciliado,
            "estado": estado,
            "detalle_ajustes": [
                {"tipo": p["tipo"], "descripcion": p["descripcion"], "monto": p["monto"], "signo": p["signo"]}
                for p in partidas
            ],
            "partidas_conciliatorias": [p.to_dict() for p in partidas_guardadas],
            "resumen": {
                "total_transitorias": round(total_transitorias, 2),
                "total_permanentes": round(total_permanentes, 2),
                "total_positivas": round(total_positivas, 2),
                "total_negativas": round(total_negativas, 2),
            },
            "desarrollo": desarrollo,
            "verificacion": {
                "formula": formula_label,
                "saldo_contable": saldo_contable,
                "total_transitorias": round(total_transitorias, 2),
                "total_permanentes": round(total_permanentes, 2),
                "resultado": verificacion,
                "saldo_banco": verificacion_saldo_banco,
                "diferencia_sobrante": diferencia_sobrante,
                "consistente": check_ok,
            },
        }

    def conciliar_forma_1(self, cuenta_id: int, fecha_desde: str, fecha_hasta: str) -> dict:
        return self._conciliar(cuenta_id, fecha_desde, fecha_hasta, "desde_contabilidad")

    def conciliar_forma_2(self, cuenta_id: int, fecha_desde: str, fecha_hasta: str) -> dict:
        return self._conciliar(cuenta_id, fecha_desde, fecha_hasta, "desde_banco")
