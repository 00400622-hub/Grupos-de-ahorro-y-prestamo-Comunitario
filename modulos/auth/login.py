import streamlit as st
from modulos.config.conexion import db_conn

def _normalizar_dui(txt: str) -> str:
    """Quita guiones y deja solo dígitos."""
    return "".join(ch for ch in (txt or "") if ch.isdigit())

def login_screen():
    st.title("SGI GAPC — Iniciar sesión")
    dui_in = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        dui = _normalizar_dui(dui_in)
        if len(dui) != 9:
            st.error("❌ DUI inválido. Debe tener 9 dígitos.")
            return

        # ---- CONSULTAR USUARIO ----
        try:
            with db_conn() as con:
                cur = con.cursor(dictionary=True)
                try:
                    cur.execute("""
                        SELECT Id_usuarios AS id, Nombre AS nombre, DUI AS dui,
                               Contraseña AS contraseña, Rol AS rol,
                               Id_distrito AS distrito_id, Id-grupo AS grupo_id, Activo AS activo
                        FROM usuarios
                        WHERE REPLACE(DUI, '-', '') = %s
                    """, (dui,))
                    data = cur.fetchone()
                finally:
                    cur.close()

            if not data:
                st.error("❌ Usuario no encontrado.")
                return

            if password.strip() != data["contraseña"]:
                st.error("❌ Contraseña incorrecta.")
                return

            # ---- GUARDAR SESIÓN ----
            st.session_state["user"] = {
                "id": data["id"],
                "nombre": data["nombre"],
                "dui": data["dui"],
                "rol": data["rol"],
                "distrito_id": data.get("distrito_id"),
                "grupo_id": data.get("grupo_id"),
            }
            st.session_state["autenticado"] = True
            st.success(f"Bienvenido, {data['rol']} {data['nombre']}.")

        except Exception as e:
            st.error("Error al consultar la base de datos.")
            st.caption(f"Detalle: {e}")
