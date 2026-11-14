"""Registro de ventas con varios productos, historial, detalle y anulación."""
from collections import OrderedDict

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import admin_requerido, login_requerido
from .db import get_db
from .utils import a_entero

bp = Blueprint("ventas", __name__, url_prefix="/ventas")

METODOS_PAGO = {"efectivo": "Efectivo", "tarjeta": "Tarjeta", "transferencia": "Transferencia"}


class VentaInvalida(Exception):
    pass


def registrar_venta(usuario_id: int, items: dict[int, int], metodo_pago: str, cliente: str | None) -> int:
    """Crea la venta y descuenta el stock en una sola transacción.

    `items` es {producto_id: cantidad}. Lanza VentaInvalida si algo no cuadra,
    y en ese caso no se guarda nada.
    """
    if not items:
        raise VentaInvalida("Agrega al menos un producto a la venta.")
    if metodo_pago not in METODOS_PAGO:
        raise VentaInvalida("Elige un método de pago válido.")

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")  # bloquea escrituras concurrentes mientras se valida el stock
        lineas, total = [], 0
        for producto_id, cantidad in items.items():
            producto = db.execute(
                "SELECT id, nombre, precio_centavos, stock FROM productos WHERE id = ? AND activo = 1",
                (producto_id,)).fetchone()
            if producto is None:
                raise VentaInvalida("Uno de los productos ya no existe.")
            if cantidad > producto["stock"]:
                raise VentaInvalida(
                    f"Stock insuficiente de «{producto['nombre']}»: quedan {producto['stock']}.")
            subtotal = producto["precio_centavos"] * cantidad
            total += subtotal
            lineas.append((producto, cantidad, subtotal))

        venta_id = db.execute(
            "INSERT INTO ventas (usuario_id, cliente, metodo_pago, total_centavos) VALUES (?, ?, ?, ?)",
            (usuario_id, cliente or None, metodo_pago, total)).lastrowid
        for producto, cantidad, subtotal in lineas:
            db.execute(
                "INSERT INTO venta_items (venta_id, producto_id, nombre_producto, cantidad,"
                " precio_unitario_centavos, subtotal_centavos) VALUES (?, ?, ?, ?, ?, ?)",
                (venta_id, producto["id"], producto["nombre"], cantidad, producto["precio_centavos"], subtotal))
            db.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto["id"]))
        db.commit()
        return venta_id
    except Exception:
        db.rollback()
        raise


def leer_items(form) -> dict[int, int]:
    """Agrupa las líneas del formulario sumando cantidades del mismo producto."""
    items: dict[int, int] = OrderedDict()
    ids = form.getlist("producto_id")
    cantidades = form.getlist("cantidad")
    for producto_id, cantidad in zip(ids, cantidades):
        pid = a_entero(producto_id, 1)
        cant = a_entero(cantidad, 1)
        if pid is None and not str(producto_id).strip():
            continue  # fila vacía
        if pid is None or cant is None:
            raise VentaInvalida("Revisa los productos y cantidades (las cantidades deben ser mayores que 0).")
        items[pid] = items.get(pid, 0) + cant
    return items


@bp.route("/nueva", methods=("GET", "POST"))
@login_requerido
def nueva():
    db = get_db()
    productos = db.execute(
        "SELECT id, sku, nombre, precio_centavos, stock FROM productos WHERE activo = 1 AND stock > 0 ORDER BY nombre"
    ).fetchall()
    if request.method == "POST":
        try:
            items = leer_items(request.form)
            venta_id = registrar_venta(
                g.usuario["id"], items, request.form.get("metodo_pago", ""),
                request.form.get("cliente", "").strip()[:120])
        except VentaInvalida as error:
            flash(str(error), "error")
        else:
            flash(f"Venta #{venta_id} registrada correctamente.", "ok")
            return redirect(url_for("ventas.detalle", venta_id=venta_id))
    return render_template("ventas/nueva.html", productos=productos, metodos=METODOS_PAGO)


@bp.route("/")
@login_requerido
def historial():
    estado = request.args.get("estado", "")
    condiciones, parametros = [], []
    if estado in ("completada", "anulada"):
        condiciones.append("v.estado = ?")
        parametros.append(estado)
    if g.usuario["rol"] != "admin":
        condiciones.append("v.usuario_id = ?")  # cada vendedor ve sus propias ventas
        parametros.append(g.usuario["id"])
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    ventas = get_db().execute(
        f"""SELECT v.*, u.nombre AS vendedor,
                   (SELECT SUM(cantidad) FROM venta_items WHERE venta_id = v.id) AS unidades
            FROM ventas v JOIN usuarios u ON u.id = v.usuario_id {where}
            ORDER BY v.creado_en DESC, v.id DESC LIMIT 100""", parametros).fetchall()
    return render_template("ventas/historial.html", ventas=ventas, estado=estado, metodos=METODOS_PAGO)


def obtener_venta(venta_id: int):
    venta = get_db().execute(
        """SELECT v.*, u.nombre AS vendedor, a.nombre AS anulada_por_nombre
           FROM ventas v JOIN usuarios u ON u.id = v.usuario_id
           LEFT JOIN usuarios a ON a.id = v.anulada_por WHERE v.id = ?""", (venta_id,)).fetchone()
    if venta is None:
        abort(404)
    if g.usuario["rol"] != "admin" and venta["usuario_id"] != g.usuario["id"]:
        abort(403)
    return venta


@bp.route("/<int:venta_id>")
@login_requerido
def detalle(venta_id):
    venta = obtener_venta(venta_id)
    items = get_db().execute("SELECT * FROM venta_items WHERE venta_id = ? ORDER BY id", (venta_id,)).fetchall()
    return render_template("ventas/detalle.html", venta=venta, items=items, metodos=METODOS_PAGO)


@bp.route("/<int:venta_id>/anular", methods=("POST",))
@admin_requerido
def anular(venta_id):
    venta = obtener_venta(venta_id)
    if venta["estado"] == "anulada":
        flash("Esta venta ya estaba anulada.", "info")
        return redirect(url_for("ventas.detalle", venta_id=venta_id))
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        for item in db.execute("SELECT producto_id, cantidad FROM venta_items WHERE venta_id = ?", (venta_id,)):
            db.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (item["cantidad"], item["producto_id"]))
        db.execute(
            "UPDATE ventas SET estado = 'anulada', anulada_en = datetime('now', 'localtime'), anulada_por = ?"
            " WHERE id = ?", (g.usuario["id"], venta_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    flash(f"Venta #{venta_id} anulada y stock devuelto al inventario.", "ok")
    return redirect(url_for("ventas.detalle", venta_id=venta_id))
