# modulos/promotora/grupos.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import has_role


def _obtener_grupos_de_promotora(dui_promotora: str):
    """
    Devuelve los grupos donde el DUI indicado aparece en la columna DUIs_promotoras.
    """
    sql = """
        SELECT 
            g.Id_grupo,
            g.Nombre,
            d.Nombre AS Distrito,
            g.Estado,
            g.Creado_en,
            g.DUIs_promotoras
        FROM grupos g
        LEFT JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Id_grupo
    """
    return fetch_all(sql, (dui_promotora,))


def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    st.caption(
        f"Promotora principal: {promotora['Nombre']} — DUI: {promotora['DUI']}"
    )

    nombre_grupo = st.text_input("Nombre del grupo")
    # Cargar distritos
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )
    if not distritos:
        st.warning(
            "No hay distritos registrados. Primero crea distritos desde el panel de administrador."
        )
        return

    mapa_distritos = {d["Nombre"]: d["Id_distrito"] for d in distritos}
    nombre_distrito_sel = st.selectbox(
        "Distrito", list(mapa_distritos.keys())
    )
    id_distrito_sel = mapa_distritos[nombre_distrito_sel]

    if st.button("Guardar grupo"):
        nombre_ok = nombre_grupo.strip()
        if not nombre_ok:
            st.warning("Ingresa el nombre del grupo.")
            return

        hoy = dt.date.today()
        # El DUI de la promotora que crea el grupo será el primero en la lista
        duis_promotoras = promotora["DUI"]

        execute(
            """
            INSERT INTO grupos (Nombre, Id_distrito, Estado, Creado_por, Creado_en, DUIs_promotoras)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nombre_ok,
                id_distrito_sel,
                "ACTIVO",
                promotora["Nombre"],
                hoy,
                duis_promotoras,
            ),
        )
        st.success("Grupo creado correctamente.")
        st.experimental_rerun()


def _seccion_listado_grupos(promotora: dict):
    st.subheader("Mis grupos")

    grupos = _obtener_grupos_de_promotora(promotora["DUI"])
    if not grupos:
        st.info(
            "No se encontraron grupos donde tu DUI aparezca como promotora responsable."
        )
        return grupos

    st.write(
        "Listado de grupos donde tu DUI aparece como promotora responsable."
    )
    st.table(grupos)
    return grupos


def _seccion_eliminar_grupo(promotora: dict, grupos: list):
    st.markdown("---")
    st.subheader("Eliminar grupo")

    if not grupos:
        st.info("No tienes grupos para eliminar.")
        return

    opciones = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }
    etiqueta_sel = st.selectbox(
        "Selecciona el grupo a eliminar", list(opciones.keys())
    )
    id_grupo_sel = opciones[etiqueta_sel]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer)."
    )

    if st.button("Eliminar grupo"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
            return

        # Eliminar grupo (podrías agregar aquí borrado en cascada si hace falta)
        execute("DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_sel,))
        st.success(f"Grupo {etiqueta_sel} eliminado correctamente.")
        st.experimental_rerun()


def _seccion_gestion_promotoras(grupos: list):
    st.markdown("---")
    st.subheader("Gestionar promotoras asignadas a un grupo ↩")

    if not grupos:
        st.info("No hay grupos para gestionar.")
        return

    opciones = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g for g in grupos
    }
    etiqueta_sel = st.selectbox(
        "Selecciona el grupo a gestionar", list(opciones.keys())
    )
    grupo_sel = opciones[etiqueta_sel]
    id_grupo_sel = grupo_sel["Id_grupo"]

    # DUIs actuales
    duis_actuales = []
    if grupo_sel["DUIs_promotoras"]:
        duis_actuales = [
            x.strip()
            for x in str(grupo_sel["DUIs_promotoras"]).split(",")
            if x.strip()
        ]

    st.write("DUIs asignados actualmente:", ", ".join(duis_actuales) or "Ninguno")

    st.markdown("#### Agregar nuevas promotoras al grupo")

    # Listar todas las promotoras disponibles
    todas_promos = fetch_all(
        "SELECT Nombre, DUI FROM promotora ORDER BY Nombre ASC"
    )
    if not todas_promos:
        st.info("No hay promotoras registradas en la tabla 'promotora'.")
        return

    opciones_add = {
        f"{p['Nombre']} — {p['DUI']}": p["DUI"] for p in todas_promos
    }

    duis_a_agregar = st.multiselect(
        "Selecciona las promotoras que deseas AGREGAR al grupo",
        list(opciones_add.keys()),
    )

    if st.button("Agregar promotoras al grupo"):
        nuevos_duis = set(duis_actuales)
        for etiqueta in duis_a_agregar:
            dui = opciones_add[etiqueta]
            nuevos_duis.add(dui)

        nuevo_valor = ",".join(sorted(nuevos_duis)) if nuevos_duis else ""
        execute(
            "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
            (nuevo_valor, id_grupo_sel),
        )
        st.success("Promotoras agregadas correctamente al grupo.")
        st.experimental_rerun()

    st.markdown("#### Quitar promotoras del grupo")

    if duis_actuales:
        duis_a_quitar = st.multiselect(
            "Selecciona los DUIs que deseas quitar del grupo",
            duis_actuales,
            key="duis_quitar",
        )

        if st.button("Quitar promotoras seleccionadas"):
            nuevos_duis = [d for d in duis_actuales if d not in duis_a_quitar]
            nuevo_valor = ",".join(nuevos_duis) if nuevos_duis else ""
            execute(
                "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                (nuevo_valor, id_grupo_sel),
            )
            st.success("Promotoras removidas del grupo.")
            st.experimental_rerun()
    else:
        st.info("Este grupo aún no tiene DUIs asignados.")


@has_role("PROMOTORA")
def promotora_panel(promotora: dict):
    st.title("Panel de Promotora")

    st.caption(
        f"Usuario: {promotora['Nombre']} — DUI: {promotora['DUI']}"
    )

    pestañas = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    # ---- Pestaña 1: Crear grupo ----
    with pestañas[0]:
        _crear_grupo(promotora)

    # ---- Pestaña 2: Mis grupos + eliminar + gestionar promotoras ----
    with pestañas[1]:
        grupos = _seccion_listado_grupos(promotora)
        _seccion_eliminar_grupo(promotora, grupos)
        _seccion_gestion_promotoras(grupos)

    # ---- Pestaña 3: Crear Directiva ----
    with pestañas[2]:
        from modulos.promotora.directiva import crear_directiva_panel

        crear_directiva_panel(promotora)

    # ---- Pestaña 4: Reportes (placeholder) ----
    with pestañas[3]:
        st.info(
            "Aquí más adelante puedes agregar reportes específicos para la promotora."
        )
