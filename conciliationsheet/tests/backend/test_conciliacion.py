import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from unittest.mock import MagicMock, patch

from services.conciliador import ConciliadorBancario


def _make_mock_result(data):
    m = MagicMock()
    m.fetchall.return_value = data
    return m

def _mock_conn(mock_get_conn, side_effects):
    conn = MagicMock()
    mock_get_conn.return_value = conn
    conn.execute.side_effect = [_make_mock_result(se) for se in side_effects]
    return conn


class TestSaldos:
    @patch("services.conciliador.get_connection")
    def test_saldo_contable_ultimo_registro(self, mock_get_conn):
        conn = MagicMock()
        mock_get_conn.return_value = conn
        row = MagicMock()
        row.__getitem__.side_effect = lambda k: {"saldo": 15000.0}[k]
        conn.execute.return_value.fetchone.return_value = row

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_hasta = "2025-06-30"
        saldo = conciliador._obtener_saldo_contabilidad()

        assert saldo == 15000.0
        sql_llamado = conn.execute.call_args[0][0]
        assert "ORDER BY fecha DESC, id DESC LIMIT 1" in sql_llamado
        assert "sum" not in sql_llamado.lower()

    @patch("services.conciliador.get_connection")
    def test_saldo_banco_ultimo_registro(self, mock_get_conn):
        conn = MagicMock()
        mock_get_conn.return_value = conn
        row = MagicMock()
        row.__getitem__.side_effect = lambda k: {"saldo": 25000.0}[k]
        conn.execute.return_value.fetchone.return_value = row

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_hasta = "2025-06-30"
        saldo = conciliador._obtener_saldo_banco()

        assert saldo == 25000.0
        sql_llamado = conn.execute.call_args[0][0]
        assert "ORDER BY fecha DESC, id DESC LIMIT 1" in sql_llamado
        assert "sum" not in sql_llamado.lower()

    @patch("services.conciliador.get_connection")
    def test_saldo_sin_registros_retorna_cero(self, mock_get_conn):
        conn = MagicMock()
        mock_get_conn.return_value = conn
        conn.execute.return_value.fetchone.return_value = None

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_hasta = "2025-06-30"
        assert conciliador._obtener_saldo_contabilidad() == 0.0
        assert conciliador._obtener_saldo_banco() == 0.0


class TestIdentificarPartidas:
    @patch("services.conciliador.get_connection")
    def test_cheques_no_debitados(self, mock_get_conn):
        _mock_conn(mock_get_conn, [
            [{"id": 1, "fecha": "2025-06-15", "descripcion": "Cheque 001", "debe": 0, "haber": 500.0,
              "saldo": None, "comprobante": "C-001", "conciliado": 0, "cuenta_id": 1}],
            [],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "cheque_no_debitado"
        assert partidas[0]["monto"] == 500.0
        assert partidas[0]["signo"] == 1
        assert partidas[0]["origen"] == "contabilidad"
        assert partidas[0]["afecta"] == "banco"
        assert partidas[0]["clasificacion"] == "transitoria"

    @patch("services.conciliador.get_connection")
    def test_depositos_no_acreditados(self, mock_get_conn):
        _mock_conn(mock_get_conn, [
            [{"id": 2, "fecha": "2025-06-20", "descripcion": "Deposito 001", "debe": 300.0, "haber": 0,
              "saldo": None, "comprobante": None, "conciliado": 0, "cuenta_id": 1}],
            [],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "deposito_no_acreditado"
        assert partidas[0]["monto"] == 300.0
        assert partidas[0]["signo"] == -1

    @patch("services.conciliador.get_connection")
    def test_diferencia_contabilidad_banco(self, mock_get_conn):
        _mock_conn(mock_get_conn, [
            [{"id": 1, "fecha": "2025-06-15", "descripcion": "PAGO PROVEEDOR", "debe": 0, "haber": 500.0,
              "saldo": None, "comprobante": "C-001", "conciliado": 0, "cuenta_id": 1}],
            [{"id": 10, "fecha": "2025-06-15", "descripcion": "PAGO PROVEEDOR", "debe": 480.0, "haber": 0,
              "saldo": None, "tipo": "cheque", "conciliado": 0, "cuenta_id": 1}],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        # Debe generar 1 partida: diferencia_contabilidad (diferencia neta)
        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "diferencia_contabilidad"
        assert partidas[0]["origen"] == "contabilidad"
        assert partidas[0]["clasificacion"] == "permanente"
        assert partidas[0]["monto"] == 20.0
        assert partidas[0]["signo"] == 1

    @patch("services.conciliador.get_connection")
    def test_diferencia_fuzzy_matching(self, mock_get_conn):
        _mock_conn(mock_get_conn, [
            [{"id": 1, "fecha": "2025-06-15", "descripcion": "CHEQUE 001 PAGO PROVEEDOR", "debe": 0, "haber": 500.0,
              "saldo": None, "comprobante": "C-001", "conciliado": 0, "cuenta_id": 1}],
            [{"id": 10, "fecha": "2025-06-15", "descripcion": "CHEQUE 002 PAGO PROVEEDOR", "debe": 480.0, "haber": 0,
              "saldo": None, "tipo": "cheque", "conciliado": 0, "cuenta_id": 1}],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "diferencia_contabilidad"
        assert partidas[0]["monto"] == 20.0
        assert partidas[0]["signo"] == 1

    @patch("services.conciliador.get_connection")
    def test_diferencia_mismo_lado_debe(self, mock_get_conn):
        """DEBE-DEBE: compra en contabilidad vs debito en banco, mismos keywords, montos distintos."""
        _mock_conn(mock_get_conn, [
            [{"id": 1, "fecha": "2025-06-15", "descripcion": "COMPRA DE ARTICULOS DE OFICINA", "debe": 500.0, "haber": 0,
              "saldo": None, "comprobante": "C-001", "conciliado": 0, "cuenta_id": 1}],
            [{"id": 10, "fecha": "2025-06-15", "descripcion": "DEBITO COMPRA - LIBRERIA", "debe": 480.0, "haber": 0,
              "saldo": None, "tipo": "cheque", "conciliado": 0, "cuenta_id": 1}],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "diferencia_contabilidad"
        assert partidas[0]["origen"] == "contabilidad"
        assert partidas[0]["monto"] == 20.0
        assert partidas[0]["signo"] == 1

    @patch("services.conciliador.get_connection")
    def test_diferencia_mismo_lado_haber(self, mock_get_conn):
        """HABER-HABER: abono en contabilidad vs nota credito en banco, mismos keywords, montos distintos."""
        _mock_conn(mock_get_conn, [
            [{"id": 1, "fecha": "2025-06-15", "descripcion": "COBRANZA CLIENTE A", "debe": 0, "haber": 1000.0,
              "saldo": None, "comprobante": "R-001", "conciliado": 0, "cuenta_id": 1}],
            [{"id": 10, "fecha": "2025-06-15", "descripcion": "ACREDITACION COBRANZA", "debe": 0, "haber": 980.0,
              "saldo": None, "tipo": "deposito", "conciliado": 0, "cuenta_id": 1}],
        ])

        conciliador = ConciliadorBancario()
        conciliador.cuenta_id = 1
        conciliador.fecha_desde = "2025-06-01"
        conciliador.fecha_hasta = "2025-06-30"
        partidas = conciliador._identificar_partidas()

        assert len(partidas) == 1
        assert partidas[0]["tipo"] == "diferencia_contabilidad"
        assert partidas[0]["monto"] == 20.0
        assert partidas[0]["signo"] == -1


class TestConciliacionForma1:
    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_conciliacion_exitosa_sin_partidas(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=[]):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria"):
                    result = conciliador.conciliar_forma_1(1, "2025-06-01", "2025-06-30")

        assert result["metodo"] == "desde_contabilidad"
        assert result["saldo_segun_contabilidad"] == 9500.0
        assert result["saldo_segun_banco"] == 10000.0
        assert result["saldo_ajustado"] == 9500.0
        assert result["diferencia"] == 500.0
        assert result["conciliado"] is False
        assert result["estado"] == "PENDIENTE"
        assert result["resumen"]["total_transitorias"] == 0.0
        assert result["resumen"]["total_permanentes"] == 0.0
        assert len(result["detalle_ajustes"]) == 0
        des = result["desarrollo"]
        assert len(des) == 3
        assert des[0]["descripcion"] == "SALDO CONTABLE"
        assert des[0]["saldo_parcial"] == 9500.0
        assert des[1]["descripcion"] == "SALDO CALCULADO"
        assert des[1]["saldo_parcial"] == 9500.0
        assert des[2]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[2]["saldo_parcial"] == 10000.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_conciliacion_con_partidas(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        partidas = [
            {"fecha": "2025-06-15", "descripcion": "Cheque 001", "monto": 500.0, "signo": 1,
             "origen": "contabilidad", "tipo": "cheque_no_debitado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2025-06-20", "descripcion": "Deposito 001", "monto": 300.0, "signo": -1,
             "origen": "contabilidad", "tipo": "deposito_no_acreditado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2025-06-30", "descripcion": "Comision", "monto": 200.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
        ]

        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=partidas):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria") as mock_part_cls:
                    mock_part = MagicMock()
                    mock_part.to_dict.return_value = {"id": 1}
                    mock_part_cls.return_value = mock_part
                    result = conciliador.conciliar_forma_1(1, "2025-06-01", "2025-06-30")

        # transitorias: 500*1 + 300*(-1) = 200; permanentes: 200*(-1) = -200
        # saldo_ajustado = 9500 + 200 - 200 = 9500
        assert result["saldo_ajustado"] == 9500.0
        assert result["diferencia"] == 500.0
        assert result["conciliado"] is False
        assert result["estado"] == "PENDIENTE"
        assert result["resumen"]["total_transitorias"] == 200.0
        assert result["resumen"]["total_permanentes"] == -200.0
        assert len(result["detalle_ajustes"]) == 3
        des = result["desarrollo"]
        assert len(des) == 6  # 1 + 3 partidas + 2 fin
        assert des[0]["saldo_parcial"] == 9500.0
        assert des[1]["saldo_parcial"] == 10000.0
        assert des[2]["saldo_parcial"] == 9700.0
        assert des[3]["saldo_parcial"] == 9500.0
        assert des[4]["descripcion"] == "SALDO CALCULADO"
        assert des[4]["saldo_parcial"] == 9500.0
        assert des[5]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[5]["saldo_parcial"] == 10000.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_conciliacion_conciliada(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=[]):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria"):
                    result = conciliador.conciliar_forma_1(1, "2025-06-01", "2025-06-30")

        assert result["diferencia"] == 0.0
        assert result["conciliado"] is True
        assert result["estado"] == "CONCILIADO"
        assert result["resumen"]["total_transitorias"] == 0.0
        assert result["resumen"]["total_permanentes"] == 0.0
        des = result["desarrollo"]
        assert len(des) == 3
        assert des[0]["descripcion"] == "SALDO CONTABLE"
        assert des[0]["saldo_parcial"] == 9500.0
        assert des[1]["descripcion"] == "SALDO CALCULADO"
        assert des[1]["saldo_parcial"] == 9500.0
        assert des[2]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[2]["saldo_parcial"] == 9500.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=1569500.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=1450000.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_conciliacion_ejemplo_completo(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        partidas = [
            {"fecha": "2026-07-10", "descripcion": "COMPRA DE ARTICULOS DE OFICINA", "monto": 20000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "diferencia_contabilidad", "afecta": "banco", "clasificacion": "permanente"},
            {"fecha": "2026-07-20", "descripcion": "PAGO DE ALQUILER COMERCIAL", "monto": 5000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "diferencia_contabilidad", "afecta": "banco", "clasificacion": "permanente"},
            {"fecha": "2026-07-28", "descripcion": "CHEQUE EMITIDO NRO 8821", "monto": 115000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "cheque_no_debitado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2026-07-29", "descripcion": "COMISION POR CHEQUERA", "monto": 8500.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
            {"fecha": "2026-07-31", "descripcion": "CARGO POR MANTENIMIENTO", "monto": 12000.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
        ]

        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=partidas):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria") as mock_part_cls:
                    mock_part = MagicMock()
                    mock_part.to_dict.return_value = {"id": 1}
                    mock_part_cls.return_value = mock_part
                    result = conciliador.conciliar_forma_1(1, "2026-07-01", "2026-07-31")

        # transitorias (solo cheque_no_debitado): 115000*1 = 115000
        # permanentes: 20000*1 + 5000*1 - 8500 - 12000 = 4500
        # saldo_ajustado = 1450000 + 115000 + 4500 = 1569500
        # diferencia = 1569500 - 1569500 = 0 -> CONCILIADO
        assert result["saldo_segun_contabilidad"] == 1450000.0
        assert result["saldo_segun_banco"] == 1569500.0
        assert result["resumen"]["total_transitorias"] == 115000.0
        assert result["resumen"]["total_permanentes"] == 4500.0
        assert result["resumen"]["total_positivas"] == 140000.0
        assert result["resumen"]["total_negativas"] == -20500.0
        assert result["saldo_ajustado"] == 1569500.0
        assert result["diferencia"] == 0.0
        assert result["conciliado"] is True
        assert result["estado"] == "CONCILIADO"
        assert len(result["detalle_ajustes"]) == 5

        # Verificar desarrollo
        des = result["desarrollo"]
        assert len(des) == 8  # 1 inicio + 5 partidas + 2 fin (calculado + banco)
        assert des[0]["descripcion"] == "SALDO CONTABLE"
        assert des[0]["saldo_parcial"] == 1450000.0
        assert des[1]["descripcion"] == "COMPRA DE ARTICULOS DE OFICINA"
        assert des[1]["monto"] == 20000.0
        assert des[1]["efecto"] == "Suma"
        assert des[1]["saldo_parcial"] == 1470000.0
        assert des[2]["descripcion"] == "PAGO DE ALQUILER COMERCIAL"
        assert des[2]["monto"] == 5000.0
        assert des[2]["efecto"] == "Suma"
        assert des[2]["saldo_parcial"] == 1475000.0
        assert des[3]["descripcion"] == "CHEQUE EMITIDO NRO 8821"
        assert des[3]["monto"] == 115000.0
        assert des[3]["efecto"] == "Suma"
        assert des[3]["saldo_parcial"] == 1590000.0
        assert des[4]["descripcion"] == "COMISION POR CHEQUERA"
        assert des[4]["monto"] == -8500.0
        assert des[4]["efecto"] == "Resta"
        assert des[4]["saldo_parcial"] == 1581500.0
        assert des[5]["descripcion"] == "CARGO POR MANTENIMIENTO"
        assert des[5]["monto"] == -12000.0
        assert des[5]["efecto"] == "Resta"
        assert des[5]["saldo_parcial"] == 1569500.0
        assert des[6]["descripcion"] == "SALDO CALCULADO"
        assert des[6]["saldo_parcial"] == 1569500.0
        assert des[7]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[7]["saldo_parcial"] == 1569500.0


class TestConciliacionForma2:
    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=1569500.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=1450000.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_forma2_con_partidas_conciliado(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        partidas = [
            {"fecha": "2026-07-10", "descripcion": "COMPRA DE ARTICULOS DE OFICINA", "monto": 20000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "diferencia_contabilidad", "afecta": "banco", "clasificacion": "permanente"},
            {"fecha": "2026-07-20", "descripcion": "PAGO DE ALQUILER COMERCIAL", "monto": 5000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "diferencia_contabilidad", "afecta": "banco", "clasificacion": "permanente"},
            {"fecha": "2026-07-28", "descripcion": "CHEQUE EMITIDO NRO 8821", "monto": 115000.0, "signo": 1,
             "origen": "contabilidad", "tipo": "cheque_no_debitado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2026-07-29", "descripcion": "COMISION POR CHEQUERA", "monto": 8500.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
            {"fecha": "2026-07-31", "descripcion": "CARGO POR MANTENIMIENTO", "monto": 12000.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
        ]

        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=partidas):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria") as mock_part_cls:
                    mock_part = MagicMock()
                    mock_part.to_dict.return_value = {"id": 1}
                    mock_part_cls.return_value = mock_part
                    result = conciliador.conciliar_forma_2(1, "2026-07-01", "2026-07-31")

        # En Forma 2 se resta del saldo banco:
        # transitorias: 115000*1 = 115000; permanentes: 20000+5000-8500-12000 = 4500
        # saldo_ajustado = 1569500 - 115000 - 4500 = 1450000 (= saldo contable)
        assert result["metodo"] == "desde_banco"
        assert result["saldo_segun_banco"] == 1569500.0
        assert result["saldo_segun_contabilidad"] == 1450000.0
        assert result["resumen"]["total_transitorias"] == 115000.0
        assert result["resumen"]["total_permanentes"] == 4500.0
        assert result["saldo_ajustado"] == 1450000.0
        assert result["diferencia"] == 0.0
        assert result["conciliado"] is True
        assert result["estado"] == "CONCILIADO"
        assert len(result["detalle_ajustes"]) == 5

        # Verificar desarrollo (inicia desde banco, termina en contabilidad)
        des = result["desarrollo"]
        assert len(des) == 8
        assert des[0]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[0]["saldo_parcial"] == 1569500.0
        # Partidas con signo invertido:
        assert des[1]["descripcion"] == "COMPRA DE ARTICULOS DE OFICINA"
        assert des[1]["monto"] == -20000.0
        assert des[1]["efecto"] == "Resta"
        assert des[1]["saldo_parcial"] == 1549500.0
        assert des[2]["descripcion"] == "PAGO DE ALQUILER COMERCIAL"
        assert des[2]["monto"] == -5000.0
        assert des[2]["efecto"] == "Resta"
        assert des[2]["saldo_parcial"] == 1544500.0
        assert des[3]["descripcion"] == "CHEQUE EMITIDO NRO 8821"
        assert des[3]["monto"] == -115000.0
        assert des[3]["efecto"] == "Resta"
        assert des[3]["saldo_parcial"] == 1429500.0
        assert des[4]["descripcion"] == "COMISION POR CHEQUERA"
        assert des[4]["monto"] == 8500.0
        assert des[4]["efecto"] == "Suma"
        assert des[4]["saldo_parcial"] == 1438000.0
        assert des[5]["descripcion"] == "CARGO POR MANTENIMIENTO"
        assert des[5]["monto"] == 12000.0
        assert des[5]["efecto"] == "Suma"
        assert des[5]["saldo_parcial"] == 1450000.0
        assert des[6]["descripcion"] == "SALDO CALCULADO"
        assert des[6]["saldo_parcial"] == 1450000.0
        assert des[7]["descripcion"] == "SALDO CONTABLE (segun libros)"
        assert des[7]["saldo_parcial"] == 1450000.0

        # Verificacion
        v = result["verificacion"]
        assert v["formula"] == "saldo_banco - total_transitorias - total_permanentes"
        assert v["resultado"] == 1450000.0
        assert v["saldo_banco"] == 1450000.0
        assert v["consistente"] is True

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_forma2_conciliacion_exitosa_sin_partidas(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=[]):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria"):
                    result = conciliador.conciliar_forma_2(1, "2025-06-01", "2025-06-30")

        # Sin partidas: saldo_ajustado = saldo_banco = 10000
        # diferencia = saldo_contable - saldo_ajustado = 9500 - 10000 = -500
        assert result["metodo"] == "desde_banco"
        assert result["saldo_segun_contabilidad"] == 9500.0
        assert result["saldo_segun_banco"] == 10000.0
        assert result["saldo_ajustado"] == 10000.0
        assert result["diferencia"] == -500.0
        assert result["conciliado"] is False
        assert result["estado"] == "PENDIENTE"

        des = result["desarrollo"]
        assert len(des) == 3
        assert des[0]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[0]["saldo_parcial"] == 10000.0
        assert des[1]["descripcion"] == "SALDO CALCULADO"
        assert des[1]["saldo_parcial"] == 10000.0
        assert des[2]["descripcion"] == "SALDO CONTABLE (segun libros)"
        assert des[2]["saldo_parcial"] == 9500.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_forma2_conciliacion_conciliada(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=[]):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria"):
                    result = conciliador.conciliar_forma_2(1, "2025-06-01", "2025-06-30")

        assert result["diferencia"] == 0.0
        assert result["conciliado"] is True
        assert result["estado"] == "CONCILIADO"
        des = result["desarrollo"]
        assert len(des) == 3
        assert des[0]["descripcion"] == "SALDO BANCO (segun extracto)"
        assert des[0]["saldo_parcial"] == 9500.0
        assert des[1]["descripcion"] == "SALDO CALCULADO"
        assert des[1]["saldo_parcial"] == 9500.0
        assert des[2]["descripcion"] == "SALDO CONTABLE (segun libros)"
        assert des[2]["saldo_parcial"] == 9500.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_limpiar_partidas_anteriores")
    def test_forma2_con_partidas(
        self, mock_limpiar, mock_saldo_cont, mock_saldo_banco
    ):
        partidas = [
            {"fecha": "2025-06-15", "descripcion": "Cheque 001", "monto": 500.0, "signo": 1,
             "origen": "contabilidad", "tipo": "cheque_no_debitado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2025-06-20", "descripcion": "Deposito 001", "monto": 300.0, "signo": -1,
             "origen": "contabilidad", "tipo": "deposito_no_acreditado", "afecta": "banco", "clasificacion": "transitoria"},
            {"fecha": "2025-06-30", "descripcion": "Comision", "monto": 200.0, "signo": -1,
             "origen": "banco", "tipo": "nota_debito_no_registrada", "afecta": "contabilidad", "clasificacion": "permanente"},
        ]

        conciliador = ConciliadorBancario()
        with patch.object(conciliador, "_identificar_partidas", return_value=partidas):
            with patch("services.conciliador.Conciliacion") as mock_conc_cls:
                mock_conc = MagicMock()
                mock_conc.id = 1
                mock_conc_cls.return_value = mock_conc
                with patch("services.conciliador.PartidaConciliatoria") as mock_part_cls:
                    mock_part = MagicMock()
                    mock_part.to_dict.return_value = {"id": 1}
                    mock_part_cls.return_value = mock_part
                    result = conciliador.conciliar_forma_2(1, "2025-06-01", "2025-06-30")

        # transitorias: 500*1 + 300*(-1) = 200; permanentes: 200*(-1) = -200
        # saldo_ajustado = 10000 - 200 + 200 = 10000
        # No concilia porque 10000 != 9500
        assert result["saldo_ajustado"] == 10000.0
        assert result["diferencia"] == -500.0
        assert result["conciliado"] is False
        assert result["resumen"]["total_transitorias"] == 200.0
        assert result["resumen"]["total_permanentes"] == -200.0
        des = result["desarrollo"]
        assert len(des) == 6
        assert des[0]["saldo_parcial"] == 10000.0
        assert des[1]["descripcion"] == "Cheque 001"
        assert des[1]["monto"] == -500.0  # signo invertido en Forma 2
        assert des[1]["saldo_parcial"] == 9500.0
        assert des[2]["descripcion"] == "Deposito 001"
        assert des[2]["monto"] == 300.0   # -(-1)*300 = +300
        assert des[2]["saldo_parcial"] == 9800.0
        assert des[3]["descripcion"] == "Comision"
        assert des[3]["monto"] == 200.0   # -(-1)*200 = +200
        assert des[3]["saldo_parcial"] == 10000.0
        assert des[4]["descripcion"] == "SALDO CALCULADO"
        assert des[4]["saldo_parcial"] == 10000.0
        assert des[5]["descripcion"] == "SALDO CONTABLE (segun libros)"
        assert des[5]["saldo_parcial"] == 9500.0
