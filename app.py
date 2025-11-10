import streamlit as st
from modulos.auth.login import login_screen
from modulos.admin.panel import panel_admin
from modulos.promotora.grupos import listado_grupos_distrito
from modulos.directiva.panel import panel_directiva


# ⚙️ Configuración general de la app
st.set_page_config(page_title="SGI GAPC", page_icon="💠", layout="wide")


# 🔄 Función auxiliar compatible con distintas versiones de Streamlit
def _safe_rerun():
    """Intenta recargar la app, compatible con versiones nuevas y viejas de Streamlit."""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


# 🎛️ Menú lateral (panel por tipo de usuario)
def sidebar_menu():
    user = st.session_state.get("user")
    if not user:
        return

    # --- Información del usuario ---
    st.sidebar.title(f"👋 Hola, {user['nombre']}")
    st.sidebar.write(f"Rol: **{user['rol']}**")

    # --- Panel para el Administrador ---
    if user["rol"] == "ADMIN":
        panel_admin()

    # --- Panel para la Promotora ---
    elif user["rol"] == "PROMOTORA":
        sel = st.sidebar.radio("Menú", ["Grupos del distrito", "Reportes del distrito"])
        if sel == "Grupos del distrito":
            listado_grupos_distrito()
        else:
            st.info("📊 Reportes del distrito (pendiente).")

    # --- Panel para la Directiva ---
    elif user["rol"] == "DIRECTIVA":
        sel = st.sidebar.radio("Menú", ["Mi grupo", "Reportes del grupo"])
        if sel == "Mi grupo":
            panel_directiva()
        else:
            st.info("📄 Reportes del grupo (pendiente).")

    # --- Botón de cierre de sesión ---
    if st.sidebar.button("🚪 Cerrar sesión"):
        st.session_state.clear()
        _safe_rerun()


# 🚀 Punto de entrada principal
def main():
    if not st.session_state.get("autenticado"):
        login_screen()
    else:
        sidebar_menu()


# 🧩 Ejecutar la aplicación
if __name__ == "__main__":
    main()
