import sqlite3

import pytest

from app import create_app
from tests.conftest import Navegador

DATOS = {"nombre_tienda": "Bodega La Esquina", "nombre": "María Pérez", "usuario": "maria",
         "password": "clave-segura-1", "password2": "clave-segura-1"}


@pytest.fixture
def vacio(tmp_path):
    """Aplicación recién instalada: base de datos sin usuarios ni productos."""
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "nueva.sqlite")})
    return Navegador(app.test_client())


def test_sin_usuarios_lleva_a_configuracion_inicial(vacio):
    for ruta in ("/", "/panel", "/auth/login", "/productos/"):
        r = vacio.get(ruta)
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/configuracion-inicial")


def test_configuracion_inicial_crea_admin_y_entra(vacio):
    r = vacio.post("/configuracion-inicial", DATOS)
    assert r.status_code == 302
    panel = vacio.get("/panel")
    assert panel.status_code == 200
    assert "Bodega La Esquina" in panel.get_data(as_text=True)
    assert "María Pérez" in panel.get_data(as_text=True)


def test_configuracion_inicial_no_se_puede_repetir(vacio):
    vacio.post("/configuracion-inicial", DATOS)
    otro = Navegador(vacio.client.application.test_client())
    r = otro.post("/configuracion-inicial", {**DATOS, "usuario": "intruso"})
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/auth/login")
    r = otro.login("intruso", DATOS["password"])
    assert "incorrectos" in r.get_data(as_text=True)


@pytest.mark.parametrize("cambio, mensaje", [
    ({"password2": "otra-cosa-123"}, "no coinciden"),
    ({"password": "corta", "password2": "corta"}, "al menos 8"),
    ({"usuario": "con espacio"}, "solo puede tener letras"),
    ({"nombre_tienda": ""}, "nombre de tu negocio"),
])
def test_configuracion_inicial_valida_datos(vacio, cambio, mensaje):
    r = vacio.post("/configuracion-inicial", {**DATOS, **cambio})
    assert r.status_code == 200
    assert mensaje in r.get_data(as_text=True)
    assert vacio.get("/panel").status_code == 302


def test_configuracion_inicial_exige_csrf(vacio):
    r = vacio.client.post("/configuracion-inicial", data=DATOS)
    assert r.status_code == 400


def test_admin_cambia_nombre_del_negocio(admin):
    admin.post("/ajustes", {"nombre_tienda": "Repuestos Caracas"})
    assert "Repuestos Caracas" in admin.get("/panel").get_data(as_text=True)


def test_copia_de_seguridad_es_una_base_valida(admin, tmp_path):
    r = admin.get("/ajustes/copia-de-seguridad")
    assert r.status_code == 200
    assert "attachment" in r.headers["Content-Disposition"]
    copia = tmp_path / "copia.sqlite"
    copia.write_bytes(r.data)
    conexion = sqlite3.connect(copia)
    assert conexion.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 2
    conexion.close()


def test_vendedor_no_puede_ver_ajustes_ni_descargar_copia(vendedor):
    assert vendedor.get("/ajustes").status_code == 403
    assert vendedor.get("/ajustes/copia-de-seguridad").status_code == 403
