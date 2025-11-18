# modulos/auth/rbac.py

import streamlit as st


# =========================================================
#  Manejo de sesión de usuario
# =========================================================

def get_user():
    """Devuelve el usuario guardado en sesión o None."""
    return st.session_state.get("user")


def set_user(data: dict):
    """Guarda el usuario en la sesión."""
    st.session_state["user"] = data


def clear_user():
    """Cierra sesión (elimina al usuario de session_state)."""
    st.session_state.pop("user", None)


# =========================================================
#  Reglas de rol
# =========================================================

def _require_role(expected_role: str):
    """
    Verifica que haya usuario en sesión y que tenga el rol esperado.
    expected_role: 'ADMINISTRADOR', 'PROMOTORA', 'DIRECTIVA'
    """
    user = get_user()
    if not user:
        import streamlit as st
        st.error("No hay una sesión activa.")
        st.stop()

    rol = (user.get("Rol") or "").upper().strip()
    if rol != expected_role.upper():
        import streamlit as st
        st.error("No tiene permisos para ver esta sección.")
        st.stop()

    return user


def require_admin():
    return _require_role("ADMINISTRADOR")


def require_promotora():
    return _require_role("PROMOTORA")


def require_directiva():
    return _require_role("DIRECTIVA")
