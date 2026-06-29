import re
from pathlib import Path
from typing import Optional

from config import ALLOWED_EXTENSIONS


def validar_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validar_fuente(fuente: str) -> bool:
    return fuente in {"banco", "tarjeta", "cuenta_corriente", "contabilidad"}


TIPOS_VALIDOS = {"ingreso", "egreso", "debito", "credito"}


def validar_tipo_movimiento(tipo: Optional[str]) -> bool:
    if tipo is None:
        return True
    return tipo in TIPOS_VALIDOS


def normalizar_tipo(tipo: Optional[str]) -> Optional[str]:
    if tipo is None:
        return None
    tipo_lower = tipo.strip().lower()
    return tipo_lower if tipo_lower in TIPOS_VALIDOS else None


def validar_monto(monto: float) -> bool:
    try:
        return float(monto) >= 0
    except (TypeError, ValueError):
        return False


def validar_fecha(fecha: str) -> bool:
    patron = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(patron, fecha))


import unicodedata


def sanitizar_descripcion(texto: str) -> str:
    texto = texto.strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto
