import streamlit as st
from modulos.config.conexion import obtener_conexion

def panel_directiva():
    st.header("🏛 Panel de la Directiva — Mi Grupo")
    grupo_id = st.session_state["user"]["grupo_id"]

    if not grupo_id:
        st.error("❌ No hay grupo asignado a esta cuenta.")
        return

    with obtener_conexion() as con:
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT g.id, g.nombre, g.estado, d.nombre AS distrito
            FROM grupos g
            JOIN distritos d ON d.id = g.distrito_id
            WHERE g.id = %s
        """, (grupo_id,))
        grupo = cur.fetchone()

    if not grupo:
        st.error("Grupo no encontrado.")
        return

    st.markdown(f"""
    **Nombre del grupo:** {grupo['nombre']}  
    **Distrito:** {grupo['distrito']}  
    **Estado:** {grupo['estado']}
    """)

    st.info("Aquí podrás registrar reuniones, asistencias, multas, ahorros, préstamos y reportes del grupo.")

