from fastapi import FastAPI
from app.api import router

app = FastAPI(title="Bot Inventario API")

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido al API de tu bot inventario!"}
