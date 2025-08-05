from fastapi import APIRouter
from app.productos.routes import router as productos_router
from app.telegram_bot.routes import router as telegram_router

router = APIRouter()
router.include_router(productos_router)
router.include_router(telegram_router)