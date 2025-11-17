import streamlit as st
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector import InterfaceError, Error
from contextlib import contextmanager

# Credenciales Clever Cloud
HOST = "bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com"
USER = "uvkxd9piyuwt9e3d"
PASSWORD = "NVcd1m955q5Qrzei5rFt"
DATABASE = "bddu6yel2ww6hx27qwg0"
PORT = 3306


@st.cache_resource
def _get_pool() -> MySQLConnectionPool:
    """
    Crea un pool de conexiones (máx 4) para no reventar el límite de Clever Cloud.
    Si luego borramos este cache con _get_pool.clear(), se recrea.
    """
    return MySQLConnectionPool(
        pool_name="sgi_gapc_pool",
        pool_size=4,
        pool_reset_session=True,
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        port=PORT,
        autocommit=False,
    )


def obtener_conexion():
    """Compatibilidad con código viejo: devuelve una conexión del pool."""
    return _get_pool().get_connection()


@contextmanager
def db_conn():
    """
    Uso recomendado:
        with db_conn() as con:
            ...

    Siempre devuelve una conexión válida del pool. Si el pool está corrupto,
    lo recrea automáticamente.
    """
    con = None
    try:
        try:
            # Intentamos obtener una conexión del pool
            con = _get_pool().get_connection()
        except InterfaceError:
            # Si falla (por ejemplo, conexiones muertas), recreamos el pool
            _get_pool.clear()
            con = _get_pool().get_connection()

        yield con

    finally:
        # Devolvemos la conexión al pool de forma segura
        try:
            if con and con.is_connected():
                con.close()
        except Exception:
            pass


# ----------------- helpers para consultas ----------------- #

def fetch_one(sql: str, params=None):
    """
    Ejecuta un SELECT y devuelve solo un registro (dict) o None.
    """
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params or ())
        row = cur.fetchone()
        cur.close()
        return row


def fetch_all(sql: str, params=None):
    """
    Ejecuta un SELECT y devuelve una lista de registros (list[dict]).
    """
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows


def execute(sql: str, params=None):
    """
    Ejecuta un INSERT/UPDATE/DELETE.
    Devuelve (rowcount, last_id).
    """
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(sql, params or ())
        con.commit()
        rowcount = cur.rowcount
        last_id = cur.lastrowid
        cur.close()
        return rowcount, last_id
