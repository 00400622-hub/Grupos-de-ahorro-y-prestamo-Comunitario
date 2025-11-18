import streamlit as st

# ==========================
# Manejo básico de sesión
# ==========================

def get_current_user() -> dict | None:
    """
    Devuelve el usuario guardado en la sesión, o None si no hay.
    """
    return st.session_state.get("user")


def set_user(user: dict) -> None:
    """
    Guarda el usuario en la sesión.
    Espera un diccionario con al menos: Id_usuario, Nombre, DUI, id_rol, Rol.
    """
    st.session_state["user"] = user


def clear_user() -> None:
    """
    Elimina el usuario de la sesión (logout).
    """
    if "user" in st.session_state:
        del st.session_state["user"]


# =========================================
# Helpers de autorización / protección de vistas
# =========================================

def require_auth() -> dict:
    """
    Verifica que haya un usuario logueado.
    - Si NO hay sesión, muestra error y detiene la ejecución.
    - Si SÍ hay sesión, devuelve el diccionario de usuario.
    """
    user = get_current_user()
    if not user:
        st.error("No hay una sesión activa.")
        st.stop()   # Detiene el script de Streamlit
    return user


def has_role(*roles_permitidos: str) -> dict:
    """
    Verifica que el usuario logueado tenga uno de los roles permitidos.
    Uso típico:
        user = has_role("ADMINISTRADOR")
        user = has_role("PROMOTORA", "ADMINISTRADOR")
    - Si no hay sesión -> mismo comportamiento que require_auth().
    - Si hay sesión pero el rol no está en roles_permitidos -> error y st.stop().
    - Si todo bien -> devuelve el diccionario de usuario.
    """
    user = require_auth()
    rol_usuario = (user.get("Rol") or "").upper().strip()
    roles_norm = [r.upper().strip() for r in roles_permitidos]

    if roles_norm and rol_usuario not in roles_norm:
        st.error("No tiene permisos para ver esta página.")
        st.stop()

    return user
