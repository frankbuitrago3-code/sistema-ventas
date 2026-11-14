"""Gestión de usuarios (solo administradores)."""
import sqlite3

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .auth import admin_requerido
from .db import crear_usuario, get_db

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

ROLES = {"admin": "Administrador", "vendedor": "Vendedor"}


@bp.route("/")
@admin_requerido
def listar():
    usuarios = get_db().execute(
        """SELECT u.*, (SELECT COUNT(*) FROM ventas v WHERE v.usuario_id = u.id AND v.estado = 'completada') AS ventas
           FROM usuarios u ORDER BY u.activo DESC, u.nombre""").fetchall()
    return render_template("usuarios/lista.html", usuarios=usuarios, roles=ROLES)


@bp.route("/nuevo", methods=("GET", "POST"))
@admin_requerido
def nuevo():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "")
        rol = request.form.get("rol", "")
        errores = []
        if not usuario.isalnum():
            errores.append("El usuario solo puede tener letras y números, sin espacios.")
        if not nombre:
            errores.append("El nombre es obligatorio.")
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if rol not in ROLES:
            errores.append("Elige un rol válido.")
        if not errores:
            try:
                crear_usuario(usuario, nombre, password, rol)
            except sqlite3.IntegrityError:
                errores.append(f"El usuario «{usuario}» ya existe.")
            else:
                flash(f"Usuario «{usuario}» creado.", "ok")
                return redirect(url_for("usuarios.listar"))
        for error in errores:
            flash(error, "error")
    return render_template("usuarios/formulario.html", roles=ROLES, datos=request.form)


@bp.route("/<int:usuario_id>/estado", methods=("POST",))
@admin_requerido
def cambiar_estado(usuario_id):
    if usuario_id == g.usuario["id"]:
        flash("No puedes desactivar tu propio usuario.", "error")
        return redirect(url_for("usuarios.listar"))
    db = get_db()
    usuario = db.execute("SELECT usuario, activo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if usuario is None:
        abort(404)
    db.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (0 if usuario["activo"] else 1, usuario_id))
    db.commit()
    flash(f"Usuario «{usuario['usuario']}» {'desactivado' if usuario['activo'] else 'activado'}.", "ok")
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:usuario_id>/password", methods=("POST",))
@admin_requerido
def cambiar_password(usuario_id):
    password = request.form.get("password", "")
    if len(password) < 8:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("usuarios.listar"))
    db = get_db()
    if db.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                  (generate_password_hash(password), usuario_id)).rowcount == 0:
        abort(404)
    db.commit()
    flash("Contraseña actualizada.", "ok")
    return redirect(url_for("usuarios.listar"))
