import mysql.connector
from mysql.connector import Error

def obtener_conexion():
    try:
        conexion = mysql.connector.connect(
            host='buap2lwlapikiigfik04-mysql.services.clever-cloud.com',
            user='ux2mxably9txzwyp',
            password='p2Cko9FhMUCkliGrBXF2',
            database='buap2lwlapikiigfik04',
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
