from app.db import get_db


def stock(app, producto_id):
    with app.app_context():
        return get_db().execute("SELECT stock FROM productos WHERE id = ?", (producto_id,)).fetchone()[0]


def test_venta_descuenta_stock_y_calcula_total(vendedor, app):
    respuesta = vendedor.post("/ventas/nueva", {
        "producto_id": ["1", "2", "1"], "cantidad": ["2", "1", "1"],
        "metodo_pago": "efectivo", "cliente": "Taller Norte"})
    assert respuesta.status_code == 302
    assert stock(app, 1) == 7  # 10 - 3 (dos líneas del mismo producto se agrupan)
    assert stock(app, 2) == 1
    with app.app_context():
        venta = get_db().execute("SELECT * FROM ventas").fetchone()
        items = get_db().execute("SELECT * FROM venta_items").fetchall()
    assert venta["total_centavos"] == 3 * 1850000 + 55000
    assert venta["cliente"] == "Taller Norte"
    assert len(items) == 2


def test_no_se_vende_mas_del_stock(vendedor, app):
    respuesta = vendedor.post("/ventas/nueva", {"producto_id": ["2"], "cantidad": ["5"], "metodo_pago": "efectivo"})
    assert "Stock insuficiente" in respuesta.get_data(as_text=True)
    assert stock(app, 2) == 2
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 0


def test_venta_invalida_no_guarda_nada(vendedor, app):
    # La segunda línea falla: no debe quedar descontado el stock de la primera.
    vendedor.post("/ventas/nueva", {"producto_id": ["1", "2"], "cantidad": ["1", "99"], "metodo_pago": "tarjeta"})
    assert stock(app, 1) == 10


def test_metodo_de_pago_y_cantidades_validos(vendedor):
    sin_metodo = vendedor.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["1"], "metodo_pago": "bitcoin"})
    assert "método de pago válido" in sin_metodo.get_data(as_text=True)
    cero = vendedor.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["0"], "metodo_pago": "efectivo"})
    assert "mayores que 0" in cero.get_data(as_text=True)
    vacia = vendedor.post("/ventas/nueva", {"producto_id": [""], "cantidad": ["1"], "metodo_pago": "efectivo"})
    assert "al menos un producto" in vacia.get_data(as_text=True)


def test_anular_venta_devuelve_stock(admin, app):
    admin.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["4"], "metodo_pago": "efectivo"})
    assert stock(app, 1) == 6
    admin.post("/ventas/1/anular")
    assert stock(app, 1) == 10
    admin.post("/ventas/1/anular")  # anular dos veces no debe sumar stock otra vez
    assert stock(app, 1) == 10
    assert "Anulada" in admin.get("/ventas/1").get_data(as_text=True)


def test_vendedor_no_puede_anular_ni_ver_ventas_ajenas(admin, nav, app):
    admin.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["1"], "metodo_pago": "efectivo"})
    admin.post("/auth/logout")
    nav.login("vendedor", "vende12345")
    assert nav.get("/ventas/1").status_code == 403
    assert nav.post("/ventas/1/anular").status_code == 403
