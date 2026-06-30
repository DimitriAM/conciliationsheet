# Reporte de Implementación - Conciliación Bancaria Forma 1

## Estado Actual

### ✅ Implementado
- **Método único**: `conciliar_forma_1()` en `conciliador.py` — parte del saldo contable y llega al saldo del extracto bancario
- **Endpoint `/api/conciliate`**: solo acepta `metodo: "desde_contabilidad"`; cualquier otro método devuelve error 400
- **Identificación de partidas**: 4 reglas implementadas vía SQL con `NOT EXISTS` (mismo monto ±0.01 y misma fecha)
  1. Cheques no debitados: contabilidad HABER sin match en banco DEBE
  2. Depósitos no acreditados: contabilidad DEBE sin match en banco HABER
  3. Notas de débito no registradas: banco DEBE sin match en contabilidad HABER
  4. Notas de crédito no registradas: banco HABER sin match en contabilidad DEBE
- **Estructura de cada partida**: contiene `fecha`, `descripcion`, `monto` (original completo), `signo`, `origen`, `tipo`, `afecta`, `clasificacion`
- **Cálculo**: `saldo_ajustado = saldo_contable + Σ(monto * signo)`, `diferencia = saldo_banco - saldo_ajustado`
- **Tests**: 9 tests unitarios pasando (identificación de partidas, cálculos, clasificaciones)
- **Frontend**: Selector de método eliminado, muestra solo "Forma 1: Contabilidad → Banco"

### ✅ Eliminado
- `conciliar_forma_2()` del servicio
- `conciliar_cuadrada()` del servicio
- Tabla `detalles_conciliacion` de la base de datos
- Opciones de método en el frontend (dashboard.php y dashboard.js)

### ✅ Base de Datos
- Esquema migrado automáticamente (vía `user_version` y migration en `db.py`)
- Tablas mantenidas: `cuentas_bancarias`, `movimientos_bancarios`, `movimientos_contables`, `partidas_conciliatorias`, `conciliaciones`
- `partidas_conciliatorias`: nuevos campos `monto`, `signo`, `origen` (contabilidad/banco), `tipo` (cheque_no_debitado, etc.), `afecta`, `clasificacion`
- `conciliaciones`: `metodo` solo acepta `desde_contabilidad`

## Problemas Detectados

### 1. Base de datos vacía (esperado)
```
POST /api/conciliate con metodo="desde_contabilidad"
→ 500 FOREIGN KEY constraint failed
```
**Causa**: No existe una cuenta con `id=1` (la DB fue recreada desde cero).  
**Solución**: Cargar datos de prueba (ejecutar `generar_datos_prueba.py` o subir archivos vía frontend).

### 2. Test `test_conciliator.py` roto (pre-existente)
```
ModuleNotFoundError: No module named 'models.origen'
```
**Causa**: El archivo de test referencia módulos (`models.origen`, `models.destino`, `services.conciliator`) que ya no existen en el proyecto.  
**Solución**: Eliminar o actualizar el archivo `tests/backend/test_conciliator.py`.

### 3. Migración destructiva
Al migrar de la versión anterior, se pierden los datos existentes en `partidas_conciliatorias` y `conciliaciones` porque se eliminan y recrean las tablas.  
**Impacto**: Bajo (solo datos de conciliación, no datos fuente). Los movimientos bancarios y contables se conservan.

## Instrucciones de Uso

```bash
# 1. Iniciar servidor
cd conciliationsheet/backend
python app.py

# 2. Llamar al endpoint (después de cargar datos)
curl -X POST http://localhost:5000/api/conciliate \
  -H "Content-Type: application/json" \
  -d '{
    "cuenta_id": 1,
    "fecha_desde": "2025-06-01",
    "fecha_hasta": "2025-06-30",
    "metodo": "desde_contabilidad"
  }'
```
