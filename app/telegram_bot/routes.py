from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.telegram_bot.services import manejar_mensaje_telegram
from fastapi import BackgroundTasks

from app.telegram_bot.utils import enviar_mensaje_telegram

router = APIRouter(prefix="/webhook", tags=["Telegram Bot"])
@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print("Mensaje recibido:", payload)

    if "message" not in payload:
        return JSONResponse(status_code=200, content={"message": "Sin mensaje válido"})

    message = payload["message"]

    # Responde de inmediato y lanza proceso en segundo plano
    background_tasks.add_task(manejar_mensaje_telegram, message)

    # Si quieres, puedes responderle algo al usuario de inmediato:
    chat_id = message["chat"]["id"]
    enviar_mensaje_telegram(chat_id, "Recibido. Estoy procesando tu mensaje...")

    return JSONResponse(status_code=200, content={"message": "Procesando en segundo plano"})


