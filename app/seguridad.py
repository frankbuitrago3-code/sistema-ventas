"""Protección CSRF sencilla: cada formulario POST debe enviar el token de la sesión."""
import hmac
import secrets

from flask import abort, request, session

CAMPO = "csrf_token"


def generar_token() -> str:
    if CAMPO not in session:
        session[CAMPO] = secrets.token_urlsafe(32)
    return session[CAMPO]


def init_app(app) -> None:
    app.jinja_env.globals["csrf_token"] = generar_token

    @app.before_request
    def validar_csrf():
        if request.method != "POST":
            return
        enviado = request.form.get(CAMPO, "")
        esperado = session.get(CAMPO, "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, "Token de seguridad inválido. Recarga la página e inténtalo de nuevo.")
