import os, sys
import streamlit as st

# =========================
# Asegurar rutas en PYTHONPATH
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_DIR  = os.path.join(BASE_DIR, "modulos")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if os.path.isdir(MOD_DIR) and MOD_DIR not in sys.path:
    sys.path.insert(0, MOD_DIR)   # <- fallback: permite importar "admin.panel" si falla "modulos.admin.panel"

# =========================
# Importar módulos con fallback
# =========================
def _import_with_fallback(pkg_name, attr):
    """
    Intenta importar 'modulos.<pkg_name>.<attr>' y si falla,
    intenta 'pkg_name.<attr>' usando el MOD_DIR en sys.path.
    """
    try:
        module = __import__(f"modulos.{pkg_name}.{attr}", fromlist=[attr])
        return module
    except ImportError:
        module = __import__(f"{pkg_name}.{attr}", fromlist=[attr])
        return module

from modulos.auth.login import login_screen
from modulos.auth.rbac import current_user, logout_button

# Admin
try:
    from modulos.admin.panel import admin_panel
except ImportError:
    admin_panel = _import_with_fallback("admin", "panel").admin_panel

# Promotora
try:
    from modulos.promotora.grupos import promotora_panel
except ImportError:
    promotora_panel = _import_with_fallback("promotora", "grupos").promotora_panel

# Directiva
try:
    from modulos.directiva.panel import directiva_panel
except ImportError:
    directiva_panel = _import_with_fallback("directiva", "panel").directiva_panel

# =========================
# Configuración de Streamlit
# =========================
st.set_page_config(page_title="SGI GAPC", page_icon="💠", layout="wide")

# =========================
# Router
# =========================
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
