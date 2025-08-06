from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Bitacora(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True, index=True)
    accion = Column(String)
    entidad = Column(String)
    descripcion = Column(String)
    fecha = Column(DateTime, default=func.now())