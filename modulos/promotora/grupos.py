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

    # Mostrar el usuario (DUI) con el que se está creando el grupo
    st.text_input(
        "DUI de promotora(s) asignada(s) al grupo",
        value=promotora["DUI"],
        disabled=True,
        help="Por defecto se asigna tu DUI. Luego puedes agregar más DUIs en 'Mis grupos'.",
    )

    if st.button("Guardar grupo", type="primary"):
        if not nombre_grupo.strip():
            st.warning("Ingrese un nombre válido para el grupo.")
            return

        if not id_distrito:
            st.warning("Seleccione un distrito.")
            return

        hoy = dt.date.today()

        # Insertamos el grupo ligado a esta promotora
        # y guardamos en DUIs_promotoras el DUI de la promotora que crea el grupo.
        execute(
            """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado, Creado_por, Creado_en, Id_promotora, DUIs_promotoras)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nombre_grupo.strip(),
                id_distrito,
                "ACTIVO",
                promotora["Id_promotora"],
                hoy,
                promotora["Id_promotora"],
                promotora["DUI"],       # lista inicial de DUIs (solo la creadora)
            ),
        )

        st.success("Grupo creado correctamente.")
        st.experimental_rerun()


# =====================================================
#  Mis grupos (solo los que tienen mi DUI en DUIs_promotoras)
# =====================================================
def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    # Filtramos por DUIs_promotoras: el DUI de la promotora debe estar en la lista
    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               g.DUIs_promotoras
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, REPLACE(IFNULL(g.DUIs_promotoras,''), ' ', '')) > 0
        ORDER BY g.Id_grupo ASC
        """,
        (promotora["DUI"],),
    )

    if not grupos:
        st.info("Aún no tienes grupos asociados a tu DUI.")
        return

    st.write("### Lista de grupos donde tu DUI está asignado")
    st.dataframe(grupos)

    st.write("---")
    st.write("### Editar promotoras (DUIs) asignadas a un grupo")

    # Mapa para seleccionar un grupo y editar solo el campo DUIs_promotoras
    opciones = {
        f'{g["Id_grupo"]} - {g["Nombre"]}': g for g in grupos
    }
    label_sel = st.selectbox(
        "Seleccione el grupo a editar",
        list(opciones.keys()),
    )
    grupo_sel = opciones[label_sel]

    duis_actuales = grupo_sel["DUIs_promotoras"] or ""
    nuevos_duis = st.text_input(
        "DUIs de promotoras asignadas (separados por coma, sin espacios)",
        value=duis_actuales,
        help="Ejemplo: 004006223,004006224. "
             "El DUI de cualquier promotora que esté en esta lista verá este grupo en su panel.",
    )

    if st.button("Actualizar promotoras del grupo"):
        cadena = (nuevos_duis or "").strip()
        if not cadena:
            st.warning("Debes indicar al menos un DUI.")
            return

        # Guardamos solo este campo, es la única parte editable
        execute(
            "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
            (cadena, grupo_sel["Id_grupo"]),
        )
        st.success("Promotoras asignadas actualizadas correctamente.")
        st.experimental_rerun()


# =====================================================
#  Placeholder para la pestaña “Crear Directiva”
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
