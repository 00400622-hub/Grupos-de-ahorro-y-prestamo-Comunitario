import streamlit as st

from modulos.auth.rbac import get_user, clear_user
from modulos.auth.login import login_screen
from modulos.admin.panel import admin_panel
from modulos.promotora.grupos import promotora_panel
# cuando tengas directiva:
# from modulos.directiva.panel import directiva_panel


def mostrar_barra_sesion(user):
    st.sidebar.markdown("### Sesión")
    st.sidebar.write("Usuario:", user["Nombre"])
    st.sidebar.write("Rol:", user["Rol"])
    if st.sidebar.button("Cerrar sesión"):
        clear_user()
        st.experimental_rerun()


def router():
    st.set_page_config(page_title="SGI GAPC", layout="wide")

    user = get_user()

    if not user:
        # Nadie logueado → pantalla de login
        login_screen()
        return

    # Hay usuario: mostrar barra lateral y panel según rol
    mostrar_barra_sesion(user)

    rol = (user.get("Rol") or "").upper().strip()

    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        st.write("Aquí iría el panel de DIRECTIVA.")
        # directiva_panel()
    else:
        st.error(f"Rol no reconocido: {rol}")


if __name__ == "__main__":
    router()
