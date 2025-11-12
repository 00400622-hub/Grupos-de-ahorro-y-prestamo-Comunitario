import streamlit as st
import bcrypt
from modulos.config.conexion import fetch_one
from modulos.auth.rbac import set_user

def _check_password(plain: str, hashed_or_plain_from_db: str) -> bool:
    """Soporta contraseña hasheada (bcrypt) y plano (compatibilidad)."""
    if not hashed_or_plain_from_db:
        return False
    stored = hashed_or_plain_from_db.encode("utf-8")
    try:
        # Si ya es hash bcrypt
        if hashed_or_plain_from_db.startswith("$2b$") or hashed_or_plain_from_db.startswith("$2a$"):
            return bcrypt.checkpw(plain.encode("utf-8"), stored)
        # Si está en texto plano (migración)
        return plain == hashed_or_plain_from_db
    except Exception:
        return False

def login_screen():
    st.title("SGI GAPC — Iniciar sesión")

    dui_in = st.text_input("DUI (sin guion o con guion, como esté en BD)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        if not dui_in or not password:
            st.warning("Ingrese DUI y contraseña.")
            return

        # Busca por DUI (tabla: usuarios, columnas exactas de tu BD)
        sql = """
            SELECT id_usuarios, Nombre, DUI, Contraseña, Rol, id_distrito, id_grupo, Activo
            FROM usuarios
            WHERE DUI = %s
            LIMIT 1
        """
        user = fetch_one(sql, (dui_in,))
        if not user:
            st.error("Usuario no encontrado.")
            return

        if str(user.get("Activo", "")).strip() not in {"1", "si", "sí", "SI", "true", "True"}:
            st.error("Usuario inactivo.")
            return

        if not _check_password(password, user["Contraseña"] or ""):
            st.error("Credenciales inválidas.")
            return

        # Guarda en sesión lo necesario para el alcance
        set_user({
            "id_usuarios": user["id_usuarios"],
            "Nombre": user["Nombre"],
            "DUI": user["DUI"],
            "Rol": (user["Rol"] or "").upper().strip(),
            "id_distrito": user.get("id_distrito"),
            "id_grupo": user.get("id_grupo"),
        })
        st.success("Ingreso exitoso.")
        st.rerun()
