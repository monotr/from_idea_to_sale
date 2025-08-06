import enum
from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String, Boolean, func
from app.db import Base

class TelegramTranscripcion(Base):
    __tablename__ = "telegram_transcripciones"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, unique=True, index=True)
    texto = Column(String)
    procesado = Column(Boolean, default=False)

class EstadoAccion(str, enum.Enum):
    pendiente_confirmacion = "pendiente_confirmacion"
    confirmada = "confirmada"
    cancelada = "cancelada"
    ejecutada = "ejecutada"
    error = "error"

class AccionPendiente(Base):
    __tablename__ = "acciones_pendientes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)  # ID de Telegram u otro identificador
    accion = Column(String, nullable=False)  # Ej. "crear_producto"
    params_json = Column(JSON, nullable=False)  # Los parámetros detectados
    mensaje_original = Column(String, nullable=True)  # El mensaje transcrito completo
    estado = Column(Enum(EstadoAccion), default=EstadoAccion.pendiente_confirmacion)
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_confirmacion = Column(DateTime, nullable=True)