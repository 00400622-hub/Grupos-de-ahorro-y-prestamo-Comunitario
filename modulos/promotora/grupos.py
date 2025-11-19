# modulos/promotora/grupos.py
import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import get_user, require_auth, has_role


# =====================================================
#  Helpers
# =====================================================
def _obtener_promotora_actual() -> dict | None:
    """
    Devuelve la fila de 'promotora' asociada al usuario en sesión
    (usando JOIN por DUI). Si no existe, devuelve None.
    """
    user = get_user()
    if not user:
        return None

    uid = user.get("Id_usuario")
    if not uid:
        return None

    # Usamos JOIN para asegurarnos de que es la promotora del usuario logueado
    return fetch_one(
        """
        SELECT p.Id_promotora, p.Nombre, p.DUI
        FROM promotora p
        JOIN Usuario u ON u.DUI = p.DUI
        WHERE u.Id_usuario = %s
        LIMIT 1
        """,
        (uid,),
    )


def _select_distrito() -> int | None:
    """Combo de distritos, devuelve Id_distrito o None si no hay selección."""
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )

    if not distritos:
        st.warning("No hay distritos registrados. Primero crea distritos desde el panel de Administrador.")
        return None

    opciones = {d["Nombre"]: d["Id_distrito"] for d in distritos}
    nombre_sel = st.selectbox("Distrito", list(opciones.keys()))
    return opciones.get(nombre_sel)


# =====================================================
#  Crear grupo
# =====================================================
def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    nombre_grupo = st.text_input("Nombre del grupo")
    id_distrito = _select_distrito()

    if st.button("Guardar grupo", type="primary"):
        if not nombre_grupo.strip():
            st.warning("Ingrese un nombre válido para el grupo.")
            return

        if not id_distrito:
            st.warning("Seleccione un distrito.")
            return

        hoy = dt.date.today()

        # Insertamos el grupo ligado a esta promotora
        execute(
            """
            INSERT INTO grupos (Nombre, Id_distrito, Estado, Creado_por, Creado_en, Id_promotora)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nombre_grupo.strip(),
                id_distrito,
                "ACTIVO",
                promotora["Id_promotora"],
                hoy,
                promotora["Id_promotora"],
            ),
        )

        st.success("Grupo creado correctamente.")
        st.experimental_rerun()


# =====================================================
#  Mis grupos (solo los de esa promotora)
# =====================================================
def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo ASC
        """,
        (promotora["Id_promotora"],),
    )

    if not grupos:
        st.info("Aún no tienes grupos registrados.")
        return

    st.dataframe(grupos)


# =====================================================
#  Placeholder para la pestaña “Crear Directiva”
#  (puedes reemplazarlo luego con tu lógica completa)
# =====================================================
def _crear_directiva_tab(promotora: dict):
    st.subheader("Crear Directiva del grupo")
    st.info("Aquí luego puedes implementar la creación de la directiva asociada a tus grupos.")


# =====================================================
#  Reportes
# =====================================================
def _reportes_tab(promotora: dict):
    st.subheader("Reportes de mis grupos")
    st.info("Aquí luego puedes agregar reportes filtrados por los grupos de esta promotora.")


# =====================================================
#  Panel de Promotora
# =====================================================
@require_auth
@has_role("PROMOTORA")
def promotora_panel():
    st.title("Panel de Promotora")

    promotora = _obtener_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    # Mostrar quién es la promotora actual
    st.caption(f"Promotora: {promotora['Nombre']} — DUI: {promotora['DUI']}")

    pestañas = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with pestañas[0]:
        _crear_grupo(promotora)

    with pestañas[1]:
        _mis_grupos(promotora)

    with pestañas[2]:
        _crear_directiva_tab(promotora)

    with pestañas[3]:
        _reportes_tab(promotora)
