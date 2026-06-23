import asyncio
import logging
import os
from datetime import time
from logging.handlers import TimedRotatingFileHandler
import pytz

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

import db
from handlers import (
    guardar_peso_handler,
    recibir_foto_handler,
    # Quitado comando_domingo de aquí
    comando_semana,
    comando_borrar,
    comando_historico,
    comando_backup,
    comando_resetfotos,
    recordatorio_diario,
    comando_help,
    comando_ping,
)

# --- LOGGING AUTOMÁTICO (Rotación diaria a medianoche) ---
handler_rotativo = TimedRotatingFileHandler(
    "bot.log",
    when="midnight",      # Rota exactamente a las 00:00
    interval=1,           # Cada 1 día
    backupCount=7,        # Guarda un histórico de 7 días, el resto se destruye solo
    encoding="utf-8"
)

# Configuramos el formato estándar limpio
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
handler_rotativo.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        handler_rotativo,
        logging.StreamHandler(),  # Mantiene la salida por consola
    ],
)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    allowed_id = int(os.getenv("ALLOWED_USER_ID", "0"))

    if not token:
        logger.critical("BOT_TOKEN no encontrado en .env — abortando.")
        raise SystemExit(1)

    # Inicializar base de datos
    db.init_db()

    # Limpiar posibles residuos de imágenes tras un reinicio del script
    import collage as col
    col.limpiar_fotos()

    app = Application.builder().token(token).build()

    # Comandos (Línea de /domingo eliminada de forma limpia)
    app.add_handler(CommandHandler("semana",     comando_semana))
    app.add_handler(CommandHandler("borrar",     comando_borrar))
    app.add_handler(CommandHandler("historico",  comando_historico))
    app.add_handler(CommandHandler("backup",     comando_backup))
    app.add_handler(CommandHandler("resetfotos", comando_resetfotos))
    app.add_handler(CommandHandler("help",       comando_help))
    app.add_handler(CommandHandler("ping",       comando_ping))

    # Fotos y texto
    app.add_handler(MessageHandler(filters.PHOTO, recibir_foto_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_peso_handler))

    # Recordatorio diario a las 07:05 de Madrid (solo si ALLOWED_USER_ID está configurado)
    if allowed_id:
        app.job_queue.run_daily(
            recordatorio_diario,
            time=time(hour=7, minute=5, tzinfo=pytz.timezone("Europe/Madrid")),
            name="recordatorio_diario",
            chat_id=allowed_id
        )
        logger.info(f"Recordatorio diario activado para user_id={allowed_id}")

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()