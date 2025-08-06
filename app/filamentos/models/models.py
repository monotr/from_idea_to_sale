from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Filamento(Base):
    __tablename__ = "filamentos"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    color = Column(String)
    gramos_disponibles = Column(Integer)
    gramos_totales = Column(Integer)
    uso_proyecto = Column(String)