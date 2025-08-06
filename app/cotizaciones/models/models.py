from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String)
    productos_json = Column(String)
    total_estimado = Column(Float)
    estado = Column(String, default="pendiente")
    fecha = Column(DateTime, default=func.now())