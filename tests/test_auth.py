def test_rutas_protegidas_redirigen_al_login(client):
    for ruta in ["/panel", "/productos/", "/ventas/", "/ventas/nueva", "/reportes", "/usuarios/"]:
        respuesta = client.get(ruta)
        assert respuesta.status_code == 302
        assert "/auth/login" in respuesta.headers["Location"]


def test_login_correcto_e_incorrecto(nav):
    malo = nav.login("admin", "equivocada")
    assert "Usuario o contraseña incorrectos" in malo.get_data(as_text=True)

    bueno = nav.login()
    assert bueno.status_code == 302
    assert nav.get("/panel").status_code == 200


def test_post_sin_token_csrf_es_rechazado(client):
    respuesta = client.post("/auth/login", data={"usuario": "admin", "password": "admin12345"})
    assert respuesta.status_code == 400


def test_logout(admin):
    admin.post("/auth/logout")
    assert admin.get("/panel").status_code == 302


def test_redireccion_externa_bloqueada(nav):
    respuesta = nav.post("/auth/login?next=//sitio-malicioso.com",
                         {"usuario": "admin", "password": "admin12345"})
    assert respuesta.headers["Location"] == "/panel"


def test_vendedor_no_accede_a_zonas_de_admin(vendedor):
    for ruta in ["/reportes", "/usuarios/", "/productos/nuevo"]:
        assert vendedor.get(ruta).status_code == 403


def test_usuario_desactivado_no_puede_entrar(admin, app):
    admin.post("/usuarios/2/estado")  # desactiva al vendedor
    admin.post("/auth/logout")
    respuesta = admin.login("vendedor", "vende12345")
    assert "desactivado" in respuesta.get_data(as_text=True)
