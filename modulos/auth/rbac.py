import streamlit as st


# ==========================
#  Manejo de usuario en sesión
# ==========================
def get_user():
    """Devuelve el diccionario de usuario guardado en sesión o None."""
    return st.session_state.get("user")


def set_user(user_dict: dict):
    """Guarda el usuario en la sesión."""
    st.session_state["user"] = user_dict


def clear_user():
    """Elimina el usuario de la sesión."""
    st.session_state.pop("user", None)


# ==========================
#  Decorador: requiere estar logueado
# ==========================
def require_auth(func):
    """
    Decorador: si no hay usuario en sesión, muestra error y detiene la ejecución.
    """

    def wrapper(*args, **kwargs):
        if "user" not in st.session_state:
            st.error("No hay una sesión activa.")
            st.stop()
        return func(*args, **kwargs)

    return wrapper


# ==========================
#  Decorador: requiere rol específico
# ==========================
def require_user_role(*roles_aceptados):
    """
    Uso:
        @require_auth
        @require_user_role("ADMINISTRADOR", "PROMOTORA")
        def mi_pantalla():
            ...
    """
    roles_norm = {r.upper().strip() for r in roles_aceptados}

    def decorator(func):
        def wrapper(*args, **kwargs):
            user = st.session_state.get("user")
            if not user:
                st.error("No hay una sesión activa.")
                st.stop()

            rol = (user.get("Rol") or "").upper().strip()
            if rol not in roles_norm:
                st.error("No tiene permisos para ver esta sección.")
                st.stop()

            return func(*args, **kwargs)

        return wrapper

    return decorator
