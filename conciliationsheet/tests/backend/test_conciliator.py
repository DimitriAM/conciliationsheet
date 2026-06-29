import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from models.origen import Origen
from models.destino import Destino
from models.diferencia import Diferencia
from services.conciliator import conciliar, comparar_montos, _distancia_descripcion
from services.diff_analyzer import clasificar_diferencia
from utils.validators import validar_extension, validar_fuente, validar_monto, validar_fecha
from utils.helpers import detectar_columnas, parsear_monto


class TestValidators:
    def test_validar_extension(self):
        assert validar_extension("file.xlsx") is True
        assert validar_extension("file.csv") is True
        assert validar_extension("file.pdf") is False
        assert validar_extension("file.XLSX") is True

    def test_validar_fuente(self):
        assert validar_fuente("banco") is True
        assert validar_fuente("contabilidad") is True
        assert validar_fuente("tarjeta") is True
        assert validar_fuente("cuenta_corriente") is True
        assert validar_fuente("invalido") is False

    def test_validar_monto(self):
        assert validar_monto(100.0) is True
        assert validar_monto(0) is True
        assert validar_monto(-100) is False  # negative values are invalid
        assert validar_monto("abc") is False

    def test_validar_fecha(self):
        assert validar_fecha("2024-01-15") is True
        assert validar_fecha("15/01/2024") is False
        assert validar_fecha("") is False


class TestHelpers:
    def test_detectar_columnas(self):
        headers = ["Fecha", "Descripcion", "Monto", "Saldo", "Tipo"]
        cols = detectar_columnas(headers)
        assert cols["fecha"] == 0
        assert cols["descripcion"] == 1
        assert cols["monto"] == 2
        assert cols["saldo"] == 3
        assert cols["tipo"] == 4

    def test_detectar_columnas_sinonimos(self):
        headers = ["Date", "Description", "Amount", "Balance"]
        cols = detectar_columnas(headers)
        assert cols["fecha"] == 0
        assert cols["descripcion"] == 1
        assert cols["monto"] == 2
        assert cols["saldo"] == 3

    def test_parsear_monto(self):
        assert parsear_monto(1234.56) == 1234.56
        assert parsear_monto("$1,234.56") == 1234.56
        assert parsear_monto("1,234.56") == 1234.56
        assert parsear_monto(0) == 0.0
        assert parsear_monto("abc") == 0.0


class TestConciliator:
    def test_origenes_destinos_iguales_no_diferencias(self):
        origenes = [
            Origen(fecha="2024-01-15", descripcion="PAGO PROVEEDOR", monto=1500.0),
            Origen(fecha="2024-01-16", descripcion="COBRO CLIENTE", monto=3000.0),
        ]
        destinos = [
            Destino(fecha="2024-01-15", descripcion="PAGO PROVEEDOR", monto=1500.0),
            Destino(fecha="2024-01-16", descripcion="COBRO CLIENTE", monto=3000.0),
        ]
        result = conciliar(origenes, destinos)
        assert len(result) == 0

    def test_origen_extra_encontrado(self):
        origenes = [
            Origen(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
            Origen(fecha="2024-01-16", descripcion="PAGO B", monto=2000.0),
        ]
        destinos = [
            Destino(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
        ]
        result = conciliar(origenes, destinos)
        assert len(result) == 1
        assert result[0].monto_origen == 2000.0
        assert result[0].monto_destino is None

    def test_destino_extra_encontrado(self):
        origenes = [
            Origen(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
        ]
        destinos = [
            Destino(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
            Destino(fecha="2024-01-16", descripcion="PAGO B", monto=2000.0),
        ]
        result = conciliar(origenes, destinos)
        assert len(result) == 1
        assert result[0].monto_destino == 2000.0
        assert result[0].monto_origen is None

    def test_montos_coincidentes_sin_diferencia(self):
        origenes = [
            Origen(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
        ]
        destinos = [
            Destino(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
        ]
        result = conciliar(origenes, destinos)
        assert len(result) == 0

    def test_descripcion_similar_con_diferencia_monto_crea_diferencia(self):
        origenes = [
            Origen(fecha="2024-01-15", descripcion="PAGO A", monto=1000.0),
        ]
        destinos = [
            Destino(fecha="2024-01-15", descripcion="PAGO A", monto=900.0),
        ]
        result = conciliar(origenes, destinos)
        assert len(result) == 2  # both become unmatched since montos differ beyond tolerance

    def test_comparar_montos(self):
        assert comparar_montos(100.0, 100.0) is True
        assert comparar_montos(100.0, 100.005) is True
        assert comparar_montos(100.0, 100.02) is False

    def test_distancia_descripcion(self):
        dist = _distancia_descripcion("PAGO PROVEEDOR", "PAGO PROVEEDOR")
        assert dist == 0.0
        dist = _distancia_descripcion("PAGO A", "PAGO B")
        assert round(dist, 2) == 0.67
        dist = _distancia_descripcion("", "PAGO")
        assert dist == float("inf")


class TestDiffAnalyzer:
    def test_transitoria_menor_2_porciento(self):
        d = Diferencia(monto_origen=100.0, monto_destino=98.5, diferencia=1.5)
        assert clasificar_diferencia(d) == "transitoria"

    def test_permanente_mayor_10_porciento(self):
        d = Diferencia(monto_origen=100.0, monto_destino=80.0, diferencia=20.0)
        assert clasificar_diferencia(d) == "permanente"

    def test_solo_origen_permanente(self):
        d = Diferencia(monto_origen=100.0, monto_destino=None, diferencia=100.0)
        assert clasificar_diferencia(d) == "permanente"

    def test_solo_destino_permanente(self):
        d = Diferencia(monto_origen=None, monto_destino=100.0, diferencia=-100.0)
        assert clasificar_diferencia(d) == "permanente"
