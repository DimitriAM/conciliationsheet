# Conciliation Sheet

Sistema de conciliación financiera entre contabilidad (origen) y banco/tarjeta (destino).

## Requisitos

- Python 3.10+ (entorno virtual en `venv/`)
- PHP 8.0+ (`C:\xampp\php\php.exe`)

## Inicio rápido

### 1. Activar el entorno virtual

```bash
cd C:\Aldo\CONCILIATIONSHEETS\venv\Scripts
activate
```

### 2. Iniciar API (Flask → Uvicorn)

```bash
cd C:\Aldo\CONCILIATIONSHEETS\conciliationsheet\backend
uvicorn asgi:application --host 0.0.0.0 --port 5000 --reload
```

La API queda en `http://localhost:5000`.

### 3. Iniciar Frontend (PHP built-in server)

```bash
cd C:\Aldo\CONCILIATIONSHEETS\conciliationsheet\frontend
C:\xampp\php\php.exe -S 0.0.0.0:8080 -t . router.php
```

El frontend queda en `http://localhost:8080`.

### 4. Abrir el navegador

Ingresar a `http://localhost:8080`

## Flujo de uso

1. **Cargar** → subir archivo Excel de banco (fuente: banco) y archivo de contabilidad (fuente: contabilidad)
2. **Dashboard** → ejecutar conciliación
3. **Reportes** → exportar resumen a Excel o PDF

## Datos de prueba

```bash
cd C:\Aldo\CONCILIATIONSHEETS\conciliationsheet
python generar_datos_prueba.py
```
