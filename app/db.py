"""Conexión a SQLite y comandos de consola (init-db, crear-admin, datos-demo)."""
import random
import sqlite3
from datetime import datetime, timedelta

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_e=None) -> None:
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


def init_db() -> None:
    conexion = get_db()
    with current_app.open_resource("schema.sql") as archivo:
        conexion.executescript(archivo.read().decode("utf-8"))


def crear_usuario(usuario: str, nombre: str, password: str, rol: str) -> int:
    conexion = get_db()
    cursor = conexion.execute(
        "INSERT INTO usuarios (usuario, nombre, password_hash, rol) VALUES (?, ?, ?, ?)",
        (usuario.strip().lower(), nombre.strip(), generate_password_hash(password), rol),
    )
    conexion.commit()
    return cursor.lastrowid


PRODUCTOS_DEMO = [
    ("CMP-001", "Compresor 1/3 HP R134a", "Compresores", 18500000, 8, 3),
    ("CMP-002", "Compresor 1/2 HP R600a", "Compresores", 21000000, 4, 3),
    ("GAS-001", "Gas refrigerante R410A 11,3 kg", "Gases", 9500000, 15, 5),
    ("GAS-002", "Gas refrigerante R134a 13,6 kg", "Gases", 8700000, 2, 5),
    ("CAP-001", "Capacitor de arranque 10 µF", "Eléctricos", 550000, 40, 10),
    ("CAP-002", "Capacitor dual 35+5 µF", "Eléctricos", 1250000, 25, 10),
    ("TER-001", "Termostato digital universal", "Controles", 3200000, 12, 4),
    ("TER-002", "Sensor NTC 10K", "Controles", 450000, 60, 15),
    ("MOT-001", "Motor ventilador condensador 1/6 HP", "Motores", 6800000, 6, 3),
    ("MOT-002", "Motor ventilador evaporador 9 W", "Motores", 2900000, 3, 4),
    ("TUB-001", "Tubería de cobre 1/4\" (rollo 15 m)", "Tuberías", 7400000, 10, 4),
    ("TUB-002", "Tubería de cobre 3/8\" (rollo 15 m)", "Tuberías", 9900000, 7, 4),
    ("HER-001", "Manómetro doble R410A/R22", "Herramientas", 12500000, 5, 2),
    ("HER-002", "Bomba de vacío 3 CFM", "Herramientas", 28500000, 1, 2),
    ("FIL-001", "Filtro deshidratador 1/4\"", "Accesorios", 380000, 80, 20),
]


def cargar_datos_demo(dias: int = 30, semilla: int = 7) -> None:
    """Crea usuarios, productos y ventas de ejemplo para probar la aplicación."""
    rnd = random.Random(semilla)
    conexion = get_db()
    if conexion.execute("SELECT COUNT(*) FROM productos").fetchone()[0]:
        raise click.ClickException("La base de datos ya tiene productos. Usa una base vacía para la demo.")

    if not conexion.execute("SELECT 1 FROM usuarios WHERE usuario = 'admin'").fetchone():
        crear_usuario("admin", "Administrador Demo", "admin123", "admin")
    if not conexion.execute("SELECT 1 FROM usuarios WHERE usuario = 'vendedor'").fetchone():
        crear_usuario("vendedor", "Vendedor Demo", "vendedor123", "vendedor")
    vendedores = [fila["id"] for fila in conexion.execute("SELECT id FROM usuarios")]

    conexion.executemany(
        "INSERT INTO productos (sku, nombre, categoria, precio_centavos, stock, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)",
        [(sku, nombre, cat, precio, stock + 40, minimo) for sku, nombre, cat, precio, stock, minimo in PRODUCTOS_DEMO],
    )
    productos = conexion.execute("SELECT id, nombre, precio_centavos FROM productos").fetchall()

    ahora = datetime.now()
    for dia in range(dias, -1, -1):
        for _ in range(rnd.randint(1, 5)):
            fecha = (ahora - timedelta(days=dia)).replace(hour=rnd.randint(8, 18), minute=rnd.randint(0, 59))
            if fecha > ahora:
                fecha = ahora
            elegidos = rnd.sample(productos, rnd.randint(1, 3))
            items = [(p, rnd.randint(1, 3)) for p in elegidos]
            total = sum(p["precio_centavos"] * cant for p, cant in items)
            venta_id = conexion.execute(
                "INSERT INTO ventas (usuario_id, cliente, metodo_pago, total_centavos, creado_en) VALUES (?, ?, ?, ?, ?)",
                (rnd.choice(vendedores), rnd.choice([None, "Taller El Polo", "Hielos Norte", "Cliente mostrador"]),
                 rnd.choice(["efectivo", "tarjeta", "transferencia"]), total, fecha.strftime("%Y-%m-%d %H:%M:%S")),
            ).lastrowid
            for p, cant in items:
                conexion.execute(
                    "INSERT INTO venta_items (venta_id, producto_id, nombre_producto, cantidad, precio_unitario_centavos, subtotal_centavos)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (venta_id, p["id"], p["nombre"], cant, p["precio_centavos"], p["precio_centavos"] * cant),
                )
                conexion.execute("UPDATE productos SET stock = MAX(stock - ?, 0) WHERE id = ?", (cant, p["id"]))
    # Dejar algunos productos con stock bajo para que se vean las alertas.
    for sku, *_resto, stock, _minimo in PRODUCTOS_DEMO:
        conexion.execute("UPDATE productos SET stock = ? WHERE sku = ?", (stock, sku))
    conexion.commit()


@click.command("init-db")
def init_db_command():
    """Crea las tablas de la base de datos (no borra datos existentes)."""
    init_db()
    click.echo("Base de datos lista.")


@click.command("crear-admin")
@click.option("--usuario", prompt="Usuario")
@click.option("--nombre", prompt="Nombre completo")
@click.password_option("--password", prompt="Contraseña")
def crear_admin_command(usuario, nombre, password):
    """Crea un usuario administrador."""
    if len(password) < 8:
        raise click.ClickException("La contraseña debe tener al menos 8 caracteres.")
    init_db()
    try:
        crear_usuario(usuario, nombre, password, "admin")
    except sqlite3.IntegrityError:
        raise click.ClickException(f"El usuario '{usuario}' ya existe.")
    click.echo(f"Administrador '{usuario}' creado.")


@click.command("datos-demo")
def datos_demo_command():
    """Carga usuarios, productos y 30 días de ventas de ejemplo."""
    init_db()
    cargar_datos_demo()
    click.echo("Datos de demostración cargados. Usuarios: admin/admin123 y vendedor/vendedor123")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(crear_admin_command)
    app.cli.add_command(datos_demo_command)
