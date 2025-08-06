from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    estado = Column(String, default="pendiente")
    prioridad = Column(String, default="media")
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_limite = Column(DateTime)