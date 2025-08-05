from sqlalchemy.orm import Session
from app.productos.models import Product

class ProductDAO:

    def crear_producto(self, db: Session, producto):
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto

    def obtener_todos(self, db: Session):
        return db.query(Product).all()
