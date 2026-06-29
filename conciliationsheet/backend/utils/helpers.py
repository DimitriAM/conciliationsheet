import csv
import os
import uuid
from pathlib import Path
from typing import Any

from config import UPLOADS_DIR


def generar_nombre_unico(original: str) -> str:
    ext = Path(original).suffix
    return f"{uuid.uuid4().hex}{ext}"


def guardar_archivo(archivo_bytes: bytes, nombre: str) -> str:
    nombre_unico = generar_nombre_unico(nombre)
    ruta = UPLOADS_DIR / nombre_unico
    ruta.write_bytes(archivo_bytes)
    return str(ruta)


SINONIMOS = {
    "fecha": ["fecha", "date", "fecha de transaccion", "fecha transaccion",
              "fecha de transacción", "fecha transacción"],
    "descripcion": ["descripcion", "description", "detalle", "concepto", "glosa",
                    "descripción"],
    "monto": ["monto", "amount", "importe", "valor", "total", "monto \$"],
    "debe": ["debe", "debito", "débito", "deudor", "cargo", "egreso"],
    "haber": ["haber", "credito", "crédito", "acreedor", "abono", "ingreso"],
    "tipo": ["tipo", "type", "operacion", "movimiento", "operación"],
    "saldo": ["saldo", "balance", "saldo acumulado", "saldo final"],
}


def detectar_columnas(headers: list[str]) -> dict[str, int]:
    mapeo = {}
    for i, h in enumerate(headers):
        h_lower = h.strip().lower()
        for clave, sinonimos_lista in SINONIMOS.items():
            if h_lower in sinonimos_lista:
                mapeo[clave] = i
                break
    return mapeo


SINONIMOS_DESCRIPCION = {
    "cheque": ["cheque", "cheq", "chq", "cheque emitido", "cheque librado",
               "cheque pagado", "pago cheque", "cheque nro", "cheque no"],
    "deposito": ["deposito", "depósito", "dep", "acreditacion", "acreditación",
                 "acredito", "abono", "ingreso", "deposito efectivo", "depósito efectivo"],
    "nota_debito": ["nota debito", "nota débito", "nota de debito", "nota de débito",
                    "nd", "debito bancario", "débito bancario", "cargo bancario"],
    "nota_credito": ["nota credito", "nota crédito", "nota de credito", "nota de crédito",
                     "nc", "credito bancario", "crédito bancario"],
    "comision": ["comision", "comisión", "comis", "comisiones", "gasto",
                 "gastos bancarios", "mantenimiento", "comision bancaria"],
    "interes": ["interes", "interés", "intereses", "interes bancario", "interés bancario"],
    "transferencia": ["transferencia", "transf", "transfer", "envio", "envío",
                      "giro", "transferencia bancaria"],
    "saldo_inicial": ["saldo inicial", "saldo anterior", "saldo inicio", "saldo inicial"],
}

def normalizar_descripcion(desc: str) -> str:
    desc = desc.strip().lower()
    for canon, sinonimos in SINONIMOS_DESCRIPCION.items():
        for s in sinonimos:
            if s in desc:
                return canon
    return desc

def coinciden_descripciones(desc_a: str, desc_b: str) -> bool:
    return normalizar_descripcion(desc_a) == normalizar_descripcion(desc_b)

def normalizar_valor(texto: str) -> str:
    return texto.strip().upper()


def parsear_monto(valor: Any) -> float:
    if isinstance(valor, (int, float)):
        return abs(float(valor))
    if isinstance(valor, str):
        limpio = valor.replace("$", "").replace(",", "").replace(" ", "").strip()
        try:
            return abs(float(limpio))
        except ValueError:
            return 0.0
    return 0.0
