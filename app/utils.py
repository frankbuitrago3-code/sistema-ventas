"""Funciones de ayuda para importes y fechas."""
from datetime import datetime
from decimal import Decimal, InvalidOperation


def formatear_dinero(centavos: int | None) -> str:
    """1234550 -> '$12.345,50' (formato español)."""
    centavos = centavos or 0
    signo = "-" if centavos < 0 else ""
    texto = f"{abs(centavos) / 100:,.2f}"  # 12,345.50
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{signo}${texto}"


def formatear_dinero_corto(centavos: int | None) -> str:
    """1234550 -> '$12.346' (sin decimales, para gráficos)."""
    return formatear_dinero(round((centavos or 0) / 100) * 100)[:-3]


def a_centavos(valor: str | None) -> int | None:
    """Convierte lo que escribe el usuario ('12,50', '12.50', '1.234,50') a centavos.

    Devuelve None si el valor no es un importe válido o es negativo.
    """
    if valor is None:
        return None
    texto = valor.strip().replace("$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto:
        # Formato español: el punto separa miles y la coma los decimales.
        texto = texto.replace(".", "").replace(",", ".")
    try:
        importe = Decimal(texto)
    except InvalidOperation:
        return None
    if importe < 0 or importe != importe:  # negativo o NaN
        return None
    return int((importe * 100).quantize(Decimal("1")))


def a_entero(valor: str | None, minimo: int = 0) -> int | None:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    return numero if numero >= minimo else None


def formatear_fecha(texto: str | None, con_hora: bool = True) -> str:
    if not texto:
        return ""
    try:
        fecha = datetime.fromisoformat(texto)
    except ValueError:
        return texto
    return fecha.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
