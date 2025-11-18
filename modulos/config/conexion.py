# modulos/config/conexion.py
import contextlib
import mysql.connector
from mysql.connector import pooling
import streamlit as st

# -------------------------------------------------------------------
#  Configuración del pool de conexiones
# -------------------------------------------------------------------
# Ajusta estos valores a como ya los tenías antes (st.secrets o datos fijos)
MYSQL_CONFIG = {
    "host": st.secrets["mysql"]["host"],
    "port": st.secrets["mysql"].get("port", 3306),
    "user": st.secrets["mysql"]["user"],
    "password": st.secrets["mysql"]["password"],
    "database": st.secrets["mysql"]["database"],
}

POOL = pooling.MySQLConnectionPool(
    pool_name="sgi_gapc_pool",
    pool_size=5,
    pool_reset_session=True,
    **MYSQL_CONFIG,
)

# -------------------------------------------------------------------
#  Helper de conexión (context manager)
# -------------------------------------------------------------------
@contextlib.contextmanager
def db_conn():
    cnx = None
    try:
        cnx = POOL.get_connection()
        yield cnx
    finally:
        if cnx is not None and cnx.is_connected():
            cnx.close()


# -------------------------------------------------------------------
#  Helpers de consulta
# -------------------------------------------------------------------
def execute(sql: str, params=None, return_last_id: bool = False):
    """
    Ejecuta un INSERT/UPDATE/DELETE.
    Si return_last_id=True, devuelve el lastrowid del cursor.
    """
    if params is None:
        params = ()

    with db_conn() as cnx:
        cur = cnx.cursor()
        cur.execute(sql, params)
        cnx.commit()
        if return_last_id:
            return cur.lastrowid
        return None


def fetch_one(sql: str, params=None):
    """Devuelve UNA fila como dict o None."""
    if params is None:
        params = ()

    with db_conn() as cnx:
        cur = cnx.cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        return row


def fetch_all(sql: str, params=None):
    """Devuelve TODAS las filas como lista de dicts."""
    if params is None:
        params = ()

    with db_conn() as cnx:
        cur = cnx.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        return rows
