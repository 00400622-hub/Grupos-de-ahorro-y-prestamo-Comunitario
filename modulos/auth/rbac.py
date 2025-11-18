# modulos/auth/rbac.py
import streamlit as st

# Clave única donde guardamos el usuario en la sesión de Streamlit
_SESSION_KEY = "user"


# ==========
#  Sesión
# ==========
def get_user() -> dict | None:
    """Devuelve el usuario actual o None si no hay sesión."""
    return st.session_state.get(_SESSION_KEY)


def set_user(info: dict) -> None:
    """Guarda/actualiza el usuario en la sesión."""
    st.session_state[_SESSION_KEY] = info


def clear_user() -> None:
    """Elimina la sesión de usuario."""
    st.session_state.pop(_SESSION_KEY, None)


def is_logged_in() -> bool:
    """True si hay usuario en sesión."""
    return _SESSION_KEY in st.session_state


# ==========
#  Decoradores
# ==========
def require_auth():
    """
    Decorador: exige que haya sesión.
    Si no hay usuario, muestra mensaje y corta la ejecución.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_logged_in():
                st.error("No hay una sesión activa.")
                st.stop()
            return func(*args, **kwargs)

        return wrapper

    return decorator


def has_role(*roles_permitidos: str):
    """
    Decorador: exige que el rol del usuario esté en roles_permitidos.
    Ejemplo: @has_role("ADMINISTRADOR", "PROMOTORA")
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_user()
            if not user:
                st.error("No hay una sesión activa.")
                st.stop()

            rol_usuario = (user.get("Rol") or "").upper().strip()
            roles_ok = [r.upper().strip() for r in roles_permitidos]

            if rol_usuario not in roles_ok:
                st.error("No tiene permiso para ver esta sección.")
                st.stop()

            return func(*args, **kwargs)

        return wrapper

    return decorator
