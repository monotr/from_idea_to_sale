from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.productos.schemas import ProductCreate, ProductResponse
from app.productos.service import ProductServices
from typing import List

router = APIRouter(prefix="/productos", tags=["Productos"])
domain = ProductServices()

@router.post("/", response_model=ProductResponse)
def crear_producto(data: ProductCreate, db: Session = Depends(get_db)):
    return domain.crear_producto(db, data)

@router.get("/", response_model=List[ProductResponse])
def listar_productos(db: Session = Depends(get_db)):
    return domain.obtener_productos(db)
