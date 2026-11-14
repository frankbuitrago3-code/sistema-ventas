"""Panel principal y reportes de ventas por rango de fechas (con exportación CSV)."""
import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, g, render_template, request

from .auth import admin_requerido, login_requerido
from .db import get_db
from .ventas import METODOS_PAGO

bp = Blueprint("reportes", __name__)


def _fecha(texto: str | None, por_defecto: date) -> date:
    try:
        return datetime.strptime(texto or "", "%Y-%m-%d").date()
    except ValueError:
        return por_defecto


def resumen_ventas(desde: date, hasta: date) -> dict:
    """Totales, ventas por día, por método de pago y productos más vendidos."""
    db = get_db()
    rango = (desde.isoformat(), hasta.isoformat())
    filtro = "v.estado = 'completada' AND date(v.creado_en) BETWEEN ? AND ?"

    totales = db.execute(
        f"SELECT COUNT(*) AS ventas, COALESCE(SUM(total_centavos), 0) AS total FROM ventas v WHERE {filtro}",
        rango).fetchone()
    unidades = db.execute(
        f"SELECT COALESCE(SUM(i.cantidad), 0) FROM venta_items i JOIN ventas v ON v.id = i.venta_id WHERE {filtro}",
        rango).fetchone()[0]

    por_dia_db = {fila["dia"]: fila["total"] for fila in db.execute(
        f"SELECT date(v.creado_en) AS dia, SUM(total_centavos) AS total FROM ventas v WHERE {filtro} GROUP BY dia",
        rango)}
    por_dia, dia = [], desde
    while dia <= hasta:
        por_dia.append({"dia": dia, "total": por_dia_db.get(dia.isoformat(), 0)})
        dia += timedelta(days=1)
    maximo = max((d["total"] for d in por_dia), default=0) or 1
    for d in por_dia:
        d["porcentaje"] = round(d["total"] * 100 / maximo, 1)

    por_metodo = db.execute(
        f"SELECT metodo_pago, COUNT(*) AS ventas, SUM(total_centavos) AS total FROM ventas v"
        f" WHERE {filtro} GROUP BY metodo_pago ORDER BY total DESC", rango).fetchall()
    top_productos = db.execute(
        f"""SELECT i.nombre_producto, SUM(i.cantidad) AS unidades, SUM(i.subtotal_centavos) AS total
            FROM venta_items i JOIN ventas v ON v.id = i.venta_id WHERE {filtro}
            GROUP BY i.producto_id ORDER BY total DESC LIMIT 5""", rango).fetchall()

    return {
        "ventas": totales["ventas"],
        "total": totales["total"],
        "unidades": unidades,
        "ticket_medio": totales["total"] // totales["ventas"] if totales["ventas"] else 0,
        "por_dia": por_dia,
        "por_metodo": por_metodo,
        "top_productos": top_productos,
    }


@bp.route("/panel")
@login_requerido
def panel():
    hoy = date.today()
    db = get_db()
    resumen_hoy = resumen_ventas(hoy, hoy)
    resumen_mes = resumen_ventas(hoy.replace(day=1), hoy)
    ultimos_7 = resumen_ventas(hoy - timedelta(days=6), hoy)
    stock_bajo = db.execute(
        "SELECT * FROM productos WHERE activo = 1 AND stock <= stock_minimo ORDER BY stock, nombre LIMIT 8"
    ).fetchall()
    condicion, parametros = "", []
    if g.usuario["rol"] != "admin":
        condicion, parametros = "WHERE v.usuario_id = ?", [g.usuario["id"]]
    recientes = db.execute(
        f"""SELECT v.*, u.nombre AS vendedor FROM ventas v JOIN usuarios u ON u.id = v.usuario_id
            {condicion} ORDER BY v.creado_en DESC, v.id DESC LIMIT 6""", parametros).fetchall()
    return render_template("reportes/panel.html", hoy=resumen_hoy, mes=resumen_mes, semana=ultimos_7,
                           stock_bajo=stock_bajo, recientes=recientes, metodos=METODOS_PAGO)


@bp.route("/reportes")
@admin_requerido
def reportes():
    hoy = date.today()
    desde = _fecha(request.args.get("desde"), hoy - timedelta(days=29))
    hasta = _fecha(request.args.get("hasta"), hoy)
    if desde > hasta:
        desde, hasta = hasta, desde
    if (hasta - desde).days > 366:
        desde = hasta - timedelta(days=366)
    return render_template("reportes/reportes.html", r=resumen_ventas(desde, hasta),
                           desde=desde, hasta=hasta, metodos=METODOS_PAGO)


@bp.route("/reportes/exportar.csv")
@admin_requerido
def exportar_csv():
    hoy = date.today()
    desde = _fecha(request.args.get("desde"), hoy - timedelta(days=29))
    hasta = _fecha(request.args.get("hasta"), hoy)
    filas = get_db().execute(
        """SELECT v.id, v.creado_en, u.nombre AS vendedor, COALESCE(v.cliente, '') AS cliente, v.metodo_pago,
                  v.estado, i.nombre_producto, i.cantidad, i.precio_unitario_centavos, i.subtotal_centavos
           FROM ventas v JOIN usuarios u ON u.id = v.usuario_id JOIN venta_items i ON i.venta_id = v.id
           WHERE date(v.creado_en) BETWEEN ? AND ? ORDER BY v.creado_en, v.id, i.id""",
        (desde.isoformat(), hasta.isoformat())).fetchall()

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(["venta", "fecha", "vendedor", "cliente", "metodo_pago", "estado",
                       "producto", "cantidad", "precio_unitario", "subtotal"])
    for f in filas:
        escritor.writerow([f["id"], f["creado_en"], f["vendedor"], f["cliente"], f["metodo_pago"], f["estado"],
                           f["nombre_producto"], f["cantidad"],
                           f"{f['precio_unitario_centavos'] / 100:.2f}".replace(".", ","),
                           f"{f['subtotal_centavos'] / 100:.2f}".replace(".", ",")])
    nombre = f"ventas_{desde.isoformat()}_{hasta.isoformat()}.csv"
    # BOM para que Excel abra bien las tildes.
    return Response("﻿" + salida.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})
