from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from app.db import SessionLocal
from app.telegram_bot.models import TelegramTranscripcion, AccionPendiente, EstadoAccion
from app.telegram_bot.utils import (
    enviar_mensaje_telegram,
    es_usuario_autorizado,
    descargar_audio_telegram,
    transcribir_audio_con_whisper,
    analizar_comando_con_gpt,
    analizar_modificacion_con_gpt
)
from app.productos.service import ProductServices
import traceback
import json
from copy import deepcopy

POTENCIALES_CAMPOS = {
    "tipo": "tipo de producto",
    "precio_unitario": "precio unitario",
    "costo_produccion": "costo de producción",
    "tiempo_impresion": "tiempo de impresión (minutos)",
    "stock_alerta": "nivel de alerta de stock",
    "gramos": "gramos por unidad",
    "etiquetas": "etiquetas",
    "notas": "notas o descripción adicional"
}

ACCIONES_VALIDAS = {
    "agregar_inventario": ProductServices().agregar_inventario,
    "crear_producto": ProductServices().agregar_inventario,
    "modificar_producto": ProductServices().modificar_producto,
}

async def manejar_mensaje_telegram(message: dict):
    try:
        db = SessionLocal()
        message_id = message["message_id"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]

        if not es_usuario_autorizado(user_id):
            return JSONResponse(content={"message": "Usuario no autorizado"}, status_code=200)

        if ya_fue_procesado(db, message_id):
            return JSONResponse(content={"message": "Ya procesado"}, status_code=200)

        accion_pendiente = obtener_accion_pendiente(db, user_id)

        if accion_pendiente:
            return await procesar_accion_pendiente(db, message, accion_pendiente, chat_id)

        texto = await obtener_texto_del_mensaje(message)
        guardar_transcripcion(db, message_id, texto)

        resultado = json.loads(analizar_comando_con_gpt(texto))
        guardar_accion_pendiente(db, user_id, resultado, texto)

        await enviar_mensaje_confirmacion(chat_id, resultado)
        return JSONResponse(content={"accion": resultado.get("accion")}, status_code=200)

    except Exception:
        traceback.print_exc()
        return JSONResponse(content={"message": "Error interno, pero se responde 200 para evitar reintentos"}, status_code=200)

def ya_fue_procesado(db, message_id):
    return db.query(TelegramTranscripcion).filter_by(message_id=message_id).first()

def obtener_accion_pendiente(db, user_id):
    un_minuto_atras = datetime.utcnow() - timedelta(minutes=1)
    return db.query(AccionPendiente).filter(
        AccionPendiente.user_id == str(user_id),
        AccionPendiente.estado == EstadoAccion.pendiente_confirmacion,
        AccionPendiente.fecha_creacion >= un_minuto_atras
    ).order_by(AccionPendiente.fecha_creacion.desc()).first()

async def obtener_texto_del_mensaje(message):
    if "text" in message:
        return message["text"]
    elif "voice" in message:
        file_id = message["voice"]["file_id"]
        ruta_audio = descargar_audio_telegram(file_id)
        return transcribir_audio_con_whisper(ruta_audio)
    return "(no compatible)"

def guardar_transcripcion(db, message_id, texto):
    trans = TelegramTranscripcion(message_id=message_id, texto=texto, procesado=True)
    db.add(trans)
    db.commit()

def guardar_accion_pendiente(db, user_id, resultado, texto):
    nueva = AccionPendiente(
        user_id=str(user_id),
        accion=resultado.get("accion"),
        params_json=resultado.get("params"),
        mensaje_original=texto,
        estado=EstadoAccion.pendiente_confirmacion
    )
    db.add(nueva)
    db.commit()

async def enviar_mensaje_confirmacion(chat_id, resultado):
    params = resultado.get("params", {})
    preview = json.dumps(params, indent=2, ensure_ascii=False)
    faltan = [v for k, v in POTENCIALES_CAMPOS.items() if k not in params]

    mensaje = (
        f"📝 Acción detectada:\n*{resultado.get('accion')}*\n\n"
        f"📦 Detalles:\n```\n{preview}\n```\n"
    )
    if faltan:
        mensaje += "\n️Puedes agregar también:\n- " + "\n- ".join(faltan) + "\n"
    mensaje += "\n❓¿Deseas confirmar esta acción?\nResponde con /confirmar o /cancelar."
    enviar_mensaje_telegram(chat_id, mensaje)

async def procesar_accion_pendiente(db, message, accion_pendiente, chat_id):
    texto = await obtener_texto_del_mensaje(message)
    texto_usuario = texto.strip().lower()

    if texto_usuario == "/cancelar":
        accion_pendiente.estado = EstadoAccion.cancelada
        db.commit()
        enviar_mensaje_telegram(chat_id, "❌ Acción cancelada.")
        return JSONResponse(content={"message": "Acción cancelada"}, status_code=200)

    elif texto_usuario == "/confirmar":
        if accion_pendiente.fecha_creacion < datetime.utcnow() - timedelta(minutes=1):
            return JSONResponse(content={"message": "⚠️ La acción pendiente expiró."}, status_code=200)

        try:
            if accion_pendiente.accion in ACCIONES_VALIDAS:
                funcion = ACCIONES_VALIDAS[accion_pendiente.accion]
                respuesta = funcion(accion_pendiente.params_json)
            else:
                raise ValueError(f"Acción no soportada: {accion_pendiente.accion}")

            accion_pendiente.estado = EstadoAccion.confirmada
            db.commit()
            accion_pendiente.estado = EstadoAccion.ejecutada
            db.commit()

            enviar_mensaje_telegram(chat_id, f"✅ Acción ejecutada:\n{respuesta}")
            return JSONResponse(content={"message": "Acción confirmada y ejecutada"}, status_code=200)

        except Exception as e:
            traceback.print_exc()
            accion_pendiente.estado = EstadoAccion.error
            db.commit()
            enviar_mensaje_telegram(chat_id, "❌ Ocurrió un error al ejecutar la acción.")
            return JSONResponse(content={"message": "Error al ejecutar acción"}, status_code=200)

    respuesta_json = analizar_modificacion_con_gpt(
        texto_usuario,
        accion_pendiente.accion,
        accion_pendiente.params_json or {}
    )

    nuevos_params = respuesta_json.get("params", {})
    actuales = deepcopy(accion_pendiente.params_json or {})
    actuales.update(nuevos_params)
    accion_pendiente.params_json = actuales
    db.commit()

    preview = json.dumps(actuales, indent=2, ensure_ascii=False)
    sugerencias = [v for k, v in POTENCIALES_CAMPOS.items() if k not in actuales]

    mensaje = (
        f"✏️ Parámetros actualizados:\n*{accion_pendiente.accion}*\n\n"
        f"📦 Detalles:\n```\n{preview}\n```\n"
    )
    if sugerencias:
        mensaje += "\n️Puedes agregar también:\n- " + "\n- ".join(sugerencias) + "\n"
    mensaje += "\n❓¿Deseas confirmar esta acción?\nResponde con /confirmar o /cancelar."

    enviar_mensaje_telegram(chat_id, mensaje)
    return JSONResponse(content={"message": "Esperando confirmación actualizada"}, status_code=200)


    
async def ejecutar_accion(resultado: dict):
    accion = resultado.get("accion")
    params = resultado.get("params", {})

    try:
        if accion == "registrar_venta":
            return registrar_venta(params)
        elif accion == "registrar_compra":
            return registrar_compra(params)
        elif accion == "registrar_gasto":
            return registrar_gasto(params)
        elif accion == "crear_cotizacion":
            return crear_cotizacion(params)
        elif accion == "registrar_evento":
            return registrar_evento(params)
        elif accion == "crear_producto":
            return ProductServices().agregar_inventario(params)
        elif accion == "crear_tarea":
            return crear_tarea(params)
        elif accion == "resumen_inventario":
            return resumen_inventario(params)
        elif accion == "otro":
            return "Acción no definida o sin ejecución."
        else:
            return f"Acción desconocida: {accion}"
    except Exception as e:
        print(f"Error ejecutando acción '{accion}':")
        traceback.print_exc()
        return f"Error en acción {accion}"
    
def registrar_venta(params: dict):
    producto = params.get("producto", "desconocido")
    cantidad = params.get("cantidad", 1)
    notas = params.get("notas", "")

    # Aquí podrías hacer inserts en tu DB, o cualquier lógica que necesites
    print(f"Registrando venta: {cantidad}x {producto} - {notas}")
    return f"Venta registrada: {cantidad}x {producto}"


