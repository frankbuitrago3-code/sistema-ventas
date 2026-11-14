"""Punto de entrada para servidores de producción (por ejemplo: gunicorn wsgi:app)."""
from app import create_app

app = create_app()
