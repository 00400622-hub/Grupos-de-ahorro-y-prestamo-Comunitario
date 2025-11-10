import streamlit as st
from typing import Iterable

def set_user_session(user_row, permisos: set[str]):
    st.session_state["user"] = {
        "id": user_row["id"],
        "nombre": user_row["nombre"],
        "dui": user_row.get("dui"),          # ← ahora guardamos DUI
        "rol": user_row["rol"],
        "distrito_id": user_row.get("distrito_id"),
        "grupo_id": user_row.get("grupo_id"),
    }
    st.session_state["permisos"] = permisos
    st.session_state["autenticado"] = True

def usuario_tiene(perms: Iterable[str]) -> bool:
    return all(p in st.session_state.get("permisos", set()) for p in perms)

def requiere(*perms):
    def deco(view):
        def inner(*args, **kwargs):
            if not st.session_state.get("autenticado"):
                st.error("Sesión no válida."); return
            if not usuario_tiene(perms):
                st.error("No tienes permisos para esta acción."); return
            return view(*args, **kwargs)
        return inner
    return deco
