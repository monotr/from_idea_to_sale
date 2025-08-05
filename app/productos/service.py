from sqlalchemy.orm import Session
from app.productos.models import Product
from app.productos.schemas import ProductCreate
from app.productos.dao import ProductDAO

class ProductServices:
    def __init__(self):
        self.dao = ProductDAO()

    def crear_producto(self, db: Session, data: ProductCreate):
        producto = Product(
            nombre=data.nombre,
            descripcion=data.descripcion,
            cantidad=data.cantidad,
            precio=data.precio,
        )
        return self.dao.crear_producto(db, producto)

    def obtener_productos(self, db: Session):
        return self.dao.obtener_todos(db)
