import logging
import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ContextTypes

import db
import collage as col

logger = logging.getLogger(__name__)

# Configuraciones globales
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
TZ_MADRID = pytz.timezone("Europe/Madrid")

# --- DECORADOR DE SEGURIDAD ---
def solo_yo(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
            logger.warning(f"Acceso denegado a user_id={user_id}")
            await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
            return
        return await func(update, context)
    return wrapper

# --- HANDLERS DE MENSAJES Y TEXTO ---

@solo_yo
async def guardar_peso_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        peso = float(texto.replace(",", "."))
        if not (30 < peso < 300):
            raise ValueError()
            
        db.guardar_peso(peso)
        pesos = db.pesos_semana_actual()
        media = sum(pesos) / len(pesos)
        
        # Obtenemos el día de la semana según el reloj de Madrid
        ahora = datetime.now(TZ_MADRID)
        es_domingo = ahora.weekday() == 6

        if es_domingo:
            fecha_hoy = ahora.strftime("%Y-%m-%d")
            db.guardar_historico(fecha_hoy, media)
            
            await update.message.reply_text(
                f"✅ *{peso} kg* guardado.\n\n"
                f"🏁 *¡CIERRE DE SEMANA AUTOMÁTICO!*\n"
                f"📊 Media final guardada: *{media:.2f} kg* ({len(pesos)} días).\n\n"
                f"📸 Ahora envíame las *3 fotos de progreso* seguidas (frente, perfil, espalda) para montar el collage.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"✅ *{peso} kg* guardado.\n"
                f"📊 Media provisional de la semana ({len(pesos)} registros): *{media:.2f} kg*",
                parse_mode="Markdown"
            )
    except ValueError:
        await update.message.reply_text("❌ Número no válido. Envía solo el peso (ej: `96.2`)", parse_mode="Markdown")


@solo_yo
async def recibir_foto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto_file = await update.message.photo[-1].get_file()
    foto_bytes = await foto_file.download_as_bytearray()
    
    # Guardamos en disco y comprobamos el estado de la cola
    ruta_guardada = col.guardar_foto(bytes(foto_bytes))
    num_fotos = col.fotos_recibidas()
    
    if num_fotos < 3:
        await update.message.reply_text(f"📸 Foto guardada ({num_fotos}/3). Mándame la siguiente.")
    else:
        await update.message.reply_text("⏳ ¡Tercera foto recibida! Procesando tu edit semanal...")
        pesos = db.pesos_semana_actual()
        
        # Si por casualidad procesas las fotos el lunes por retraso, pasamos un fallback de seguridad
        ruta_edit = col.generar_collage(pesos if pesos else [0.0])
        
        if ruta_edit and os.path.exists(ruta_edit):
            # Usamos 'with' para cerrar correctamente el descriptor del archivo y evitar fugas en el VPS
            with open(ruta_edit, "rb") as foto_archivo:
                await update.message.reply_photo(
                    photo=foto_archivo,
                    caption="🔥 *¡Tu progreso de la semana está listo!*\nLas fotos temporales han sido eliminadas del VPS.",
                    parse_mode="Markdown"
                )
            col.limpiar_fotos()
        else:
            await update.message.reply_text("❌ Error o faltan fotos temporales para generar el collage.")


# --- HANDLERS DE COMANDOS (/semana, /historico, etc.) ---

@solo_yo
async def comando_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesos = db.pesos_semana_actual()
    if not pesos:
        await update.message.reply_text("No hay registros esta semana.")
        return
    media = sum(pesos) / len(pesos)
    lista = "\n".join([f"  • {p} kg" for p in pesos])
    await update.message.reply_text(
        f"📋 *Pesos de esta semana:*\n{lista}\n\n📉 *Media provisional:* {media:.2f} kg",
        parse_mode="Markdown"
    )


@solo_yo
async def comando_historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    historico = db.obtener_historico(12)
    if not historico:
        await update.message.reply_text("El historial está vacío.")
        return
    
    lineas = []
    for r in reversed(historico):
        # Si la media es 0.0 significa que es una semana fantasma auto-rellenada
        if r['media_peso'] == 0.0:
            lineas.append(f"  • {r['fecha_cierre']}: ❌ *Sin registros*")
        else:
            lineas.append(f"  • {r['fecha_cierre']}: *{r['media_peso']} kg*")
            
    await update.message.reply_text(
        f"📉 *Histórico (últimas semanas):*\n" + "\n".join(lineas),
        parse_mode="Markdown"
    )


@solo_yo
async def comando_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eliminado = db.borrar_ultimo_peso()
    if eliminado:
        await update.message.reply_text(f"🗑️ Último peso registrado ({eliminado} kg) eliminado.")
    else:
        await update.message.reply_text("No hay pesos que borrar.")


@solo_yo
async def comando_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(db.DB_FILE):
        # Evitamos fugas de descriptores de archivo cerrando el flujo con 'with'
        with open(db.DB_FILE, "rb") as f_db:
            await update.message.reply_document(document=f_db, filename=db.DB_FILE, caption="💾 Copia de seguridad.")
    else:
        await update.message.reply_text("No se encuentra el archivo de base de datos.")


@solo_yo
async def comando_resetfotos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    col.limpiar_fotos()
    await update.message.reply_text("🗑️ Contenedor de fotos temporales vaciado.")


@solo_yo
async def comando_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Comandos disponibles:*\n\n"
        "📝 *Registro diario*\n"
        "  Envía un número (ej: `96.2`) para guardar tu peso del día\n\n"
        "📋 /semana — Ver pesos de la semana en curso\n"
        "🗑️ /borrar — Elimina el último peso registrado\n"
        "📉 /historico — Medias de las últimas 12 semanas (auto-rellenable)\n"
        "💾 /backup — Recibe el archivo dieta.db\n"
        "🗑️ /resetfotos — Limpia la cola de fotos temporales\n"
        "🏓 /ping — Comprueba el sistema de envio de mensajes\n"
    )

@solo_yo
async def comando_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="🏓 Pong! El bot puede enviarte mensajes."
    )

# --- TAREAS DE CONTEXTO / CRON ---

async def recordatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    hoy = date.today().strftime("%Y-%m-%d")
    with db.get_conn() as conn:
        ya_pesado = conn.execute(
            "SELECT 1 FROM pesos WHERE fecha = ?", (hoy,)
        ).fetchone()
    if not ya_pesado:
        await context.bot.send_message(
            chat_id=context.job.chat_id,  # <- leerlo del contexto
            text="⏰ ¡Recuerda pesarte hoy! Envíame el número cuando puedas."
        )

async def test_contexto(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,  # <- leerlo del contexto
        text="⏰ Contexto funciona."
    )