import streamlit as st, bcrypt
from modulos.config.conexion import obtener_conexion
from modulos.auth.rbac import set_user_session

def _row_to_dict(cursor, row): 
    return {d[0]: v for d, v in zip(cursor.description, row)}

def _normalizar_dui(txt: str) -> str:
    # deja solo dígitos (acepta con o sin guion) y valida 9 dígitos
    digits = "".join(ch for ch in (txt or "") if ch.isdigit())
    return digits  # "#########" (9 dígitos)

def login_screen():
    st.title("SGI GAPC — Iniciar sesión")
    dui_in = st.text_input("DUI (sin guion)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        dui = _normalizar_dui(dui_in)
        if len(dui) != 9:
            st.warning("Ingresa un DUI válido (9 dígitos).")
            return
        if not password:
            st.warning("Ingresa la contraseña.")
            return

        con = obtener_conexion(); cur = con.cursor()
        try:
            cur.execute("""
                SELECT id, nombre, dui, hash_password, rol, distrito_id, grupo_id, activo
                FROM usuarios
                WHERE REPLACE(dui, '-', '') = %s
            """, (dui,))
            row = cur.fetchone()
            if not row:
                st.error("Usuario no encontrado.")
                return

            data = _row_to_dict(cur, row)
            if not data["activo"]:
                st.error("Usuario inactivo.")
                return

            if not bcrypt.checkpw(password.encode(), data["hash_password"].encode()):
                st.error("Contraseña incorrecta.")
                return

            # Cargar permisos por rol
            cur.execute("""
                SELECT p.clave
                FROM rol_permiso rp
                JOIN permisos p ON p.id = rp.permiso_id
                WHERE rp.rol = %s
            """, (data["rol"],))
            permisos = {r[0] for r in cur.fetchall()}

            set_user_session(data, permisos)
            st.success(f"Bienvenido, {data['nombre']}")

        finally:
            cur.close(); con.close()
