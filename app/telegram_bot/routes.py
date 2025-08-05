from fastapi import APIRouter, Request, HTTPException
from app.telegram_bot.services import procesar_mensaje

router = APIRouter(prefix="/webhook", tags=["Telegram Bot"])

@router.post("/telegram")
async def telegram_webhook(request: Request):
    payload = await request.json()
    print("Mensaje recibido:", payload)

    # Validación mínima
    if "message" not in payload:
        raise HTTPException(status_code=400, detail="Sin mensaje válido")

    return await procesar_mensaje(payload["message"])
