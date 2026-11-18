"""Configuración inicial (primer uso), ajustes del negocio y copia de seguridad."""
import io
import re
import sqlite3
from datetime import date

from flask import (Blueprint, current_app, flash, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import generate_password_hash

from .auth import admin_requerido
from .db import get_db

bp = Blueprint("configuracion", __name__)

# Rutas que se pueden abrir aunque todavía no exista ningún usuario.
LIBRES = {"configuracion.inicial", "static"}


def obtener_ajuste(clave: str, por_defecto: str | None = None) -> str | None:
    fila = get_db().execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,)).fetchone()
    return fila["valor"] if fila else por_defecto


def guardar_ajuste(conexion: sqlite3.Connection, clave: str, valor: str) -> None:
    conexion.execute(
        "INSERT INTO ajustes (clave, valor) VALUES (?, ?) ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )


def hay_usuarios() -> bool:
    return get_db().execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None


@bp.before_app_request
def exigir_configuracion():
    """Mientras no haya ningún usuario, todo lleva a la pantalla de configuración inicial."""
    if current_app.config.get("_configurado"):
        return None
    if hay_usuarios():
        current_app.config["_configurado"] = True
        return None
    if request.endpoint not in LIBRES:
        return redirect(url_for("configuracion.inicial"))
    return None


def _validar(nombre_tienda: str, nombre: str, usuario: str, password: str, password2: str) -> list[str]:
    errores = []
    if not nombre_tienda:
        errores.append("Escribe el nombre de tu negocio.")
    if not nombre:
        errores.append("Escribe tu nombre.")
    if not re.fullmatch(r"[a-z0-9]+", usuario):
        errores.append("El usuario solo puede tener letras y números, sin espacios ni tildes.")
    if len(password) < 8:
        errores.append("La contraseña debe tener al menos 8 caracteres.")
    elif password != password2:
        errores.append("Las contraseñas no coinciden.")
    return errores


@bp.route("/configuracion-inicial", methods=("GET", "POST"))
def inicial():
    if hay_usuarios():
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        f = request.form
        nombre_tienda = f.get("nombre_tienda", "").strip()[:60]
        nombre = f.get("nombre", "").strip()[:80]
        usuario = f.get("usuario", "").strip().lower()[:40]
        password = f.get("password", "")
        errores = _validar(nombre_tienda, nombre, usuario, password, f.get("password2", ""))
        if errores:
            for error in errores:
                flash(error, "error")
        else:
            conexion = get_db()
            conexion.execute("BEGIN IMMEDIATE")
            # Se vuelve a comprobar dentro de la transacción: solo el primero crea el administrador.
            if conexion.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
                conexion.rollback()
                return redirect(url_for("auth.login"))
            cursor = conexion.execute(
                "INSERT INTO usuarios (usuario, nombre, password_hash, rol) VALUES (?, ?, ?, 'admin')",
                (usuario, nombre, generate_password_hash(password)),
            )
            guardar_ajuste(conexion, "nombre_tienda", nombre_tienda)
            conexion.commit()
            token = session.get("csrf_token")
            session.clear()
            if token:
                session["csrf_token"] = token
            session["usuario_id"] = cursor.lastrowid
            flash("¡Listo! Tu sistema está configurado. Empieza registrando tus productos en Inventario.", "ok")
            return redirect(url_for("productos.listar"))
    return render_template("configuracion/inicial.html")


@bp.route("/ajustes", methods=("GET", "POST"))
@admin_requerido
def ajustes():
    if request.method == "POST":
        nombre_tienda = request.form.get("nombre_tienda", "").strip()[:60]
        if not nombre_tienda:
            flash("El nombre del negocio no puede quedar vacío.", "error")
        else:
            conexion = get_db()
            guardar_ajuste(conexion, "nombre_tienda", nombre_tienda)
            conexion.commit()
            flash("Nombre del negocio actualizado.", "ok")
            return redirect(url_for("configuracion.ajustes"))
    return render_template("configuracion/ajustes.html")


@bp.route("/ajustes/copia-de-seguridad")
@admin_requerido
def copia_seguridad():
    """Descarga una copia completa y consistente de la base de datos."""
    datos = get_db().serialize()
    nombre = f"copia-ventas-{date.today().isoformat()}.sqlite"
    return send_file(io.BytesIO(datos), mimetype="application/vnd.sqlite3",
                     as_attachment=True, download_name=nombre)
