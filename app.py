import streamlit as st
from modulos.auth.login import login_screen
from modulos.admin.panel import panel_admin
from modulos.promotora.grupos import listado_grupos_distrito
from modulos.directiva.panel import panel_directiva

st.set_page_config(page_title="SGI GAPC", page_icon="💠", layout="wide")

def sidebar_menu():
    user = st.session_state.get("user")
    if not user: return
    st.sidebar.title(f"Hola, {user['nombre']}")
    st.sidebar.write(f"Rol: **{user['rol']}**")

    if user["rol"] == "ADMIN":
        panel_admin()

    elif user["rol"] == "PROMOTORA":
        sel = st.sidebar.radio("Menú", ["Grupos del distrito","Reportes del distrito"])
        listado_grupos_distrito() if sel=="Grupos del distrito" else st.info("Reportes del distrito — pronto.")

    elif user["rol"] == "DIRECTIVA":
        sel = st.sidebar.radio("Menú", ["Mi grupo","Reportes del grupo"])
        panel_directiva() if sel=="Mi grupo" else st.info("Reportes del grupo — pronto.")

    if st.sidebar.button("Cerrar sesión"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.experimental_rerun()

def main():
    if not st.session_state.get("autenticado"): login_screen()
    else: sidebar_menu()

if __name__ == "__main__":
    main()
