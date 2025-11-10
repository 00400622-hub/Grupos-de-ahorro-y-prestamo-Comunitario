import mysql.connector
import streamlit as st

# Datos de conexión a Clever Cloud
HOST = "bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com"
USER = "uvkxd9piyuwt9e3d"
PASSWORD = "NVcd1m955q5Qrzei5rFt"
DATABASE = "bddu6yel2ww6hx27qwg0"
PORT = 3306

def obtener_conexion():
    try:
        con = mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            port=PORT,
            autocommit=False
        )
        return con
    except mysql.connector.Error as e:
        st.error(f"❌ Error de conexión a la base de datos: {e}")
        st.stop()
