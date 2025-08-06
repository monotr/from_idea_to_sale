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

    def modificar_producto(self, params: dict):
        db = SessionLocal()

        try:
            producto_id = params.get("producto_id")
            nombre = params.get("producto")

            if not producto_id and not nombre:
                return {"error": "Debes proporcionar el ID o nombre del producto para modificarlo."}

            # Buscar el producto
            query = db.query(Product)
            if producto_id:
                producto = query.filter_by(id=producto_id).first()
            else:
                producto = query.filter(Product.descripcion.ilike(f"%{nombre}%")).first()

            if not producto:
                return {"error": "Producto no encontrado."}

            # Actualizar solo los campos presentes
            if "descripcion" in params or "producto" in params:
                producto.descripcion = params.get("descripcion") or nombre

            if "tipo" in params:
                tipo_nombre = params["tipo"]
                tipo = db.query(ProductoTipo).filter_by(nombre=tipo_nombre).first()
                if not tipo:
                    tipo = ProductoTipo(nombre=tipo_nombre)
                    db.add(tipo)
                    db.commit()
                producto.tipo_id = tipo.id

            if "precio_unitario" in params:
                producto.precio_unitario = params["precio_unitario"]

            if "costo_produccion" in params:
                producto.costo_produccion = params["costo_produccion"]

            if "tiempo_impresion" in params:
                producto.tiempo_impresion = params["tiempo_impresion"]

            if "stock_alerta" in params:
                producto.stock_alerta = params["stock_alerta"]

            if "gramos" in params:
                producto.gramos = params["gramos"]

            if "notas" in params:
                producto.notas = params["notas"]

            if "etiquetas" in params:
                etiquetas = params["etiquetas"] or []
                nuevas = []
                for nombre_etiqueta in etiquetas:
                    etiqueta = db.query(Etiqueta).filter_by(nombre=nombre_etiqueta).first()
                    if not etiqueta:
                        etiqueta = Etiqueta(nombre=nombre_etiqueta)
                        db.add(etiqueta)
                        db.commit()
                    nuevas.append(etiqueta)
                producto.etiquetas = nuevas  # Reemplaza completamente

            db.commit()
            return {"mensaje": f"Producto actualizado: {producto.descripcion}"}

        except Exception as e:
            print("Error en modificar_producto:")
            import traceback
            traceback.print_exc()
            return {"error": "Error al modificar el producto"}

        finally:
            db.close()

    def obtener_producto(self, nombre: str) -> dict:
        db = SessionLocal()
        try:
            producto = db.query(Product).filter(Product.descripcion.ilike(f"%{nombre}%")).first()

            if not producto:
                return {"error": f"No se encontró un producto que coincida con '{nombre}'."}

            return {
                "id": producto.id,
                "producto": producto.descripcion,
                "cantidad": producto.cantidad,
                "tipo": producto.tipo.nombre if producto.tipo else None,
                "precio_unitario": producto.precio_unitario,
                "costo_produccion": producto.costo_produccion,
                "tiempo_impresion": producto.tiempo_impresion,
                "stock_alerta": producto.stock_alerta,
                "gramos": producto.gramos,
                "etiquetas": [et.nombre for et in producto.etiquetas],
                "notas": producto.notas
            }

        except Exception as e:
            print("Error en get_producto:")
            import traceback
            traceback.print_exc()
            return {"error": "Error al obtener el producto."}

        finally:
            db.close()

