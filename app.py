# app.py
import streamlit as st

from modulos.auth.login import login_screen
from modulos.auth.rbac import get_user, clear_user
from modulos.admin.panel import admin_panel
from modulos.promotora.grupos import promotora_panel
from modulos.directiva.panel import directiva_panel 

st.set_page_config(page_title="SGI GAPC", layout="wide")


def router():
    user = get_user()

    if not user:
        # Sin sesión → mostramos login
        login_screen()
        return

    # Con sesión → mostramos barra lateral de sesión
    with st.sidebar:
        st.write("Sesión")
        st.write(f"Usuario: {user['Nombre']}")
        st.write(f"Rol: {user['Rol']}")
        if st.button("Cerrar sesión"):
            clear_user()
            st.rerun()

    rol = (user.get("Rol") or "").upper().strip()

    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        directiva_panel()
    else:
        st.error(f"Rol desconocido: {rol}")


if __name__ == "__main__":
    router()
