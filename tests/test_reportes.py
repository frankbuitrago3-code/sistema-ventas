from datetime import date

from app.db import cargar_datos_demo


def test_panel_muestra_ventas_de_hoy(admin):
    admin.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["2"], "metodo_pago": "efectivo"})
    html = admin.get("/panel").get_data(as_text=True)
    assert "$37.000,00" in html  # 2 x 18.500,00
    assert "Capacitor 10 uF" in html  # aparece en stock bajo


def test_reporte_excluye_ventas_anuladas(admin):
    admin.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["1"], "metodo_pago": "efectivo"})
    admin.post("/ventas/nueva", {"producto_id": ["2"], "cantidad": ["1"], "metodo_pago": "tarjeta"})
    admin.post("/ventas/2/anular")
    html = admin.get(f"/reportes?desde={date.today()}&hasta={date.today()}").get_data(as_text=True)
    assert "$18.500,00" in html
    assert "$550,00" not in html


def test_exportar_csv(admin):
    admin.post("/ventas/nueva", {"producto_id": ["1"], "cantidad": ["1"], "metodo_pago": "efectivo"})
    respuesta = admin.get("/reportes/exportar.csv")
    assert respuesta.mimetype == "text/csv"
    texto = respuesta.get_data(as_text=True)
    assert "venta;fecha;vendedor" in texto
    assert "Compresor 1/3 HP;1;18500,00;18500,00" in texto


def test_fechas_invalidas_no_rompen_el_reporte(admin):
    assert admin.get("/reportes?desde=no-es-fecha&hasta=2026-99-99").status_code == 200


def test_datos_demo(tmp_path):
    from app import create_app
    from app.db import get_db, init_db
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "demo.sqlite")})
    with app.app_context():
        init_db()
        cargar_datos_demo()
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 15
        assert db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] > 30
        assert db.execute("SELECT MIN(stock) FROM productos").fetchone()[0] >= 0
