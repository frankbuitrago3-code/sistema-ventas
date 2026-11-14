"""Inventario: listado con búsqueda, alta, edición y desactivación de productos."""
import math
import sqlite3

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from .auth import admin_requerido, login_requerido
from .db import get_db
from .utils import a_centavos, a_entero

bp = Blueprint("productos", __name__, url_prefix="/productos")


def obtener_producto(producto_id: int):
    producto = get_db().execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if producto is None:
        abort(404)
    return producto


def validar_formulario(form) -> tuple[dict, list[str]]:
    datos = {
        "sku": form.get("sku", "").strip().upper(),
        "nombre": form.get("nombre", "").strip(),
        "categoria": form.get("categoria", "").strip() or "General",
        "precio_centavos": a_centavos(form.get("precio")),
        "stock": a_entero(form.get("stock")),
        "stock_minimo": a_entero(form.get("stock_minimo")),
    }
    errores = []
    if not datos["sku"]:
        errores.append("El código (SKU) es obligatorio.")
    if not datos["nombre"]:
        errores.append("El nombre es obligatorio.")
    if datos["precio_centavos"] is None:
        errores.append("El precio no es válido.")
    if datos["stock"] is None:
        errores.append("El stock debe ser un número entero mayor o igual a 0.")
    if datos["stock_minimo"] is None:
        errores.append("El stock mínimo debe ser un número entero mayor o igual a 0.")
    return datos, errores


@bp.route("/")
@login_requerido
def listar():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    filtro = request.args.get("filtro", "")
    pagina = max(a_entero(request.args.get("pagina"), 1) or 1, 1)
    por_pagina = current_app.config["PRODUCTOS_POR_PAGINA"]

    condiciones, parametros = ["activo = 1"], []
    if q:
        condiciones.append("(nombre LIKE ? OR sku LIKE ?)")
        parametros += [f"%{q}%", f"%{q}%"]
    if categoria:
        condiciones.append("categoria = ?")
        parametros.append(categoria)
    if filtro == "stock-bajo":
        condiciones.append("stock <= stock_minimo")
    where = " AND ".join(condiciones)

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM productos WHERE {where}", parametros).fetchone()[0]
    paginas = max(math.ceil(total / por_pagina), 1)
    pagina = min(pagina, paginas)
    productos = db.execute(
        f"SELECT * FROM productos WHERE {where} ORDER BY nombre LIMIT ? OFFSET ?",
        [*parametros, por_pagina, (pagina - 1) * por_pagina],
    ).fetchall()
    categorias = [f["categoria"] for f in db.execute(
        "SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria")]
    return render_template("productos/lista.html", productos=productos, categorias=categorias,
                           q=q, categoria=categoria, filtro=filtro, pagina=pagina, paginas=paginas, total=total)


@bp.route("/nuevo", methods=("GET", "POST"))
@admin_requerido
def nuevo():
    datos = {}
    if request.method == "POST":
        datos, errores = validar_formulario(request.form)
        if not errores:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO productos (sku, nombre, categoria, precio_centavos, stock, stock_minimo)"
                    " VALUES (:sku, :nombre, :categoria, :precio_centavos, :stock, :stock_minimo)", datos)
                db.commit()
            except sqlite3.IntegrityError:
                errores.append(f"Ya existe un producto con el código {datos['sku']}.")
            else:
                flash(f"Producto «{datos['nombre']}» creado.", "ok")
                return redirect(url_for("productos.listar"))
        for error in errores:
            flash(error, "error")
    return render_template("productos/formulario.html", producto=None, datos=request.form)


@bp.route("/<int:producto_id>/editar", methods=("GET", "POST"))
@admin_requerido
def editar(producto_id):
    producto = obtener_producto(producto_id)
    if request.method == "POST":
        datos, errores = validar_formulario(request.form)
        if not errores:
            try:
                db = get_db()
                db.execute(
                    "UPDATE productos SET sku = :sku, nombre = :nombre, categoria = :categoria,"
                    " precio_centavos = :precio_centavos, stock = :stock, stock_minimo = :stock_minimo,"
                    " actualizado_en = datetime('now', 'localtime') WHERE id = :id",
                    {**datos, "id": producto_id})
                db.commit()
            except sqlite3.IntegrityError:
                errores.append(f"Ya existe otro producto con el código {datos['sku']}.")
            else:
                flash("Producto actualizado.", "ok")
                return redirect(url_for("productos.listar"))
        for error in errores:
            flash(error, "error")
        return render_template("productos/formulario.html", producto=producto, datos=request.form)
    datos = {
        "sku": producto["sku"], "nombre": producto["nombre"], "categoria": producto["categoria"],
        "precio": f"{producto['precio_centavos'] / 100:.2f}".replace(".", ","),
        "stock": producto["stock"], "stock_minimo": producto["stock_minimo"],
    }
    return render_template("productos/formulario.html", producto=producto, datos=datos)


@bp.route("/<int:producto_id>/eliminar", methods=("POST",))
@admin_requerido
def eliminar(producto_id):
    producto = obtener_producto(producto_id)
    db = get_db()
    # Se desactiva en lugar de borrar para no perder el historial de ventas.
    db.execute("UPDATE productos SET activo = 0, actualizado_en = datetime('now', 'localtime') WHERE id = ?",
               (producto_id,))
    db.commit()
    flash(f"Producto «{producto['nombre']}» eliminado del inventario.", "ok")
    return redirect(url_for("productos.listar"))
