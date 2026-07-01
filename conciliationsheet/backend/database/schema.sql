DROP TABLE IF EXISTS detalles_conciliacion;
DROP TABLE IF EXISTS conciliaciones;
DROP TABLE IF EXISTS partidas_conciliatorias;
DROP TABLE IF EXISTS movimientos_contables;
DROP TABLE IF EXISTS movimientos_bancarios;
DROP TABLE IF EXISTS cuentas_bancarias;
DROP TABLE IF EXISTS diferencias;
DROP TABLE IF EXISTS destino;
DROP TABLE IF EXISTS origen;
DROP TABLE IF EXISTS archivos;

-- ============================================================
-- IMPORTANTE: VISION CONTABLE
-- ============================================================
-- Cada tabla almacena datos TAL CUAL vienen de su fuente.
-- La conversion logica se realiza en el servicio de conciliacion.
--
-- movimientos_bancarios:  VISION BANCO (tal cual del extracto)
--   debe  = CARGO segun banco  (equivale a HABER en la empresa)
--   haber = ABONO segun banco  (equivale a DEBE en la empresa)
--
-- movimientos_contables:   VISION EMPRESA (tal cual de libros)
--   debe  = INGRESO segun empresa  (aumenta el activo)
--   haber = EGRESO segun empresa   (disminuye el activo)
-- ============================================================

CREATE TABLE cuentas_bancarias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    cbu TEXT,
    banco TEXT NOT NULL,
    saldo_inicial REAL DEFAULT 0,
    fecha_apertura DATE
);

-- VISION BANCO: datos tal cual del extracto bancario
CREATE TABLE movimientos_bancarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT NOT NULL,
    debe REAL DEFAULT 0,             -- CARGO segun banco (HABER en empresa)
    haber REAL DEFAULT 0,            -- ABONO segun banco (DEBE en empresa)
    saldo REAL,
    tipo TEXT CHECK(tipo IN ('saldo_inicial','deposito','cheque','nota_debito','nota_credito','comision','interes','error')),
    conciliado BOOLEAN DEFAULT 0,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
);

-- VISION EMPRESA: datos tal cual de los registros contables
CREATE TABLE movimientos_contables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT NOT NULL,
    debe REAL DEFAULT 0,             -- INGRESO segun empresa (aumenta activo)
    haber REAL DEFAULT 0,            -- EGRESO segun empresa (disminuye activo)
    saldo REAL,
    comprobante TEXT,
    conciliado BOOLEAN DEFAULT 0,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
);

CREATE TABLE partidas_conciliatorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT NOT NULL,
    monto REAL NOT NULL DEFAULT 0,
    signo INTEGER NOT NULL DEFAULT 1 CHECK(signo IN (1, -1)),
    origen TEXT NOT NULL CHECK(origen IN ('contabilidad', 'banco')),
    tipo TEXT NOT NULL CHECK(tipo IN ('cheque_no_debitado', 'deposito_no_acreditado', 'nota_debito_no_registrada', 'nota_credito_no_registrada', 'diferencia_contabilidad', 'diferencia_banco')),
    afecta TEXT NOT NULL CHECK(afecta IN ('banco', 'contabilidad')),
    clasificacion TEXT NOT NULL CHECK(clasificacion IN ('transitoria', 'permanente')),
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'ajustada', 'resuelta')),
    fecha_resolucion DATE,
    observaciones TEXT,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
);

-- Historial de conciliaciones (vision EMPRESA por defecto)
CREATE TABLE conciliaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL,
    fecha_cierre DATE NOT NULL,
    metodo TEXT CHECK(metodo IN ('desde_contabilidad', 'desde_banco')),
    vision TEXT DEFAULT 'empresa' CHECK(vision IN ('empresa','banco')),
    saldo_segun_banco REAL,
    saldo_segun_contabilidad REAL,
    saldo_ajustado_banco REAL,
    saldo_ajustado_contabilidad REAL,
    diferencia_total REAL,
    estado TEXT DEFAULT 'en_proceso' CHECK(estado IN ('en_proceso','conciliada','pendiente_ajustes')),
    fecha_conciliacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas_bancarias(id) ON DELETE CASCADE
);

CREATE INDEX idx_movimientos_bancarios_cuenta_fecha ON movimientos_bancarios(cuenta_id, fecha);
CREATE INDEX idx_movimientos_contables_cuenta_fecha ON movimientos_contables(cuenta_id, fecha);
CREATE INDEX idx_partidas_conciliatorias_cuenta ON partidas_conciliatorias(cuenta_id);
CREATE INDEX idx_conciliaciones_cuenta ON conciliaciones(cuenta_id);

CREATE TABLE diccionario_sinonimos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente TEXT NOT NULL CHECK(fuente IN ('banco', 'contabilidad')),
    patron TEXT NOT NULL,
    tipo TEXT NOT NULL,
    autogenerado INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diccionario_fuente ON diccionario_sinonimos(fuente, tipo);
CREATE UNIQUE INDEX idx_diccionario_patron_fuente ON diccionario_sinonimos(fuente, patron);
