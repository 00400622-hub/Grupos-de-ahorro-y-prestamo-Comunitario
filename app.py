import os
import sys
import streamlit as st

# =====================================
# 🔧 Asegura que Python vea la carpeta raíz del proyecto
# =====================================
# Esto soluciona errores de importación en Streamlit Cloud o entornos externos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# =====================================
# 📦 Importaciones de módulos
# =====================================
from modulos.auth.login import login_screen
from modulos.auth.rbac import require_auth, current_user, logout_button
from modulos.admin.panel import admin_panel
from modulos.promotora.grupos import promotora_panel
from modulos.directiva.panel import directiva_panel

# =====================================
# ⚙️ Configuración general de Streamlit
# =====================================
st.set_page_config(
    page_title="SGI GAPC — Sistema de Grupos de Ahorro y Préstamo Comunitario",
    page_icon="💠",
    layout="wide"
)

# =====================================
# 🚀 Router principal
# =====================================
def router():
    user = current_user()

    # Si no hay usuario en sesión, mostrar login
    if not user:
        login_screen()
        return

    # Sidebar con datos de sesión y logout
    with st.sidebar:
        st.markdown("### Sesión actual")
        st.write(f"👤 **Usuario:** {user.get('Nombre','')}")
        st.write(f"🧩 **Rol:** {user.get('Rol','')}")
        logout_button()

    # Redirección por rol
    rol = (user.get("Rol") or "").upper().strip()
    if rol == "ADMINISTRADOR":
        admin_panel()
    elif rol == "PROMOTORA":
        promotora_panel()
    elif rol == "DIRECTIVA":
        directiva_panel()
    else:
        st.error("⚠️ Rol no reconocido. Contacte al administrador del sistema.")

# =====================================
# 🏁 Ejecución
# =====================================
if __name__ == "__main__":
    router()
