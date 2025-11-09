import streamlit as st, bcrypt
from modulos.config.conexion import obtener_conexion
from modulos.auth.rbac import set_user_session

def _row_to_dict(cursor, row): return {d[0]: v for d, v in zip(cursor.description, row)}

def login_screen():
    st.title("SGI GAPC — Iniciar sesión")
    email = st.text_input("Email")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        con = obtener_conexion(); cur = con.cursor()
        try:
            cur.execute("""SELECT id,nombre,email,hash_password,rol,distrito_id,grupo_id,activo
                           FROM usuarios WHERE email=%s""", (email,))
            row = cur.fetchone()
            if not row:
                st.error("Usuario no encontrado."); return
            data = _row_to_dict(cur, row)
            if not data["activo"]: st.error("Usuario inactivo."); return
            if not bcrypt.checkpw(password.encode(), data["hash_password"].encode()):
                st.error("Contraseña incorrecta."); return
            cur.execute("""SELECT p.clave FROM rol_permiso rp
                           JOIN permisos p ON p.id=rp.permiso_id WHERE rp.rol=%s""",
                        (data["rol"],))
            permisos = {r[0] for r in cur.fetchall()}
            set_user_session(data, permisos)
            st.success(f"Bienvenido, {data['nombre']}")
        finally:
            cur.close(); con.close()
