import streamlit as st
from modulos.auth.rbac import require_auth, has_role, current_user
from modulos.config.conexion import fetch_one

def _validar_rol_directiva():
    require_auth()
    if not has_role("DIRECTIVA"):
        st.error("Acceso restringido a Directiva.")
        st.stop()

def directiva_panel():
    _validar_rol_directiva()
    u = current_user()
    id_grupo = u.get("id_grupo")

    st.markdown("## Panel Directiva")
    if not id_grupo:
        st.error("No hay grupo asignado a esta cuenta de Directiva.")
        return

    grupo = fetch_one("SELECT id_grupo, Nombre, id_distrito FROM grupos WHERE id_grupo=%s", (id_grupo,))
    if grupo:
        st.write(f"**Grupo:** {grupo['Nombre']} (id {grupo['id_grupo']}) — **Distrito:** {grupo['id_distrito']}")
    else:
        st.error("No se encontró el grupo asignado.")

    st.info("Aquí agregaremos: registro de reuniones, asistencia, ahorros, préstamos, pagos, multas y caja.\nPor ahora, panel base funcionando con alcance restringido al grupo.")
