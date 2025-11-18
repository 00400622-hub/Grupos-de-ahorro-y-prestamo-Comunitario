import os, sys
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from modulos.auth.login import login_screen
from modulos.auth.rbac import current_user, logout_button
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
        st.write(f"**Usuario:** {user.get('Nombre','')}")
        st.write(f"**Rol:** {user.get('Rol','')}")
        logout_button()

    rol = (user.get("Rol") or "").upper().strip()
    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        directiva_panel()
    else:
        st.error("Rol no reconocido.")

if __name__ == "__main__":
    router()
