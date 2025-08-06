from copy import deepcopy
import json
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from app.telegram_bot.utils import (
    analizar_modificacion_con_gpt,
    enviar_mensaje_telegram,
    es_usuario_autorizado,
    descargar_audio_telegram,
    transcribir_audio_con_whisper,
    analizar_comando_con_gpt
)
from app.db import SessionLocal
from app.telegram_bot.models import AccionPendiente, EstadoAccion, TelegramTranscripcion
from app.productos.service import ProductServices
import traceback

async def manejar_mensaje_telegram(message: dict):
    try:
        db = SessionLocal()
        message_id = message["message_id"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]

        if not es_usuario_autorizado(user_id):
            return JSONResponse(content={"message": "Usuario no autorizado"}, status_code=200)

        # Revisar si ya fue procesado
        existente = db.query(TelegramTranscripcion).filter_by(message_id=message_id).first()
        if existente:
            return JSONResponse(content={"message": "Ya procesado", "texto": existente.texto}, status_code=200)

        # Revisar si hay acción pendiente sin confirmar y no expirada
        un_minuto_atras = datetime.utcnow() - timedelta(minutes=1)
        accion_pendiente = (
            db.query(AccionPendiente)
            .filter(
                AccionPendiente.user_id == str(user_id),
                AccionPendiente.estado == EstadoAccion.pendiente_confirmacion,
                AccionPendiente.fecha_creacion >= un_minuto_atras
            )
            .order_by(AccionPendiente.fecha_creacion.desc())
            .first()
        )

        if accion_pendiente:
            # Procesar mensaje (voz o texto)
            texto = ""
            if "text" in message:
                texto = message["text"]
            elif "voice" in message:
                file_id = message["voice"]["file_id"]
                ruta_audio = descargar_audio_telegram(file_id)
                texto = transcribir_audio_con_whisper(ruta_audio)
            else:
                texto = "(no compatible)"
            texto_usuario = texto.strip().lower()

            if texto_usuario == "/cancelar":
                accion_pendiente.estado = EstadoAccion.cancelada
                db.commit()
                enviar_mensaje_telegram(chat_id, "❌ Acción cancelada.")
                return JSONResponse(content={"message": "Acción cancelada"}, status_code=200)

            elif texto_usuario == "/confirmar":
                if not accion_pendiente or (accion_pendiente.fecha_creacion < datetime.utcnow() - timedelta(minutes=1)):
                    return JSONResponse(content={"message": "⚠️ La acción pendiente expiró. Por favor repite el comando."}, status_code=200)

                resultado = {
                    "accion": accion_pendiente.accion,
                    "params": accion_pendiente.params_json
                }

                try:
                    if accion_pendiente.accion == "agregar_inventario":
                        respuesta_accion = ProductServices().agregar_inventario(accion_pendiente.params_json)
                    elif accion_pendiente.accion == "crear_producto":
                        respuesta_accion = ProductServices().agregar_inventario(accion_pendiente.params_json)
                    # Aquí puedes añadir más acciones válidas...
                    else:
                        raise ValueError(f"Acción no soportada: {accion_pendiente.accion}")

                    accion_pendiente.estado = EstadoAccion.confirmada
                    db.commit()
                    accion_pendiente.estado = EstadoAccion.ejecutada
                    db.commit()

                    enviar_mensaje_telegram(chat_id, f"✅ Acción ejecutada:\n{respuesta_accion}")
                    return JSONResponse(content={"message": "Acción confirmada y ejecutada"}, status_code=200)

                except Exception as e:
                    traceback.print_exc()
                    print("❌ Error al ejecutar la acción confirmada:", e)
                    accion_pendiente.estado = EstadoAccion.error
                    db.commit()
                    enviar_mensaje_telegram(chat_id, "❌ Ocurrió un error al ejecutar la acción.")
                    return JSONResponse(content={"message": "Error al ejecutar acción"}, status_code=200)

            else:
                respuesta_json = analizar_modificacion_con_gpt(
                    texto_usuario,
                    accion_pendiente.accion,
                    accion_pendiente.params_json or {}
                )
                print("xxx respuesta_json",respuesta_json)

                nuevos_params = respuesta_json.get("params", {})
                print("🆕 Nuevos parámetros detectados:", nuevos_params)

                params_actuales = deepcopy(accion_pendiente.params_json or {})
                print("📦 Parámetros actuales antes de merge:", params_actuales)
                for key, value in (nuevos_params or {}).items():
                    params_actuales[key] = value
                    print(f"🔁 Campo actualizado/agregado: {key} = {value}")

                accion_pendiente.params_json = params_actuales
                db.commit()

                preview = json.dumps(params_actuales, indent=2, ensure_ascii=False)
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
                campos_faltantes = [c for c in POTENCIALES_CAMPOS if c not in params_actuales]
                sugerencias = [POTENCIALES_CAMPOS[c] for c in campos_faltantes]

                mensaje_confirmacion = (
                    "✏️ Parámetros actualizados:\n"
                    f"*{accion_pendiente.accion}*\n\n"
                    f"📦 Detalles:\n```\n{preview}\n```\n"
                )
                if sugerencias:
                    mensaje_confirmacion += (
                        "\nℹ️ Puedes agregar también:\n"
                        "- " + "\n- ".join(sugerencias) + "\n"
                    )
                mensaje_confirmacion += "\n¿Deseas confirmar esta acción?\nResponde con /confirmar o /cancelar."

                enviar_mensaje_telegram(chat_id, mensaje_confirmacion)
                return JSONResponse(content={"message": "Esperando confirmación actualizada"}, status_code=200)

        # Procesar mensaje (voz o texto)
        if "text" in message:
            texto = message["text"]
        elif "voice" in message:
            file_id = message["voice"]["file_id"]
            ruta_audio = descargar_audio_telegram(file_id)
            texto = transcribir_audio_con_whisper(ruta_audio)
        else:
            texto = "(no compatible)"

        # Guardar transcripción
        nuevo = TelegramTranscripcion(message_id=message_id, texto=texto, procesado=True)
        db.add(nuevo)
        db.commit()

        # Llamar a GPT
        respuesta_json = analizar_comando_con_gpt(texto)
        resultado = json.loads(respuesta_json)

        # Guardar como acción pendiente
        pendiente = AccionPendiente(
            user_id=str(user_id),
            accion=resultado.get("accion"),
            params_json=resultado.get("params"),
            mensaje_original=texto,
            estado=EstadoAccion.pendiente_confirmacion
        )
        db.add(pendiente)
        db.commit()

        # Preparar mensaje de confirmación
        params_recibidos = resultado.get("params", {})
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
        # Detectar campos faltantes
        campos_faltantes = [
            nombre for nombre, descripcion in POTENCIALES_CAMPOS.items()
            if nombre not in params_recibidos
        ]

        # Mensaje base
        preview = json.dumps(params_recibidos, indent=2, ensure_ascii=False)

        mensaje_confirmacion = (
            "📝 Acción detectada:\n"
            f"*{resultado.get('accion')}*\n\n"
            f"📦 Detalles:\n```\n{preview}\n```\n"
        )

        # Agregar sugerencia si hay campos faltantes
        if campos_faltantes:
            sugerencias = [POTENCIALES_CAMPOS[c] for c in campos_faltantes]
            mensaje_confirmacion += (
                "\nℹ️ Puedes agregar también:\n"
                "- " + "\n- ".join(sugerencias) + "\n"
            )

        mensaje_confirmacion += "\n¿Deseas confirmar esta acción?\nResponde con /confirmar o /cancelar."

        enviar_mensaje_telegram(chat_id, mensaje_confirmacion)

        return JSONResponse(content={"accion": resultado.get("accion")}, status_code=200)

    except Exception as e:
        print("Error procesando mensaje Telegram:")
        traceback.print_exc()
        return JSONResponse(content={"message": "Error interno, pero se responde 200 para evitar reintentos"}, status_code=200)
    
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


