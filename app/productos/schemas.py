from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    cantidad: int
    precio: float

class ProductResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    cantidad: int
    precio: float

    class Config:
        from_attributes = True
