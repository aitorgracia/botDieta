import sqlite3
import logging
from datetime import datetime, timedelta
import pytz

DB_FILE = "dieta.db"
logger = logging.getLogger(__name__)

# Definimos la zona horaria de Madrid de forma global
TZ_MADRID = pytz.timezone("Europe/Madrid")

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea las tablas si no existen adaptadas al sistema de semanas ISO."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pesos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT NOT NULL,
                semana    INTEGER NOT NULL,
                anio      INTEGER NOT NULL,
                peso      REAL NOT NULL,
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS historico (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_cierre TEXT NOT NULL,
                media_peso   REAL NOT NULL
            );
        """)
    logger.info("Base de datos inicializada correctamente.")


# --- CAPA DE PESOS DIARIOS ---

def guardar_peso(peso: float):
    # Cogemos la hora exacta actual en Madrid
    ahora = datetime.now(TZ_MADRID)
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    anio_actual, semana_actual, _ = ahora.isocalendar()
    
    # 1. Procesar cierres antiguos y rellenar huecos vacíos
    cerrar_semanas_pendientes(anio_actual, semana_actual)
    
    # 2. Guardar el peso en la semana actual
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pesos (fecha, semana, anio, peso) VALUES (?, ?, ?, ?)",
            (fecha_hoy, semana_actual, anio_actual, peso)
        )
    logger.info(f"Peso guardado: {peso} kg — Semana {semana_actual} ({fecha_hoy} Madrid)")


def cerrar_semanas_pendientes(anio_actual: int, semana_actual: int):
    """Bucle que recorre el calendario y cierra de forma limpia el pasado pendiente."""
    with get_conn() as conn:
        primer_registro = conn.execute("""
            SELECT anio, semana FROM pesos 
            ORDER BY anio ASC, semana ASC LIMIT 1
        """).fetchone()
        
        ultimo_historico = conn.execute("""
            SELECT fecha_cierre FROM historico 
            ORDER BY id DESC LIMIT 1
        """).fetchone()

    if not primer_registro and not ultimo_historico:
        return

    if ultimo_historico:
        fecha_u = datetime.strptime(ultimo_historico["fecha_cierre"], "%Y-%m-%d")
        fecha_inicio = fecha_u + timedelta(days=7)
        anio_p, semana_p, _ = fecha_inicio.isocalendar()
    else:
        anio_p = primer_registro["anio"]
        semana_p = primer_registro["semana"]

    while anio_p < anio_actual or (anio_p == anio_actual and semana_p < semana_actual):
        pesos_antiguos = pesos_por_semana(semana_p, anio_p)
        fecha_cierre_estimada = datetime.fromisocalendar(anio_p, semana_p, 7).strftime("%Y-%m-%d")
        
        if pesos_antiguos:
            media = sum(pesos_antiguos) / len(pesos_antiguos)
            guardar_historico_automatico(fecha_cierre_estimada, media)
            with get_conn() as conn:
                conn.execute("DELETE FROM pesos WHERE semana = ? AND anio = ?", (semana_p, anio_p))
            logger.info(f"Archivada semana vieja automáticamente: Semana {semana_p}-{anio_p} -> Media: {media:.2f} kg")
        else:
            guardar_historico_automatico(fecha_cierre_estimada, 0.0)
            logger.info(f"Rellenado hueco vacío: Semana {semana_p}-{anio_p} -> Registrado con 0.0 kg")
        
        fecha_siguiente = datetime.fromisocalendar(anio_p, semana_p, 7) + timedelta(days=7)
        anio_p, semana_p, _ = fecha_siguiente.isocalendar()


def pesos_semana_actual() -> list[float]:
    """Devuelve todos los pesos registrados en la semana ISO en curso."""
    anio, semana, _ = datetime.now(TZ_MADRID).isocalendar()
    return pesos_por_semana(semana, anio)


def pesos_por_semana(semana: int, anio: int) -> list[float]:
    """Recupera los pesos de cualquier combinación de semana/año específica."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT peso FROM pesos 
            WHERE semana = ? AND anio = ? 
            ORDER BY id ASC
        """, (semana, anio)).fetchall()
    return [r["peso"] for r in rows]


def borrar_ultimo_peso() -> float | None:
    """Elimina el último registro de peso de la tabla pesos."""
    with get_conn() as conn:
        row = conn.execute("SELECT id, peso FROM pesos ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM pesos WHERE id = ?", (row["id"],))
    return row["peso"]


# --- CAPA HISTÓRICA ---

def guardar_historico(fecha_cierre: str, media: float):
    """Interfaz estándar usada desde handlers.py para el cierre manual del domingo."""
    guardar_historico_automatico(fecha_cierre, media)


def guardar_historico_automatico(fecha_cierre: str, media: float):
    """Inserta registros en el histórico controlando duplicados y manteniendo el límite de 52 filas."""
    with get_conn() as conn:
        # Evitamos re-procesar si ya existe el cierre exacto para ese domingo
        existe = conn.execute("SELECT 1 FROM historico WHERE fecha_cierre = ?", (fecha_cierre,)).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO historico (fecha_cierre, media_peso) VALUES (?, ?)",
                (fecha_cierre, round(media, 2))
            )
            # Mantenemos limpia la base de datos limitándola a un año de histórico (52 semanas)
            conn.execute("""
                DELETE FROM historico WHERE id NOT IN (
                    SELECT id FROM historico ORDER BY id DESC LIMIT 52
                )
            """)
    logger.info(f"Histórico guardado: {media:.2f} kg — {fecha_cierre}")


def obtener_historico(semanas: int = 12) -> list[sqlite3.Row]:
    """Devuelve los cierres guardados para pintarlos en el comando /historico."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT fecha_cierre, media_peso FROM historico ORDER BY id DESC LIMIT ?",
            (semanas,)
        ).fetchall()