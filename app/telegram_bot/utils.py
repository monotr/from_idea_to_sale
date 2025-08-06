import json
import os
import traceback
import requests
from openai import OpenAI
from app.config import settings


client = OpenAI(api_key=settings.OPENAI_API_KEY)
print("settings.OPENAI_API_KEY",settings.OPENAI_API_KEY)
print("cliente", client)
try:
    print("xxx")
    client.models.list()
    print("xxx")
    print("Conexión OK")
except Exception as e:
    print("Error:", e)

def es_usuario_autorizado(user_id: int) -> bool:
    # Comparar con tu ID personal
    return str(user_id) == settings.TELEGRAM_ADMIN_ID

def enviar_mensaje_telegram(chat_id: int, texto: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print("Error enviando mensaje de Telegram:")
        traceback.print_exc()

def descargar_audio_telegram(file_id: str, nombre_local: str = "audio.ogg") -> str:
    # 1. Obtener file_path del archivo
    url_get_file = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    r = requests.get(url_get_file)
    r.raise_for_status()
    file_path = r.json()["result"]["file_path"]

    # 2. Descargar el archivo usando file_path
    url_file = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
    r = requests.get(url_file)
    r.raise_for_status()

    # 3. Asegurar carpeta /tmp existe
    tmp_dir = "/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    # 4. Guardar archivo localmente
    ruta_local = os.path.join(tmp_dir, nombre_local)
    with open(ruta_local, "wb") as f:
        f.write(r.content)

    return ruta_local

def transcribir_audio_con_whisper(ruta_audio: str) -> str:
    with open(ruta_audio, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file, 
            response_format="text"
        )
        print("transcription",transcription)
        return transcription

def analizar_comando_con_gpt(texto: str) -> dict:
    try:
        system_prompt = """Eres un asistente que interpreta mensajes de voz transcritos de un usuario.  
Tu tarea es analizar el texto y generar una respuesta en formato JSON que indique la acción a realizar y sus parámetros.

Tu respuesta debe ser exclusivamente un JSON válido, con la siguiente estructura:

{
  "accion": "<nombre_de_la_accion>",
  "params": { ... }
}

Acciones posibles y sus parámetros:

1. "registrar_venta":
   - producto (str): nombre del producto vendido.
   - cantidad (int): cantidad vendida.
   - notas (str, opcional): contexto adicional.

2. "registrar_compra":
   - producto (str): nombre del producto o servicio comprado.
   - cantidad (int): cantidad comprada.
   - precio_total (float, opcional): monto total de la compra.
   - proveedor (str, opcional): a quién se le compró.
   - notas (str, opcional): detalles adicionales.

3. "crear_producto":
   - producto (str): nombre o descripción principal del producto (ej. "chimuelo chico").
   - cantidad (int, opcional): cuántos se agregan (default: 1).
   - tipo (str, opcional): categoría general, como "articulado", "decorativo", "accesorio", etc.
   - precio_unitario (float, opcional): precio de venta por unidad.
   - costo_produccion (float, opcional): costo interno por unidad.
   - tiempo_impresion (int, opcional): minutos que toma imprimir, si no son minutos conviértelo.
   - stock_alerta (int, opcional): nivel mínimo antes de alertar.
   - gramos (int, opcional): gramos usados por unidad.
   - etiquetas (list[str], opcional): palabras clave como "brilla en la oscuridad", "niño", "navideño", etc.
   - notas (str, opcional): motivo o contexto adicional.

   Al analizar el texto, intenta separar correctamente los elementos.  
   Por ejemplo, si se dice "chimuelo articulado chico con ojos que brillan en la oscuridad":
   - producto: "chimuelo chico"
   - tipo: "articulado"
   - etiquetas: ["brilla en la oscuridad"]
   - notas: si hay contexto adicional

4. "modificar_producto":
   - producto (str): nombre actual del producto que se desea modificar.
   - descripcion (str, opcional): nuevo nombre del producto.
   - tipo (str, opcional): nueva categoría.
   - precio_unitario (float, opcional): nuevo precio de venta por unidad.
   - costo_produccion (float, opcional): nuevo costo interno por unidad.
   - tiempo_impresion (int, opcional): nuevo tiempo de impresión en minutos.
   - stock_alerta (int, opcional): nuevo nivel de alerta de stock.
   - gramos (int, opcional): nuevos gramos por unidad.
   - etiquetas (list[str], opcional): etiquetas actualizadas.
   - notas (str, opcional): nueva nota o descripción adicional.

5. "registrar_gasto":
   - descripcion (str): concepto del gasto (ej. gasolina, renta).
   - monto (float): cantidad gastada.
   - categoria (str, opcional): tipo de gasto (ej. transporte, servicios).
   - notas (str, opcional): detalles adicionales.

6. "crear_cotizacion":
   - cliente (str, opcional): nombre del cliente.
   - productos (list): lista de objetos con:
     - producto (str)
     - cantidad (int)
   - notas (str, opcional)

7. "registrar_evento":
   - nombre (str): nombre del evento.
   - fecha (str, opcional): en formato YYYY-MM-DD o texto libre.
   - descripcion (str, opcional)

8. "crear_tarea":
   - descripcion (str): lo que se debe hacer.
   - fecha (str, opcional): en formato YYYY-MM-DD o texto libre.
   - prioridad (str, opcional): baja, media o alta.

9. "resumen_inventario":
   - sin campos adicionales. Deja "params": {}.

10. "ver_producto":
    - producto (str): nombre del producto a consultar (ej. Stitch, Clicker, etc.)

11. "otro":
   - Usa esta acción si el mensaje no puede clasificarse.
   - "params": {"texto_original": "<texto_recibido>"}

Reglas importantes:
- Si no se menciona una cantidad, asume **1**.
- Si falta el nombre del producto o concepto, usa **"desconocido"**.
- Si no hay detalles suficientes, completa solo los campos posibles.
- No escribas explicaciones, comentarios, encabezados, ni texto adicional. Solo responde con un **JSON plano y válido**.
- Sé lo más preciso posible con base en el texto recibido.
- Si puedes intuir categorías, etiquetas o campos a partir de adjetivos o descripciones, hazlo.

Ejemplo de respuesta esperada:

{
  "accion": "crear_producto",
  "params": {
    "producto": "chimuelo chico",
    "tipo": "articulado",
    "etiquetas": ["brilla en la oscuridad"],
    "cantidad": 1
  }
}
"""
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto}
            ],
        )
        print("chatgpt respuesta",respuesta.choices[0].message.content)

        return respuesta.choices[0].message.content

    except Exception as e:
        print("❌ Error al procesar el texto con ChatGPT:")
        print("Texto transcrito:", texto)
        print("Error:", e)
        traceback.print_exc()
        return {
            "accion": "otro",
            "params": {
                "producto": "desconocido",
                "cantidad": 1,
                "notas": f"Error al interpretar mensaje: {str(e)}"
            }
        }
    
def analizar_modificacion_con_gpt(texto: str, accion: str, params_actuales: dict) -> dict:
    try:
        CAMPOS_POR_ACCION = {
            "crear_producto": {
                "producto": "nombre del producto",
                "cantidad": "cuántos se agregan (int)",
                "tipo": "categoría general",
                "precio_unitario": "precio de venta por unidad",
                "costo_produccion": "costo interno por unidad",
                "tiempo_impresion": "minutos de impresión, si no viene en minutos conviertelo",
                "stock_alerta": "nivel mínimo antes de alertar",
                "gramos": "gramos por unidad",
                "etiquetas": "etiquetas descriptivas",
                "notas": "contexto o descripción"
            },
            "modificar_producto": {
                "producto": "nombre del producto a modificar",
                "descripcion": "nuevo nombre del producto si se quiere cambiar",
                "tipo": "nueva categoría general",
                "precio_unitario": "nuevo precio de venta por unidad",
                "costo_produccion": "nuevo costo interno por unidad",
                "tiempo_impresion": "nuevo tiempo de impresión (en minutos)",
                "stock_alerta": "nuevo nivel mínimo de stock",
                "gramos": "nuevos gramos por unidad",
                "etiquetas": "etiquetas actualizadas",
                "notas": "nueva nota o descripción"
            },
            "registrar_venta": {
                "producto": "nombre del producto vendido",
                "cantidad": "cantidad vendida",
                "notas": "detalles adicionales"
            },
            "registrar_compra": {
                "producto": "nombre del producto comprado",
                "cantidad": "cantidad comprada",
                "precio_total": "monto total",
                "proveedor": "quién vendió",
                "notas": "contexto adicional"
            },
            # agrega más acciones si quieres
        }

        campos_esperados = CAMPOS_POR_ACCION.get(accion, {})

        system_prompt = f"""Eres un asistente que ayuda a completar o modificar los parámetros para la acción `{accion}`.

Parámetros actuales:
{json.dumps(params_actuales, indent=2, ensure_ascii=False)}

Estos son los campos esperados para esta acción:
{json.dumps(list(campos_esperados.keys()), indent=2)}

El usuario ha enviado un nuevo mensaje. Tu tarea es:
- Modificar o agregar parámetros según el mensaje.
- Mantener los existentes si no son modificados.
- NO eliminar ningún campo existente.
- Incluir solo los campos esperados para esta acción.
- El tiempo de impresion es un INT minutos, si viene de otra forma convertir

Responde SOLO con un JSON válido con la estructura:

{{
  "params": {{
    ...
  }}
}}

No escribas explicaciones, comentarios ni encabezados. Solo JSON plano.
"""

        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto}
            ],
        )
        print("🤖 Respuesta GPT (modificación):", respuesta.choices[0].message.content)
        return json.loads(respuesta.choices[0].message.content)

    except Exception as e:
        print("❌ Error al procesar la modificación con ChatGPT:")
        print("Acción:", accion)
        print("Texto:", texto)
        print("Params actuales:", params_actuales)
        print("Error:", e)
        traceback.print_exc()
        return {
            "params": params_actuales
        }


