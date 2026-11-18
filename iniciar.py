"""Lanzador para Windows: arranca el sistema en esta computadora y abre el navegador.

Los datos se guardan en %LOCALAPPDATA%\\SistemaVentas, separados del programa,
así se puede reemplazar el .exe por una versión nueva sin perder nada.
"""
import os
import socket
import sys
import threading
import webbrowser

PUERTO = 8765
DIRECCION = f"http://127.0.0.1:{PUERTO}"


def carpeta_datos() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    carpeta = os.path.join(base, "SistemaVentas")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def puerto_ocupado() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PUERTO)) == 0


def main() -> None:
    if puerto_ocupado():
        # El sistema ya está abierto (por ejemplo, se hizo doble clic dos veces): solo abrimos el navegador.
        webbrowser.open(DIRECCION)
        return

    os.environ.setdefault("CARPETA_DATOS", carpeta_datos())
    from waitress import serve

    from app import create_app

    app = create_app()
    print("=" * 60)
    print("  SISTEMA DE VENTAS E INVENTARIO")
    print("=" * 60)
    print(f"  El sistema está funcionando en: {DIRECCION}")
    print(f"  Tus datos se guardan en: {os.environ['CARPETA_DATOS']}")
    print()
    print("  NO CIERRES ESTA VENTANA mientras uses el sistema.")
    print("  Puedes minimizarla. Al cerrarla, el sistema se apaga.")
    print("=" * 60)
    threading.Timer(1.5, webbrowser.open, args=(DIRECCION,)).start()
    serve(app, host="127.0.0.1", port=PUERTO, threads=4, _quiet=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # Mostrar el error en vez de cerrar la ventana de golpe.
        print(f"\nOcurrió un error al iniciar el sistema: {error}")
        input("Pulsa Enter para cerrar...")
        sys.exit(1)
