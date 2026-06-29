# API Documentation

Base URL: `http://localhost:5000/api`

---

## VISIÓN CONTABLE

La API trabaja exclusivamente en **VISIÓN EMPRESA**, que refleja la perspectiva contable de la empresa sobre los movimientos bancarios.

### Tabla de Conversión Banco ↔ Empresa

| Concepto | Visión Banco | Visión Empresa |
|----------|-------------|----------------|
| Naturaleza de la cuenta | PASIVO | ACTIVO |
| Depósito / Ingreso | CRÉDITO (+ pasivo) | DÉBITO (+ activo) → columna **Debe** |
| Cheque / Egreso | DÉBITO (- pasivo) | CRÉDITO (- activo) → columna **Haber** |

### Reglas en Visión Empresa

| Movimiento | Debe (ingresos) | Haber (egresos) |
|------------|:---------------:|:----------------:|
| Depósito no acreditado | Monto del depósito | — |
| Cheque no debitado | — | Monto del cheque |
| Nota de débito no registrada | — | Cargo bancario |
| Nota de crédito no registrada | Abono bancario | — |

### Signos de Ajuste (Visión Empresa)

| Partida | Signo | Efecto en saldo del banco |
|---------|:-----:|---------------------------|
| Cheques no debitados | **RESTA** (−) | Disminuye el saldo |
| Depósitos no acreditados | **SUMA** (+) | Aumenta el saldo |
| Notas de débito no registradas | **RESTA** (−) | Disminuye el saldo contable |
| Notas de crédito no registradas | **SUMA** (+) | Aumenta el saldo contable |

### Endpoints

Todos los endpoints retornan datos en **visión empresa**. El endpoint `/api/conciliate` requiere explícitamente `vision: "empresa"` en el body.

**Ejemplo request:**
```json
{
  "cuenta_id": 1,
  "fecha_desde": "2025-06-01",
  "fecha_hasta": "2025-06-30",
  "metodo": "1",
  "vision": "empresa"
}
```

**Ejemplo response (visión empresa):**
```json
{
  "conciliacion_id": 1,
  "metodo": "desde_banco",
  "vision": "empresa",
  "saldo_segun_banco": 2383000.0,
  "saldo_segun_contabilidad": 2443000.0,
  "ajustes_banco": {
    "cheques_no_debitados": -500.0,
    "depositos_no_acreditados": 300.0
  },
  "ajustes_contabilidad": {
    "notas_debito_no_registradas": -200.0,
    "notas_credito_no_registradas": 100.0
  },
  "saldo_banco_ajustado": 2382500.0,
  "saldo_contable_ajustado": 2382500.0,
  "diferencia": 0.0,
  "conciliado": true,
  "partidas_conciliatorias": []
}
```

---

## Health

### `GET /api/health`

Verifica que el servidor está operativo.

**Response 200:**
```json
{"status": "ok"}
```

---

## Archivos

### `GET /api/upload`

Lista todos los archivos subidos.

**Response 200:**
```json
[
  {
    "id": 1,
    "nombre": "banco_enero.xlsx",
    "tipo": "excel",
    "fuente": "banco",
    "fecha_carga": "2026-06-28T12:00:00",
    "ruta": "C:/.../uploads/abc123.xlsx"
  }
]
```

### `POST /api/upload`

Sube un archivo para procesar.

**Form-data:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `file` | File | Archivo .xlsx, .xls o .csv |
| `fuente` | string | `banco`, `tarjeta`, `cuenta_corriente`, `contabilidad` |

**Response 201:**
```json
{
  "message": "Archivo subido correctamente",
  "archivo": { "id": 1, "nombre": "file.csv", "tipo": "csv", "fuente": "banco", ... }
}
```

---

## Procesamiento

### `POST /api/process`

Procesa un archivo subido: parsea e inserta registros en `origen` o `destino`.

**Body:**
```json
{"archivo_id": 1}
```

**Response 200:**
```json
{
  "message": "Archivo procesado correctamente",
  "archivo_id": 1,
  "origenes_insertados": 10,
  "destinos_insertados": 0
}
```

---

## Conciliación

### `POST /api/conciliate`

Ejecuta la conciliación entre registros de origen y destino.

**Body (opcional):**
```json
{
  "origen_fuente": "contabilidad",
  "destino_fuente": "banco"
}
```

**Response 200:**
```json
{
  "message": "Conciliación completada",
  "total_origen": 100,
  "total_destino": 95,
  "diferencias_encontradas": 8
}
```

---

## Diferencias

### `GET /api/differences`

Obtiene diferencias con paginación y filtros.

**Query params:**
| Parámetro | Tipo | Default |
|-----------|------|---------|
| `tipo` | string | - |
| `estado` | string | - |
| `page` | int | 1 |
| `per_page` | int | 50 (max 500) |

**Response 200:**
```json
{
  "total": 42,
  "page": 1,
  "per_page": 50,
  "data": [
    {
      "id": 1,
      "fecha": "2024-01-18",
      "descripcion": "SERVICIO ADICIONAL",
      "monto_origen": null,
      "monto_destino": 700.0,
      "diferencia": -700.0,
      "tipo": "permanente",
      "estado": "pendiente",
      "observaciones": null,
      "fecha_deteccion": "2026-06-28 22:16:28"
    }
  ],
  "resumen": [
    {"tipo": "permanente", "cantidad": 1, "total_diferencia": -700.0}
  ]
}
```

### `GET /api/differences/:id`

Obtiene una diferencia por ID.

### `PATCH /api/differences/:id`

Actualiza campos de una diferencia.

**Body:**
```json
{
  "estado": "revisada",
  "tipo": "transitoria",
  "observaciones": "Pendiente de documentación"
}
```

---

## Reportes

### `GET /api/reports/summary`

Obtiene resumen estadístico con filtros.

**Query params:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `tipo` | string | Filtrar por tipo |
| `estado` | string | Filtrar por estado |
| `fecha_desde` | string | Fecha inicio (YYYY-MM-DD) |
| `fecha_hasta` | string | Fecha fin (YYYY-MM-DD) |

**Response 200:**
```json
{
  "total": 42,
  "monto_total": 15500.50,
  "resumen": [
    {"tipo": "permanente", "cantidad": 30, "total_diferencia": -12000.0}
  ]
}
```

### `GET /api/reports/export`

Exporta reporte en Excel o PDF.

**Query params:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `formato` | string | `excel` | `excel` o `pdf` |
| `tipo` | string | - | Filtro tipo |
| `estado` | string | - | Filtro estado |
| `fecha_desde` | string | - | Fecha inicio |
| `fecha_hasta` | string | - | Fecha fin |

**Response:** Archivo binario (attachment) `.xlsx` o `.pdf`.
