import os

def es_usuario_autorizado(user_id: int) -> bool:
    # Comparar con tu ID personal
    return str(user_id) == os.getenv("TELEGRAM_ADMIN_ID")

def interpretar_comando(texto: str) -> str:
    texto = texto.lower()

    if "vendí" in texto or "vendi" in texto:
        return "¡Ok! Registraremos la venta (pendiente lógica)"
    elif "agrega" in texto or "agregar" in texto:
        return "¡Perfecto! Agregaremos al inventario (pendiente lógica)"
    elif "resumen" in texto:
        return "Resumen de inventario: (pendiente implementar)"
    else:
        return "No entendí el comando. Intenta con: vendí / agrega / resumen"
