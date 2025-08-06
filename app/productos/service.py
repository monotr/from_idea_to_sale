from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.productos.models import Etiqueta, Product, ProductoTipo
from app.productos.schemas import ProductCreate


class ProductServices:
    def __init__(self):
        pass

    def agregar_inventario(self, params: dict):
        db = SessionLocal()

        try:
            nombre = params.get("producto", "desconocido")
            cantidad = params.get("cantidad", 1)
            tipo_nombre = params.get("tipo")
            precio_unitario = params.get("precio_unitario")
            costo_produccion = params.get("costo_produccion")
            tiempo_impresion = params.get("tiempo_impresion")
            stock_alerta = params.get("stock_alerta")
            gramos = params.get("gramos")
            etiquetas = params.get("etiquetas", []) or []
            notas = params.get("notas")

            # Buscar producto existente
            producto = db.query(Product).filter_by(descripcion=nombre).first()

            if producto:
                # Ya existe → sumamos la cantidad
                producto.cantidad += cantidad
                if notas:
                    producto.notas = (producto.notas or "") + f"\n+ {notas}"
            else:
                # Si viene tipo, buscarlo o crearlo
                tipo = None
                if tipo_nombre:
                    tipo = db.query(ProductoTipo).filter_by(nombre=tipo_nombre).first()
                    if not tipo:
                        tipo = ProductoTipo(nombre=tipo_nombre)
                        db.add(tipo)
                        db.commit()

                producto = Product(
                    descripcion=nombre,
                    cantidad=cantidad,
                    tipo_id=tipo.id if tipo else None,
                    precio_unitario=precio_unitario or 0.0,
                    costo_produccion=costo_produccion or 0.0,
                    tiempo_impresion=tiempo_impresion or 0.0,
                    stock_alerta=stock_alerta or 0,
                    gramos=gramos or 0,
                    notas=notas,
                )
                db.add(producto)
                db.commit()

            # Si vienen etiquetas, vincular
            if etiquetas:
                for nombre_etiqueta in etiquetas:
                    etiqueta = db.query(Etiqueta).filter_by(nombre=nombre_etiqueta).first()
                    if not etiqueta:
                        etiqueta = Etiqueta(nombre=nombre_etiqueta)
                        db.add(etiqueta)
                        db.commit()
                    if etiqueta not in producto.etiquetas:
                        producto.etiquetas.append(etiqueta)

            db.commit()
            return {"mensaje": f"Inventario actualizado: {producto.descripcion} (+{cantidad})"}

        except Exception as e:
            print("Error en agregar_inventario:")
            import traceback
            traceback.print_exc()
            return {"error": "Error al agregar al inventario"}

        finally:
            db.close()
