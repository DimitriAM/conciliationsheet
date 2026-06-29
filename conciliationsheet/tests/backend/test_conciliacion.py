import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from unittest.mock import MagicMock, patch

from services.conciliador import ConciliadorBancario


PARTIDAS_VACIAS = {
    "cheques_no_debitados": [],
    "depositos_no_acreditados": [],
    "notas_debito_no_registradas": [],
    "notas_credito_no_registradas": [],
}

PARTIDAS_EJEMPLO = {
    "cheques_no_debitados": [{"monto": 500.0}],
    "depositos_no_acreditados": [{"monto": 300.0}],
    "notas_debito_no_registradas": [{"monto": 200.0}],
    "notas_credito_no_registradas": [{"monto": 100.0}],
}


class TestConciliacionForma1:
    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_guardar_conciliacion", return_value=MagicMock(id=1))
    @patch.object(ConciliadorBancario, "_guardar_todas_partidas", return_value=[])
    def test_retorna_vision_empresa(
        self, mock_guardar_todas, mock_guardar_conc, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        with patch.object(conciliador, "_identificar_partidas_empresa", return_value=PARTIDAS_VACIAS):
            result = conciliador.conciliar_forma_1()
        assert result["vision"] == "empresa"

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_guardar_conciliacion", return_value=MagicMock(id=1))
    @patch.object(ConciliadorBancario, "_guardar_todas_partidas", return_value=[])
    def test_signos_ajuste(
        self, mock_guardar_todas, mock_guardar_conc, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        with patch.object(conciliador, "_identificar_partidas_empresa", return_value=PARTIDAS_EJEMPLO):
            result = conciliador.conciliar_forma_1()
        assert result["ajustes_banco"]["cheques_no_debitados"] == -500.0
        assert result["ajustes_banco"]["depositos_no_acreditados"] == 300.0
        assert result["ajustes_contabilidad"]["notas_debito_no_registradas"] == -200.0
        assert result["ajustes_contabilidad"]["notas_credito_no_registradas"] == 100.0

    @patch.object(ConciliadorBancario, "_obtener_saldo_banco", return_value=10000.0)
    @patch.object(ConciliadorBancario, "_obtener_saldo_contabilidad", return_value=9500.0)
    @patch.object(ConciliadorBancario, "_guardar_conciliacion", return_value=MagicMock(id=1))
    @patch.object(ConciliadorBancario, "_guardar_todas_partidas", return_value=[])
    def test_diferencia_calculada(
        self, mock_guardar_todas, mock_guardar_conc, mock_saldo_cont, mock_saldo_banco
    ):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        with patch.object(conciliador, "_identificar_partidas_empresa", return_value=PARTIDAS_EJEMPLO):
            result = conciliador.conciliar_forma_1()
        # saldo_banco_ajustado = 10000 - 500 + 300 = 9800
        # saldo_contable_ajustado = 9500 - 200 + 100 = 9400
        # diferencia = 9800 - 9400 = 400
        assert result["saldo_banco_ajustado"] == 9800.0
        assert result["saldo_contable_ajustado"] == 9400.0
        assert result["diferencia"] == 400.0


class TestPartidasClasificacion:
    @patch("services.conciliador.PartidaConciliatoria.to_dict", return_value={})
    @patch("services.conciliador.PartidaConciliatoria.guardar")
    def test_cheque_es_transitoria(self, mock_guardar, mock_to_dict):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        item = {"fecha": "2025-06-15", "descripcion": "Cheque 001", "monto": 500.0, "comprobante": "C-001"}
        pc = conciliador._guardar_partida_conciliatoria("cheques_no_debitados", item)
        assert pc.tipo == "transitoria"
        assert pc.origen == "contabilidad_no_banco"
        assert pc.debe == 500.0
        assert pc.haber == 0.0

    @patch("services.conciliador.PartidaConciliatoria.to_dict", return_value={})
    @patch("services.conciliador.PartidaConciliatoria.guardar")
    def test_deposito_es_transitoria(self, mock_guardar, mock_to_dict):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        item = {"fecha": "2025-06-15", "descripcion": "Deposito 001", "monto": 300.0}
        pc = conciliador._guardar_partida_conciliatoria("depositos_no_acreditados", item)
        assert pc.tipo == "transitoria"
        assert pc.debe == 0.0
        assert pc.haber == 300.0

    @patch("services.conciliador.PartidaConciliatoria.to_dict", return_value={})
    @patch("services.conciliador.PartidaConciliatoria.guardar")
    def test_nota_debito_es_permanente(self, mock_guardar, mock_to_dict):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        item = {"fecha": "2025-06-30", "descripcion": "Comision bancaria", "monto": 35.0, "tipo": "ND"}
        pc = conciliador._guardar_partida_conciliatoria("notas_debito_no_registradas", item)
        assert pc.tipo == "permanente"
        assert pc.origen == "banco_no_contabilizado"
        assert pc.debe == 35.0
        assert pc.haber == 0.0

    @patch("services.conciliador.PartidaConciliatoria.to_dict", return_value={})
    @patch("services.conciliador.PartidaConciliatoria.guardar")
    def test_nota_credito_es_permanente(self, mock_guardar, mock_to_dict):
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        item = {"fecha": "2025-06-30", "descripcion": "Interes ganado", "monto": 50.0, "tipo": "NC"}
        pc = conciliador._guardar_partida_conciliatoria("notas_credito_no_registradas", item)
        assert pc.tipo == "permanente"
        assert pc.debe == 0.0
        assert pc.haber == 50.0


class TestConciliacionCuadrada:
    @patch.object(ConciliadorBancario, "_guardar_conciliacion", return_value=MagicMock(id=1))
    @patch.object(ConciliadorBancario, "_guardar_todas_partidas", return_value=[])
    @patch.object(ConciliadorBancario, "_partidas_conciliatorias_mes_anterior", return_value=[])
    @patch.object(ConciliadorBancario, "_movimientos_banco_periodo", return_value=[])
    @patch.object(ConciliadorBancario, "_movimientos_contabilidad_periodo", return_value=[])
    @patch("services.conciliador.CuentaBancaria.obtener_por_id")
    @patch("services.conciliador.Conciliacion.obtener_ultima", return_value=None)
    def test_verifica_ambos_lados(
        self, mock_obtener_ultima, mock_cuenta,
        mock_mov_cont, mock_mov_banco, mock_partidas_ant,
        mock_guardar_todas, mock_guardar_conc
    ):
        mock_cuenta.return_value = MagicMock(saldo_inicial=8000.0)
        conciliador = ConciliadorBancario(1, "2025-06-01", "2025-06-30")
        with patch.object(conciliador, "_identificar_partidas_empresa", return_value=PARTIDAS_VACIAS):
            result = conciliador.conciliar_cuadrada()
        assert result["metodo"] == "cuadrada"
        assert result["vision"] == "empresa"
        assert result["saldo_banco_ajustado"] == 8000.0
        assert result["saldo_contable_ajustado"] == 8000.0
        assert result["diferencia"] == 0.0
        assert result["conciliado"] is True
