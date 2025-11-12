import streamlit as st
from modulos.auth.login import login_screen
from modulos.auth.rbac import require_auth, current_user, logout_button
from modulos.admin.panel import admin_panel
from modulos.promotora.grupos import promotora_panel
from modulos.directiva.panel import directiva_panel

st.set_page_config(page_title="SGI GAPC", page_icon="💠", layout="wide")

def router():
    user = current_user()
    if not user:
        login_screen()
        return

    with st.sidebar:
        st.markdown("### Sesión")
        st.write(f"**Usuario:** {user.get('Nombre','')}  \n**Rol:** {user.get('Rol','')}")
        logout_button()

    rol = user.get("Rol", "").upper().strip()
    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        directiva_panel()
    else:
        st.error("Rol no reconocido. Contacte al administrador.")

if __name__ == "__main__":
    router()
