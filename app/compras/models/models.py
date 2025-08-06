from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    proveedor = Column(String)
    cantidad = Column(Integer)
    costo_total = Column(Float)
    categoria = Column(String)
    fecha = Column(DateTime, default=func.now())