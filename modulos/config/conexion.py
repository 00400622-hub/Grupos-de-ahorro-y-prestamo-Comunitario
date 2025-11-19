# modulos/config/conexion.py
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

# -------------------------------------------------------------------
# CONFIGURACIÓN REAL DE TU BD EN CLEVER CLOUD
# -------------------------------------------------------------------
DB_CONFIG = {
    "host":     "bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com",
    "user":     "uvkxd9piyuwt9e3d",
    "password": "NVcd1m955q5Qrzei5rFt",
    "database": "bddu6yel2ww6hx27qwg0",
    "port":     3306,
}


def _get_params():
    """Devuelve los parámetros correctos para mysql.connector."""
    params = DB_CONFIG.copy()
    params["port"] = int(params.get("port", 3306))
    return params


# -------------------------------------------------------------------
# CONTEXT MANAGER PARA CONEXIÓN
# -------------------------------------------------------------------
@contextmanager
def db_conn():
    """Abre y cierra la conexión automáticamente."""
    params = _get_params()
    cnx = None

    try:
        cnx = mysql.connector.connect(**params)
        yield cnx

    finally:
        if cnx and cnx.is_connected():
            cnx.close()


# -------------------------------------------------------------------
# SELECT: fetch_one
# -------------------------------------------------------------------
def fetch_one(sql: str, params: tuple | None = None):
    """Ejecuta SELECT y devuelve 1 fila como dict."""
    try:
        with db_conn() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(sql, params or ())
            row = cur.fetchone()
            cur.close()
            return row

    except Error as err:
        raise


# -------------------------------------------------------------------
# SELECT: fetch_all
# -------------------------------------------------------------------
def fetch_all(sql: str, params: tuple | None = None):
    """Ejecuta SELECT y devuelve lista de dicts."""
    try:
        with db_conn() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            cur.close()
            return rows

    except Error as err:
        raise


# -------------------------------------------------------------------
# INSERT/UPDATE/DELETE: execute
# -------------------------------------------------------------------
def execute(sql: str, params: tuple | None = None, return_last_id: bool = False):
    """
    Ejecuta INSERT/UPDATE/DELETE.
    Si return_last_id=True, devuelve el último ID insertado.
    """
    try:
        with db_conn() as cnx:
            cur = cnx.cursor()
            cur.execute(sql, params or ())
            last_id = cur.lastrowid
            cnx.commit()
            cur.close()

            if return_last_id:
                return last_id

    except Error as err:
        raise
