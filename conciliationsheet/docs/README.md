# Conciliation Sheet

Sistema de conciliación de datos financieros entre origen (contabilidad) y destino (banco, tarjeta, cuenta corriente).

## Estructura

```
conciliationsheet/
├── backend/          # API Flask + SQLite
│   ├── app.py        # Entrypoint WSGI/ASGI
│   ├── asgi.py       # Adaptador ASGI para Uvicorn
│   ├── config.py     # Configuraciones y rutas
│   ├── database/     # Conexión DB + schema SQL
│   ├── models/       # Modelos de datos (Archivo, Origen, Destino, Diferencia)
│   ├── routes/       # Blueprints Flask (upload, process, conciliate, differences, reports)
│   ├── services/     # Lógica de negocio (file_processor, conciliator, diff_analyzer, report_generator)
│   └── utils/        # Utilidades (validators, helpers, cache)
├── frontend/         # PHP + JS
│   ├── index.php     # Punto de entrada con navegación
│   ├── views/        # Vistas (upload, dashboard, reports)
│   ├── js/           # Lógica JS (upload, conciliate, dashboard, reports)
│   ├── css/          # Estilos
│   └── router.php    # Router para PHP built-in server
├── data/
│   ├── uploads/      # Archivos subidos
│   └── results/      # Resultados generados
├── docs/             # Documentación
└── tests/            # Pruebas unitarias
```

## Requisitos

- Python 3.10+
- PHP 8.0+ (para frontend)
- Las dependencias Python se instalan con `pip install -r requirements.txt`

## Instalación

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Frontend (PHP built-in server)
cd frontend
php -S 0.0.0.0:8080 -t . router.php
```

## Ejecución

```bash
# Terminal 1 - API
cd backend
uvicorn asgi:application --host 0.0.0.0 --port 5000 --reload

# Terminal 2 - Frontend
cd frontend
php -S 0.0.0.0:8080 -t . router.php
```

## Pruebas

```bash
cd tests/backend
python -m pytest test_conciliator.py -v
```
