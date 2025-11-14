import streamlit as st

def _ensure_session():
    if "user" not in st.session_state:
        st.session_state["user"] = None

def set_user(user_dict):
    _ensure_session()
    st.session_state["user"] = user_dict

def current_user():
    _ensure_session()
    return st.session_state.get("user")

def is_authenticated():
    return current_user() is not None

def require_auth():
    if not is_authenticated():
        st.stop()

def has_role(*roles):
    """
    roles: nombres de rol en MAYÚSCULA, por ejemplo:
    has_role("ADMINISTRADOR", "PROMOTORA")
    """
    user = current_user()
    if not user:
        return False
    return (user.get("Rol") or "").upper() in {r.upper() for r in roles}

def logout_button():
    if st.button("Cerrar sesión", type="secondary", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()
