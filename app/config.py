from dotenv import load_dotenv
import os

load_dotenv()  # Carga variables de entorno desde .env

class Settings:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
    DB_URL = os.getenv("DB_URL")

settings = Settings()
