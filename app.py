# app.py

import streamlit as st

from modulos.auth.login import login_screen
from modulos.auth.rbac import get_user, clear_user
from modulos.admin.panel import admin_panel
from modulos.promotora.grupos import promotora_panel
from modulos.directiva.panel import directiva_panel


def router():
    # 1) Ver si hay usuario en sesión
    user = get_user()

    if not user:
        # No hay sesión -> mostrar login
        login_screen()
        return

    # 2) Barra lateral con datos y botón de cerrar sesión
    with st.sidebar:
        st.subheader("Sesión")
        st.write(f"**Usuario:** {user.get('Nombre', '')}")
        st.write(f"**Rol:** {user.get('Rol', '')}")
        if st.button("Cerrar sesión"):
            clear_user()
            st.rerun()

    # 3) Enrutamiento según rol
    rol = (user.get("Rol") or "").upper().strip()

    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        directiva_panel()
    else:
        st.error(f"Rol no reconocido: {rol}")


if __name__ == "__main__":
    router()
