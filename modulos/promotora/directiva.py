# modulos/promotora/directiva.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute


def _grupos_de_promotora_por_dui(dui: str):
    """
    Devuelve los grupos donde el DUI indicado aparece en la columna DUIs_promotoras.
    """
    return fetch_all(
        """
        SELECT g.Id_grupo, g.Nombre
        FROM grupos g
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Id_grupo
        """,
        (dui,),
    )


def crear_directiva_panel(promotora: dict):
    """
    Panel para que la PROMOTORA cree usuarias de DIRECTIVA para sus grupos.
    - Crea el usuario en la tabla Usuario (rol DIRECTIVA)
    - Registra a la directiva en la tabla 'directiva', ligada a un grupo.
    """
    st.subheader("Crear Directiva")

    st.caption(
        f"Promotora responsable: {promotora['Nombre']} — DUI: {promotora['DUI']}"
    )

    # 1) Grupos disponibles para esta promotora
    grupos = _grupos_de_promotora_por_dui(promotora["DUI"])

    if not grupos:
        st.info(
            "No se encontraron grupos donde tu DUI esté asignado como promotora. "
            "Primero crea un grupo en la pestaña 'Crear grupo'."
        )
        return

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos
    }
    etiqueta_sel = st.selectbox(
        "Grupo al que pertenecerá la directiva",
        list(opciones_grupo.keys()),
    )
    id_grupo_sel = opciones_grupo[etiqueta_sel]

    st.write("---")

    # 2) Datos de la directiva
    nombre = st.text_input("Nombre completo de la directiva")
    dui = st.text_input("DUI de la directiva")
    contraseña = st.text_input(
        "Contraseña para el usuario de directiva", type="password"
    )

    if st.button("Crear directiva"):
        nombre_ok = nombre.strip()
        dui_ok = dui.strip()
        pass_ok = contraseña.strip()

        if not (nombre_ok and dui_ok and pass_ok):
            st.warning("Completa todos los campos: nombre, DUI y contraseña.")
            return

        # 2.1 Verificar que no exista ya un usuario con ese DUI
        existente = fetch_one(
            "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
            (dui_ok,),
        )
        if existente:
            st.error(
                "Ya existe un usuario registrado con ese DUI en la tabla 'Usuario'. "
                "No se puede crear otro usuario con el mismo DUI."
            )
            return

        # 2.2 Obtener Id_rol correspondiente a DIRECTIVA
        fila_rol = fetch_one(
            "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
        )
        if not fila_rol:
            st.error(
                "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                "Crea ese rol antes de registrar directivas."
            )
            return

        id_rol_directiva = fila_rol["Id_rol"]

        # 2.3 Insertar en Usuario
        uid = execute(
            """
            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre_ok, dui_ok, pass_ok, id_rol_directiva),
            return_last_id=True,
        )

        # 2.4 Insertar en directiva
        hoy = dt.date.today()
        execute(
            """
            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre_ok, dui_ok, id_grupo_sel, hoy),
        )

        st.success(
            f"Directiva creada correctamente para el grupo {etiqueta_sel}. "
            f"(Id_usuario creado: {uid})"
        )
        st.experimental_rerun()
