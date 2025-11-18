# modulos/directiva/panel.py

import streamlit as st
from modulos.auth.rbac import require_directiva
from modulos.config.conexion import fetch_one


def directiva_panel():
    """
    Panel principal de la DIRECTIVA.
    Muestra solo la información del grupo que tiene asignado
    en la tabla 'directiva' (por el DUI del usuario logueado).
    """
    user = require_directiva()

    st.title("Panel de Directiva")

    dui = user.get("DUI")

    if not dui:
        st.error("El usuario actual no tiene DUI registrado.")
        st.stop()

    # Buscar en tabla 'directiva' qué grupo tiene asignado
    dir_row = fetch_one(
        "SELECT Id_directiva, Id_grupo, Nombre FROM directiva WHERE DUI = %s",
        (dui,),
    )

    if not dir_row:
        st.error(
            "No se encontró un registro de directiva asociado a este usuario.\n\n"
            "Verifica que la promotora haya creado este usuario en la sección "
            "'Crear Directiva' y que el DUI coincida."
        )
        st.stop()

    id_grupo = dir_row["Id_grupo"]

    st.info(
        f"Directiva: **{dir_row['Nombre']}** (DUI: {dui}) – "
        f"Id_directiva={dir_row['Id_directiva']}"
    )

    # Obtener datos del grupo asignado
    grupo = fetch_one(
        """
        SELECT g.Id_grupo,
               g.Nombre       AS Grupo,
               d.Nombre       AS Distrito,
               g.Estado,
               g.Creado_en
        FROM grupos g
        JOIN distritos d ON g.Id_distrito = d.Id_distrito
        WHERE g.Id_grupo = %s
        """,
        (id_grupo,),
    )

    if not grupo:
        st.error("El grupo asignado a esta directiva ya no existe.")
        st.stop()

    st.subheader("Grupo asignado")

    st.markdown(
        f"""
        - **Id_grupo:** {grupo['Id_grupo']}
        - **Nombre del grupo:** {grupo['Grupo']}
        - **Distrito:** {grupo['Distrito']}
        - **Estado:** {grupo['Estado']}
        - **Creado en:** {grupo['Creado_en']}
        """
    )

    st.info(
        "A partir de aquí puedes ir agregando las funcionalidades propias "
        "de la directiva: registrar reuniones, asistencias, ahorros, "
        "préstamos, caja, etc., siempre usando el `Id_grupo` asignado."
    )
