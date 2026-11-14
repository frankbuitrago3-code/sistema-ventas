from app.db import get_db
from app.utils import a_centavos, formatear_dinero


def test_conversion_de_importes():
    assert a_centavos("12,50") == 1250
    assert a_centavos("12.50") == 1250
    assert a_centavos("1.234,56") == 123456
    assert a_centavos("$ 100") == 10000
    assert a_centavos("-5") is None
    assert a_centavos("abc") is None
    assert formatear_dinero(123456) == "$1.234,56"


def test_crear_producto(admin, app):
    respuesta = admin.post("/productos/nuevo", {
        "sku": "ter-001", "nombre": "Termostato digital", "categoria": "Controles",
        "precio": "32.000,00", "stock": "12", "stock_minimo": "4"}, follow_redirects=True)
    assert "creado" in respuesta.get_data(as_text=True)
    with app.app_context():
        p = get_db().execute("SELECT * FROM productos WHERE sku = 'TER-001'").fetchone()
    assert p["precio_centavos"] == 3200000 and p["stock"] == 12


def test_sku_duplicado(admin):
    respuesta = admin.post("/productos/nuevo", {
        "sku": "CMP-001", "nombre": "Otro", "precio": "1", "stock": "1", "stock_minimo": "0"})
    assert "Ya existe un producto" in respuesta.get_data(as_text=True)


def test_validacion_de_campos(admin):
    respuesta = admin.post("/productos/nuevo", {"sku": "", "nombre": "", "precio": "x", "stock": "-1", "stock_minimo": "a"})
    texto = respuesta.get_data(as_text=True)
    assert "SKU) es obligatorio" in texto
    assert "precio no es válido" in texto


def test_editar_y_eliminar(admin, app):
    admin.post("/productos/1/editar", {"sku": "CMP-001", "nombre": "Compresor 1/3 HP R600a", "categoria": "Compresores",
                                        "precio": "190000", "stock": "9", "stock_minimo": "3"})
    admin.post("/productos/1/eliminar")
    with app.app_context():
        p = get_db().execute("SELECT * FROM productos WHERE id = 1").fetchone()
    assert p["nombre"] == "Compresor 1/3 HP R600a"
    assert p["precio_centavos"] == 19000000
    assert p["activo"] == 0
    assert "<td>Compresor 1/3 HP R600a</td>" not in admin.get("/productos/").get_data(as_text=True)


def test_busqueda_y_filtro_stock_bajo(admin):
    busqueda = admin.get("/productos/?q=capa").get_data(as_text=True)
    assert "<td>Capacitor 10 uF</td>" in busqueda
    assert "<td>Compresor 1/3 HP</td>" not in busqueda
    stock_bajo = admin.get("/productos/?filtro=stock-bajo").get_data(as_text=True)
    assert "<td>Capacitor 10 uF</td>" in stock_bajo and "<td>Compresor 1/3 HP</td>" not in stock_bajo
