"""Sistema de Ventas e Inventario - fábrica de la aplicación Flask."""
import os
import secrets

from flask import Flask, redirect, render_template, url_for

from . import auth, configuracion, db, productos, reportes, seguridad, usuarios, ventas
from .utils import formatear_dinero, formatear_dinero_corto, formatear_fecha


def _clave_secreta(carpeta: str) -> str:
    """Usa SECRET_KEY si está definida; si no, genera una aleatoria y la guarda para reutilizarla."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    ruta = os.path.join(carpeta, "clave_secreta.txt")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as archivo:
            clave = archivo.read().strip()
        if clave:
            return clave
    clave = secrets.token_hex(32)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(clave)
    return clave


def create_app(config: dict | None = None) -> Flask:
    # CARPETA_DATOS permite guardar la base de datos fuera del programa (lo usa el instalador de Windows).
    app = Flask(__name__, instance_relative_config=True, instance_path=os.environ.get("CARPETA_DATOS"))
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=_clave_secreta(app.instance_path),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "ventas.sqlite")),
        NOMBRE_TIENDA=os.environ.get("NOMBRE_TIENDA", "Sistema de Ventas"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PRODUCTOS_POR_PAGINA=15,
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    seguridad.init_app(app)
    # Crea las tablas que falten (no borra datos), así el programa arranca solo la primera vez.
    with app.app_context():
        db.init_db()

    app.register_blueprint(auth.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(ventas.bp)
    app.register_blueprint(reportes.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(configuracion.bp)

    app.add_template_filter(formatear_dinero, "dinero")
    app.add_template_filter(formatear_dinero_corto, "dinero_corto")
    app.add_template_filter(formatear_fecha, "fecha")

    @app.context_processor
    def datos_globales():
        return {"nombre_tienda": configuracion.obtener_ajuste("nombre_tienda", app.config["NOMBRE_TIENDA"])}

    @app.route("/")
    def inicio():
        return redirect(url_for("reportes.panel"))

    @app.errorhandler(403)
    def prohibido(_e):
        return render_template("errores/error.html", codigo=403,
                               mensaje="No tienes permiso para ver esta página."), 403

    @app.errorhandler(404)
    def no_encontrado(_e):
        return render_template("errores/error.html", codigo=404,
                               mensaje="La página que buscas no existe."), 404

    return app
