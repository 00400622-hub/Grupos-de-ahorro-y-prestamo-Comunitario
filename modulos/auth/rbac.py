import streamlit as st

# Gestión de sesión

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
    user = current_user()
    if not user:
        return False
    return user.get("Rol", "").upper() in {r.upper() for r in roles}

def logout_button():
    if st.button("Cerrar sesión", type="secondary", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()

# Filtros de alcance
def scope_filter_sql():
    """
    Devuelve (where_clause, params) para filtrar por el alcance del usuario
    en consultas que involucren distritos o grupos.
    - ADMINISTRADOR: sin restricciones (cláusula vacía)
    - PROMOTORA: restringe por id_distrito
    - DIRECTIVA: restringe por id_grupo
    """
    u = current_user()
    if not u:
        return "", ()
    rol = (u.get("Rol") or "").upper()
    if rol == "ADMINISTRADOR":
        return "", ()
    if rol == "PROMOTORA":
        return " WHERE g.id_distrito = %s ", (u.get("id_distrito"),)
    if rol == "DIRECTIVA":
        return " WHERE g.id_grupo = %s ", (u.get("id_grupo"),)
    return "", ()
