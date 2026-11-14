"""Sistema de Ventas e Inventario - fábrica de la aplicación Flask."""
import os

from flask import Flask, redirect, render_template, url_for

from . import auth, db, productos, reportes, seguridad, usuarios, ventas
from .utils import formatear_dinero, formatear_dinero_corto, formatear_fecha


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-cambia-esta-clave"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "ventas.sqlite")),
        NOMBRE_TIENDA=os.environ.get("NOMBRE_TIENDA", "FríoTech · Refrigeración"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PRODUCTOS_POR_PAGINA=15,
    )
    if config:
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    seguridad.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(productos.bp)
    app.register_blueprint(ventas.bp)
    app.register_blueprint(reportes.bp)
    app.register_blueprint(usuarios.bp)

    app.add_template_filter(formatear_dinero, "dinero")
    app.add_template_filter(formatear_dinero_corto, "dinero_corto")
    app.add_template_filter(formatear_fecha, "fecha")

    @app.context_processor
    def datos_globales():
        return {"nombre_tienda": app.config["NOMBRE_TIENDA"]}

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
