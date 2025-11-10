import streamlit as st
from modulos.auth.login import login_screen
from modulos.admin.panel import panel_admin
from modulos.promotora.grupos import listado_grupos_distrito
from modulos.directiva.panel import panel_directiva

st.set_page_config(page_title="SGI GAPC", page_icon="💠", layout="wide")

def sidebar_menu():
    user = st.session_state.get("user")
    if not user:
        return

    st.sidebar.title(f"👋 Hola, {user['nombre']}")
    st.sidebar.write(f"Rol: **{user['rol']}**")

    if user["rol"] == "ADMIN":
        panel_admin()

    elif user["rol"] == "PROMOTORA":
        sel = st.sidebar.radio("Menú", ["Grupos del distrito", "Reportes del distrito"])
        if sel == "Grupos del distrito":
            listado_grupos_distrito()
        else:
            st.info("📊 Reportes del distrito (pendiente).")

    elif user["rol"] == "DIRECTIVA":
        sel = st.sidebar.radio("Menú", ["Mi grupo", "Reportes del grupo"])
        if sel == "Mi grupo":
            panel_directiva()
        else:
            st.info("📄 Reportes del grupo (pendiente).")

    def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

# ...
if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    _safe_rerun()

def main():
    if not st.session_state.get("autenticado"):
        login_screen()
    else:
        sidebar_menu()

if __name__ == "__main__":
    main()
