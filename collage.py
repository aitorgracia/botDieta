import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FOTOS_TEMP = ["frente.jpg", "perfil.jpg", "espalda.jpg"]
OUTPUT_PATH = "review_semanal.jpg"
FONT_PATH = "font.ttf"  # Pon aquí un .ttf si quieres fuente personalizada


def _cargar_fuente(size: int):
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            logger.warning("No se pudo cargar font.ttf, usando fuente por defecto.")
    return ImageFont.load_default()


def fotos_recibidas() -> int:
    """Devuelve cuántas fotos temporales hay ya guardadas."""
    return sum(1 for f in FOTOS_TEMP if os.path.exists(f))


def guardar_foto(data: bytes) -> str | None:
    """Guarda los bytes en la siguiente posición libre. Devuelve el nombre o None si ya hay 3."""
    for f in FOTOS_TEMP:
        if not os.path.exists(f):
            with open(f, "wb") as fh:
                fh.write(data)
            logger.info(f"Foto guardada como {f}")
            return f
    return None


def limpiar_fotos():
    for f in FOTOS_TEMP:
        if os.path.exists(f):
            os.remove(f)
    logger.info("Fotos temporales eliminadas.")


def generar_collage(pesos: list[float]) -> str | None:
    """
    Genera el collage con las 3 fotos y la media semanal.
    Devuelve la ruta del archivo generado, o None si falla.
    """
    if not all(os.path.exists(f) for f in FOTOS_TEMP):
        logger.warning("Faltan fotos para generar el collage.")
        return None

    media = sum(pesos) / len(pesos)
    media_texto = f"MEDIA SEMANAL: {media:.2f} kg"

    try:
        size = (400, 600)
        imagenes = [Image.open(f).resize(size) for f in FOTOS_TEMP]

        # Lienzo: 3 fotos en fila + banda inferior para el texto
        collage = Image.new("RGB", (1200, 680), color="#111111")
        for i, img in enumerate(imagenes):
            collage.paste(img, (i * 400, 0))

        draw = ImageDraw.Draw(collage)

        # Texto grande centrado en la banda inferior
        fuente_grande = _cargar_fuente(36)
        bbox = draw.textbbox((0, 0), media_texto, font=fuente_grande)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((1200 - text_w) // 2, 625),
            media_texto,
            fill="#FFFFFF",
            font=fuente_grande
        )

        collage.save(OUTPUT_PATH, quality=90)
        logger.info(f"Collage generado: {OUTPUT_PATH}")
        limpiar_fotos()
        return OUTPUT_PATH

    except Exception as e:
        logger.error(f"Error generando collage: {e}")
        return None
