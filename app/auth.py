"""Inicio de sesión, cierre de sesión y control de acceso por rol."""
import functools

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def cargar_usuario():
    usuario_id = session.get("usuario_id")
    g.usuario = None
    if usuario_id is not None:
        g.usuario = get_db().execute(
            "SELECT id, usuario, nombre, rol FROM usuarios WHERE id = ? AND activo = 1", (usuario_id,)
        ).fetchone()
        if g.usuario is None:
            session.clear()


def login_requerido(vista):
    @functools.wraps(vista)
    def envoltura(**kwargs):
        if g.usuario is None:
            return redirect(url_for("auth.login", next=request.path))
        return vista(**kwargs)
    return envoltura


def admin_requerido(vista):
    @functools.wraps(vista)
    @login_requerido
    def envoltura(**kwargs):
        if g.usuario["rol"] != "admin":
            abort(403)
        return vista(**kwargs)
    return envoltura


def _destino_seguro(destino: str | None) -> str:
    # Solo se permiten rutas internas para evitar redirecciones abiertas.
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("reportes.panel")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.usuario is not None:
        return redirect(url_for("reportes.panel"))
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        password = request.form.get("password", "")
        fila = get_db().execute(
            "SELECT id, password_hash, activo FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
        if fila is None or not check_password_hash(fila["password_hash"], password):
            flash("Usuario o contraseña incorrectos.", "error")
        elif not fila["activo"]:
            flash("Este usuario está desactivado. Habla con el administrador.", "error")
        else:
            token = session.get("csrf_token")
            session.clear()
            if token:
                session["csrf_token"] = token
            session["usuario_id"] = fila["id"]
            return redirect(_destino_seguro(request.args.get("next")))
    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
