import pytest

from app import create_app
from app.db import crear_usuario, get_db, init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "test.sqlite")})
    with app.app_context():
        init_db()
        crear_usuario("admin", "Ana Admin", "admin12345", "admin")
        crear_usuario("vendedor", "Victor Vendedor", "vende12345", "vendedor")
        db = get_db()
        db.executemany(
            "INSERT INTO productos (sku, nombre, categoria, precio_centavos, stock, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)",
            [("CMP-001", "Compresor 1/3 HP", "Compresores", 1850000, 10, 3),
             ("CAP-001", "Capacitor 10 uF", "Eléctricos", 55000, 2, 5)])
        db.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class Navegador:
    """Envuelve el cliente de pruebas y añade el token CSRF a cada POST."""

    def __init__(self, client):
        self.client = client

    def token(self):
        with self.client.session_transaction() as sesion:
            return sesion.setdefault("csrf_token", "token-de-prueba")

    def post(self, ruta, data=None, **kwargs):
        data = dict(data or {})
        data.setdefault("csrf_token", self.token())
        return self.client.post(ruta, data=data, **kwargs)

    def get(self, ruta, **kwargs):
        return self.client.get(ruta, **kwargs)

    def login(self, usuario="admin", password="admin12345"):
        return self.post("/auth/login", {"usuario": usuario, "password": password})


@pytest.fixture
def nav(client):
    return Navegador(client)


@pytest.fixture
def admin(nav):
    nav.login()
    return nav


@pytest.fixture
def vendedor(nav):
    nav.login("vendedor", "vende12345")
    return nav
