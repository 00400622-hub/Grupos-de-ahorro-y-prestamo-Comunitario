import streamlit as st
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from contextlib import contextmanager

# Credenciales Clever Cloud
HOST = "bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com"
USER = "uvkxd9piyuwt9e3d"
PASSWORD = "NVcd1m955q5Qrzei5rFt"
DATABASE = "bddu6yel2ww6hx27qwg0"
PORT = 3306

@st.cache_resource
def _get_pool() -> MySQLConnectionPool:
    # pool_size <= 4 para no reventar el límite de 5
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
    # queda por compatibilidad — pero usa db_conn() abajo
    return _get_pool().get_connection()

@contextmanager
def db_conn():
    """Uso recomendado: with db_conn() as con: ...  (siempre cierra la conexión)"""
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
