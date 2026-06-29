from openpyxl import Workbook
from pathlib import Path

BASE = Path(__file__).resolve().parent / "data" / "uploads"
BASE.mkdir(parents=True, exist_ok=True)


def escribir_excel(nombre, headers, datos):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in datos:
        ws.append(row)
    ruta = BASE / nombre
    wb.save(str(ruta))
    print(f"  {ruta.name}  ({len(datos)} registros)")
    return ruta


# ── BANCO (fuente = banco → destino) ──
banco_headers = ["Fecha", "Descripción", "Monto", "Saldo", "Tipo"]
banco_data = [
    ["2025-06-01", "Saldo inicial", 0, 1250000, "ingreso"],
    ["2025-06-02", "Transferencia recibida - Cliente A", 450000, 1700000, "ingreso"],
    ["2025-06-03", "Pago proveedor - Servicios Generales", 180000, 1520000, "egreso"],
    ["2025-06-05", "Depósito efectivo - Sucursal", 600000, 2120000, "ingreso"],
    ["2025-06-07", "Transferencia emitida - Proveedor B", 320000, 1800000, "egreso"],
    ["2025-06-10", "Cobro tarjeta - Cliente C", 250000, 2050000, "ingreso"],
    ["2025-06-12", "Pago impuesto mensual", 95000, 1955000, "egreso"],
    ["2025-06-15", "Transferencia recibida - Cliente D", 700000, 2655000, "ingreso"],
    ["2025-06-18", "Pago alquiler local", 280000, 2375000, "egreso"],
    ["2025-06-20", "Honorarios contables", 120000, 2255000, "egreso"],
    ["2025-06-22", "Depósito cliente E", 380000, 2635000, "ingreso"],
    ["2025-06-25", "Transferencia - Proveedor F", 150000, 2485000, "egreso"],
    ["2025-06-28", "Pago servicios (luz/agua)", 67000, 2418000, "egreso"],
    ["2025-06-30", "Comisión bancaria mensual", 35000, 2383000, "egreso"],
]

# ── CONTABILIDAD (fuente = contabilidad → origen) ──
cont_headers = ["Fecha", "Descripción", "Monto", "Cuenta", "Tipo"]
cont_data = [
    # Coinciden con banco (8 registros)
    ["2025-06-02", "Cobro factura A-001 - Cliente A", 450000, "Banco Nación", "ingreso"],
    ["2025-06-03", "Pago factura PROV-001 - Servicios Generales", 180000, "Banco Nación", "egreso"],
    ["2025-06-10", "Cobro factura C-001 - Cliente C", 250000, "Banco Nación", "ingreso"],
    ["2025-06-15", "Cobro factura D-001 - Cliente D", 700000, "Banco Nación", "ingreso"],
    ["2025-06-18", "Pago alquiler mes junio", 280000, "Banco Nación", "egreso"],
    ["2025-06-20", "Pago honorarios contables", 120000, "Banco Nación", "egreso"],
    ["2025-06-25", "Pago factura PROV-002 - Proveedor F", 150000, "Banco Nación", "egreso"],
    ["2025-06-28", "Pago servicios públicos", 67000, "Banco Nación", "egreso"],
    ["2025-06-30", "Comisión bancaria", 35000, "Banco Nación", "egreso"],
    # Solo en contabilidad (NO están en banco)
    ["2025-06-08", "Cobro factura X-001 - Cliente X", 90000, "Banco Nación", "ingreso"],
    ["2025-06-21", "Pago proveedor Z - Servicio consultoría", 200000, "Banco Nación", "egreso"],
    # Monto diferente al banco (banco=320000 / contab=321000)
    ["2025-06-07", "Transferencia a Proveedor B", 321000, "Banco Nación", "egreso"],
    # Coinciden (ya están en banco)
    ["2025-06-05", "Depósito efectivo sucursal", 600000, "Banco Nación", "ingreso"],
    ["2025-06-12", "Pago impuesto mensual", 95000, "Banco Nación", "egreso"],
    ["2025-06-22", "Depósito cliente E", 380000, "Banco Nación", "ingreso"],
]

print("Generando archivos de prueba...\n")
print("Banco (destino):")
escribir_excel("extracto_banco_nacion.xlsx", banco_headers, banco_data)
print("Contabilidad (origen):")
escribir_excel("contabilidad_mayo_junio.xlsx", cont_headers, cont_data)

print("\n-- Resumen --")
print(f"Banco:       {len(banco_data)} registros")
print(f"Contabilidad: {len(cont_data)} registros")
print("\nDiferencias esperadas:")
print("  - Cliente X        (solo en contabilidad)     -> $90.000")
print("  - Proveedor Z      (solo en contabilidad)     -> $200.000")
print("  - Proveedor B      (monto dif: 320.000 vs 321.000) -> $1.000")
print("  Total diferencias: 3")
