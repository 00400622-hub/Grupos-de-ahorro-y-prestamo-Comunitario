# modulos/auth/login.py
import streamlit as st
import bcrypt
from modulos.config.conexion import fetch_one
from modulos.auth.rbac import set_user


def _check_password(plain: str, hashed_or_plain_from_db: str) -> bool:
    """Soporta contraseña en texto plano o bcrypt."""
    if not hashed_or_plain_from_db:
        return False
    try:
        # Si el valor de BD parece bcrypt
        if hashed_or_plain_from_db.startswith("$2b$") or hashed_or_plain_from_db.startswith("$2a$"):
            stored = hashed_or_plain_from_db.encode("utf-8")
            return bcrypt.checkpw(plain.encode("utf-8"), stored)
        # Caso contrario, texto plano
        return plain == hashed_or_plain_from_db
    except Exception:
        return False


def login_screen():
    st.title("SGI GAPC — Iniciar sesión")

    dui_in = st.text_input("DUI")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        if not dui_in or not password:
            st.warning("Ingrese DUI y contraseña.")
            return

        sql = """
            SELECT u.Id_usuario, u.Nombre, u.DUI, u.Contraseña, u.Id_rol,
                   r.`Tipo de rol` AS RolNombre
            FROM Usuario u
            JOIN rol r ON r.Id_rol = u.Id_rol
            WHERE u.DUI = %s
            LIMIT 1
        """
        user = fetch_one(sql, (dui_in,))
        if not user:
            st.error("Usuario no encontrado.")
            return

        if not _check_password(password, user["Contraseña"] or ""):
            st.error("Credenciales inválidas.")
            return

        # Guardamos lo que necesitamos en sesión
        set_user({
            "Id_usuario": user["Id_usuario"],
            "Nombre": user["Nombre"],
            "DUI": user["DUI"],
            "id_rol": user["Id_rol"],
            "Rol": (user["RolNombre"] or "").upper().strip(),  # ADMINISTRADOR / PROMOTORA / DIRECTIVA
        })

        st.success("Ingreso exitoso.")
        st.rerun()
