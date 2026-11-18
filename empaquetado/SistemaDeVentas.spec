# Receta de PyInstaller para crear SistemaDeVentas.exe (Windows).
# Uso, desde la raíz del proyecto:
#   pip install -r requirements-build.txt
#   pyinstaller --noconfirm --clean --distpath empaquetado/dist --workpath empaquetado/build empaquetado/SistemaDeVentas.spec
import os

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(RAIZ, "iniciar.py")],
    pathex=[RAIZ],
    datas=[
        (os.path.join(RAIZ, "app", "templates"), "app/templates"),
        (os.path.join(RAIZ, "app", "static"), "app/static"),
        (os.path.join(RAIZ, "app", "schema.sql"), "app"),
    ],
    excludes=["pytest", "playwright", "PIL", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SistemaDeVentas",
    icon=os.path.join(SPECPATH, "icono.ico"),
    console=True,
    upx=False,
)
