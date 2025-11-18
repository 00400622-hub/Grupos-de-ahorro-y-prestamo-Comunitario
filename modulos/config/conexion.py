# modulos/config/conexion.py
import mysql.connector
from contextlib import contextmanager
import streamlit as st


def _get_mysql_params():
    """
    Obtiene los parámetros de conexión a MySQL.

    1) Primero intenta leerlos de st.secrets["mysql"].
    2) Si no existe esa clave, usa un 'fallback' de desarrollo
       que tú puedes rellenar con tus datos LOCALES (solo para pruebas).
    """

    # --- 1) Intentar leer desde st.secrets ---
    if "mysql" in st.secrets:
        cfg = st.secrets["mysql"]
        return {
            "host": cfg.get("host"),
            "user": cfg.get("user"),
            "password": cfg.get("password"),
            "database": cfg.get("database"),
            "port": int(cfg.get("port", 3306)),
        }

    # --- 2) Fallback de desarrollo (solo para cuando NO hay st.secrets) ---
    # ⚠️ IMPORTANTE:
    # Rellena estos valores en tu entorno local si quieres,
    # pero NO subas jamás este archivo con credenciales reales a GitHub.
    return {
        "host": "TU_HOST_AQUI",        # p.ej. "xxxx-mysql.services.clever-cloud.com"
        "user": "TU_USUARIO_AQUI",
        "password": "TU_PASSWORD_AQUI",
        "database": "TU_DATABASE_AQUI",
        "port": 3306,
    }


@contextmanager
def db_conn():
    """Context manager que abre y cierra la conexión."""
    params = _get_mysql_params()
    cnx = mysql.connector.connect(**params)
    try:
        yield cnx
    finally:
        cnx.close()


def fetch_one(sql: str, params=None):
    """Ejecuta un SELECT y devuelve una sola fila como diccionario (o None)."""
    with db_conn() as cnx:
        cur = cnx.cursor(dictionary=True)
        cur.execute(sql, params or ())
        row = cur.fetchone()
        cur.close()
        return row


def fetch_all(sql: str, params=None):
    """Ejecuta un SELECT y devuelve todas las filas como lista de diccionarios."""
    with db_conn() as cnx:
        cur = cnx.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows


def execute(sql: str, params=None, return_last_id: bool = False):
    """
    Ejecuta un INSERT / UPDATE / DELETE.
    Si return_last_id=True, devuelve el último Id autoincremental.
    """
    with db_conn() as cnx:
        cur = cnx.cursor()
        cur.execute(sql, params or ())
        last_id = cur.lastrowid
        cnx.commit()
        cur.close()
        if return_last_id:
            return last_id
