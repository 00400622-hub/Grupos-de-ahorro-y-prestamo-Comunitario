import streamlit as st
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from contextlib import contextmanager

# ===============================
# 🔐 Credenciales Clever Cloud
# ===============================
HOST = "bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com"
USER = "uvkxd9piyuwt9e3d"
PASSWORD = "NVcd1m955q5Qrzei5rFt"
DATABASE = "bddu6yel2ww6hx27qwg0"
PORT = 3306

# ===============================
# ⚙️ Pool de conexiones
# ===============================
@st.cache_resource
def _get_pool() -> MySQLConnectionPool:
    """
    Se crea una única vez y se reutiliza entre sesiones.
    pool_size <= 4 para no exceder el límite gratuito de Clever Cloud.
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
    """Compatibilidad con código existente."""
    return _get_pool().get_connection()

@contextmanager
def db_conn():
    """Uso recomendado: with db_conn() as con: ... (garantiza cierre de conexión)."""
    con = None
    try:
        con = _get_pool().get_connection()
        yield con
    finally:
        try:
            if con and con.is_connected():
                con.close()
        except Exception:
            pass

# ===============================
# 🔧 Helpers para consultas
# ===============================
def fetch_one(query, params=None):
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(query, params or ())
        row = cur.fetchone()
        cur.close()
        return row

def fetch_all(query, params=None):
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows

def execute(query, params=None):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(query, params or ())
        con.commit()
        last_id = cur.lastrowid
        affected = cur.rowcount
        cur.close()
        return affected, last_id
