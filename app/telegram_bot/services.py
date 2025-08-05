from fastapi.responses import JSONResponse
from app.telegram_bot.utils import es_usuario_autorizado, interpretar_comando

async def procesar_mensaje(message: dict):
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if not es_usuario_autorizado(user_id):
        return JSONResponse(content={"message": "Usuario no autorizado"}, status_code=200)

    respuesta = interpretar_comando(text)

    # Podrías guardar en DB, registrar log, etc.

    return JSONResponse(content={"message": respuesta}, status_code=200)
