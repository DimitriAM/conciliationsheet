import csv
from pathlib import Path
from typing import Any, Optional

import openpyxl

from models.movimiento_bancario import MovimientoBancario
from models.movimiento_contable import MovimientoContable
from utils.helpers import detectar_columnas, parsear_monto, parsear_saldo, SINONIMOS
from utils.validators import sanitizar_descripcion


def _es_fila_encabezado(row: tuple) -> bool:
    sinonimos_planos = {s for lista in SINONIMOS.values() for s in lista}
    count = 0
    for cell in row:
        if cell is not None and str(cell).strip().lower() in sinonimos_planos:
            count += 1
    return count >= 2


def _parse_cell(valor):
    if valor is None:
        return None
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    return str(valor).strip()

def _extraer_valor(row, idx, default=None):
    return row[idx] if idx < len(row) else default

def leer_excel(ruta: str) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    wb.close()
    if not filas:
        return []

    header_idx = None
    for i, row in enumerate(filas):
        if _es_fila_encabezado(row):
            header_idx = i
            break

    if header_idx is None:
        return []

    headers = [str(h) if h is not None else "" for h in filas[header_idx]]
    columnas = detectar_columnas(headers)
    if not columnas:
        return []

    tiene_debe = "debe" in columnas
    tiene_haber = "haber" in columnas

    registros = []
    for row in filas[header_idx + 1:]:
        if all(cell is None for cell in row):
            continue
        registro = {}
        for clave, idx in columnas.items():
            valor = _extraer_valor(row, idx)
            if clave == "saldo":
                registro[clave] = parsear_saldo(valor) if valor is not None else 0.0
            elif clave in ("monto", "debe", "haber"):
                registro[clave] = parsear_monto(valor) if valor is not None else 0.0
            elif clave == "fecha":
                if valor is not None:
                    registro[clave] = _parse_cell(valor)
                else:
                    registro[clave] = ""
            else:
                registro[clave] = _parse_cell(valor) or ""
        registros.append(registro)
    return registros


def leer_csv(ruta: str, delimiter: str = ",") -> list[dict[str, Any]]:
    registros = []
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delimiter)
        filas = list(reader)
    if not filas:
        return []

    header_idx = None
    for i, row in enumerate(filas):
        vals = [str(c) if c else "" for c in row]
        if _es_fila_encabezado(tuple(vals)):
            header_idx = i
            break

    if header_idx is None:
        return []

    columnas = detectar_columnas(filas[header_idx])
    if not columnas:
        return []

    tiene_debe = "debe" in columnas
    tiene_haber = "haber" in columnas

    for row in filas[header_idx + 1:]:
        if all(cell.strip() == "" for cell in row):
            continue
        registro = {}
        for clave, idx in columnas.items():
            valor = row[idx] if idx < len(row) else ""
            if clave in ("monto", "debe", "haber"):
                registro[clave] = parsear_monto(valor)
            else:
                registro[clave] = valor.strip()
        registros.append(registro)
    return registros


def _clasificar_tipo_movimiento(descripcion: str) -> Optional[str]:
    desc = descripcion.upper()
    if any(p in desc for p in ("DEPOSITO", "DEPOSITO", "ACREDIT", "ACRE", "ABONO")):
        return "deposito"
    if any(p in desc for p in ("CHEQUE", "CHQUE")):
        return "cheque"
    if any(p in desc for p in ("COMISION", "COMIS", "GASTO")):
        return "comision"
    if any(p in desc for p in ("INTERES", "INTERE")):
        return "interes"
    if any(p in desc for p in ("NOTA DE DEBITO", "ND", "DEBITO")):
        return "nota_debito"
    if any(p in desc for p in ("NOTA DE CREDITO", "NC", "CREDITO")):
        return "nota_credito"
    if any(p in desc for p in ("SALDO INICIAL", "SALD INICIAL")):
        return "saldo_inicial"
    return None


def _detectar_delimitador(ruta: str) -> str:
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        muestra = f.read(2048)
    if ";" in muestra:
        return ";"
    return ","

def procesar_archivo_a_movimientos(
    ruta: str, cuenta_id: int, fuente: str
) -> list:
    ext = Path(ruta).suffix.lower()
    if ext in (".xlsx", ".xls"):
        datos = leer_excel(ruta)
    elif ext == ".csv":
        delimiter = _detectar_delimitador(ruta)
        datos = leer_csv(ruta, delimiter)
    else:
        raise ValueError(f"Formato no soportado: {ext}")

    movimientos = []
    for d in datos:
        fecha = d.get("fecha", "")
        descripcion = sanitizar_descripcion(d.get("descripcion", ""))
        saldo_valor = d.get("saldo", None)
        tiene_debe_haber = "debe" in d and "haber" in d

        if tiene_debe_haber:
            debe = d["debe"]
            haber = d["haber"]
            tipo_mov = _clasificar_tipo_movimiento(descripcion) if descripcion else None
        else:
            monto = d.get("monto", 0.0)
            tipo_mov = _clasificar_tipo_movimiento(descripcion)
            if tipo_mov is None:
                continue
            if fuente == "banco":
                debe = monto if tipo_mov in ("comision", "cheque", "nota_debito") else 0.0
                haber = monto if tipo_mov in ("deposito", "nota_credito") else 0.0
            else:
                debe = monto if tipo_mov in ("deposito", "nota_credito") else 0.0
                haber = monto if tipo_mov in ("comision", "cheque", "nota_debito") else 0.0

        if fuente == "banco":
            movimientos.append(MovimientoBancario(
                cuenta_id=cuenta_id,
                fecha=fecha,
                descripcion=descripcion,
                debe=debe,
                haber=haber,
                saldo=saldo_valor,
                tipo=tipo_mov,
            ))
        else:
            movimientos.append(MovimientoContable(
                cuenta_id=cuenta_id,
                fecha=fecha,
                descripcion=descripcion,
                debe=debe,
                haber=haber,
                saldo=saldo_valor,
            ))

    return movimientos
