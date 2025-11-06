import mysql.connector
from mysql.connector import Error

def obtener_conexion():
    try:
        conexion = mysql.connector.connect(
            host='bddu6yel2ww6hx27qwg0-mysql.services.clever-cloud.com',
            user='uvkxd9piyuwt9e3d',
            password='NVcd1m955q5Qrzei5rFt',
            database='bddu6yel2ww6hx27qwg0',
            port=3306
        )
        if conexion.is_connected():
            print("✅ Conexión establecida")
            return conexion
        else:
            print("❌ Conexión fallida (is_connected = False)")
            return None
    except mysql.connector.Error as e:
        print(f"❌ Error al conectar: {e}")
        return None
