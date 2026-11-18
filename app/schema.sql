-- Esquema de la base de datos. Los importes se guardan en centavos (enteros)
-- para evitar errores de redondeo con decimales.

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario       TEXT    NOT NULL UNIQUE,
    nombre        TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    rol           TEXT    NOT NULL CHECK (rol IN ('admin', 'vendedor')),
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT    NOT NULL UNIQUE,
    nombre          TEXT    NOT NULL,
    categoria       TEXT    NOT NULL DEFAULT 'General',
    precio_centavos INTEGER NOT NULL CHECK (precio_centavos >= 0),
    stock           INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    stock_minimo    INTEGER NOT NULL DEFAULT 5 CHECK (stock_minimo >= 0),
    activo          INTEGER NOT NULL DEFAULT 1,
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    actualizado_en  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ventas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios (id),
    cliente        TEXT,
    metodo_pago    TEXT    NOT NULL CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia')),
    total_centavos INTEGER NOT NULL CHECK (total_centavos >= 0),
    estado         TEXT    NOT NULL DEFAULT 'completada' CHECK (estado IN ('completada', 'anulada')),
    creado_en      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    anulada_en     TEXT,
    anulada_por    INTEGER REFERENCES usuarios (id)
);

CREATE TABLE IF NOT EXISTS venta_items (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id                 INTEGER NOT NULL REFERENCES ventas (id) ON DELETE CASCADE,
    producto_id              INTEGER NOT NULL REFERENCES productos (id),
    nombre_producto          TEXT    NOT NULL,
    cantidad                 INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario_centavos INTEGER NOT NULL CHECK (precio_unitario_centavos >= 0),
    subtotal_centavos        INTEGER NOT NULL CHECK (subtotal_centavos >= 0)
);

-- Ajustes del negocio (nombre de la tienda, etc.).
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ventas_fecha      ON ventas (creado_en);
CREATE INDEX IF NOT EXISTS idx_items_venta       ON venta_items (venta_id);
CREATE INDEX IF NOT EXISTS idx_items_producto    ON venta_items (producto_id);
CREATE INDEX IF NOT EXISTS idx_productos_nombre  ON productos (nombre);
