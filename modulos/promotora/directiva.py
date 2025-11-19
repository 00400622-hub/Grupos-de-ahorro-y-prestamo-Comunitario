# modulos/promotora/directiva.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import has_role


def _obtener_grupos_de_promotora(dui_promotora: str):
    """
    Devuelve los grupos donde el DUI indicado aparece en la columna DUIs_promotoras.
    Se usa para que la promotora solo pueda asignar directivas a SUS grupos.
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
        -- Quitamos espacios en DUIs_promotoras por si los hay
        WHERE FIND_IN_SET(%s, REPLACE(g.DUIs_promotoras, ' ', '')) > 0
        ORDER BY g.Id_grupo
    """
    return fetch_all(sql, (dui_promotora,))


def _listar_directivas_de_promotora(dui_promotora: str):
    """
    Lista las directivas cuya Id_grupo pertenece a grupos donde aparece el DUI de la promotora.
    """
    sql = """
        SELECT 
            dir.Id_directiva,
            dir.Nombre,
            dir.DUI,
            g.Id_grupo,
            g.Nombre AS Grupo,
            g.DUIs_promotoras,
            dir.Creado_en
        FROM directiva dir
        JOIN grupos g ON g.Id_grupo = dir.Id_grupo
        WHERE FIND_IN_SET(%s, REPLACE(g.DUIs_promotoras, ' ', '')) > 0
        ORDER BY dir.Id_directiva
    """
    return fetch_all(sql, (dui_promotora,))


@has_role("PROMOTORA")
def crear_directiva_panel(promotora: dict):
    """
    Pestaña 'Crear Directiva' dentro del panel de promotora.

    - La promotora crea usuarios con rol DIRECTIVA.
    - Se inserta tanto en la tabla Usuario como en la tabla directiva.
    - Solo puede asignar directivas a grupos donde su DUI esté en DUIs_promotoras.
    """

    st.subheader("Crear directiva de grupo")

    st.caption(
        f"Promotora: {promotora['Nombre']} — DUI: {promotora['DUI']}"
    )

    # ==========================
    # Grupos de la promotora
    # ==========================
    grupos = _obtener_grupos_de_promotora(promotora["DUI"])
    if not grupos:
        st.info(
            "No tienes grupos asignados todavía. "
            "Primero crea grupos o pide al administrador que te asigne a alguno."
        )
        return

    mapa_grupos = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    # ==========================
    # Formulario de creación
    # ==========================
    with st.form("form_crear_directiva"):
        nombre_dir = st.text_input("Nombre de la persona de la directiva")
        dui_dir = st.text_input(
            "DUI de la directiva (sin guiones o como lo manejes)"
        )
        contr_dir = st.text_input(
            "Contraseña para la directiva", type="password"
        )

        etiqueta_grupo = st.selectbox(
            "Grupo al que pertenece la directiva",
            list(mapa_grupos.keys()),
        )
        id_grupo_sel = mapa_grupos[etiqueta_grupo]

        enviar = st.form_submit_button("Crear directiva")

    if enviar:
        # Validaciones básicas
        if not (nombre_dir.strip() and dui_dir.strip() and contr_dir.strip()):
            st.warning("Completa nombre, DUI y contraseña.")
            return

        # Verificar que exista el rol DIRECTIVA
        rol_dir = fetch_one(
            "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
        )
        if not rol_dir:
            st.error(
                "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                "Pídele al administrador que lo cree."
            )
            return

        id_rol_directiva = rol_dir["Id_rol"]

        # Verificar que el DUI no exista ya como usuario (para evitar conflictos)
        existe_usuario = fetch_one(
            "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
            (dui_dir,),
        )
        if existe_usuario:
            st.warning(
                "Ya existe un usuario con ese DUI. "
                "Si es una directiva previa, usa sus credenciales existentes."
            )
            return

        # Insertar en Usuario
        hoy = dt.date.today()
        id_usuario_nuevo = execute(
            """
            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre_dir.strip(), dui_dir.strip(), contr_dir.strip(), id_rol_directiva),
            return_last_id=True,
        )

        # Insertar en tabla directiva
        execute(
            """
            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre_dir.strip(), dui_dir.strip(), id_grupo_sel, hoy),
        )

        st.success(
            f"Directiva creada correctamente y asociada al grupo {etiqueta_grupo}. "
            f"(Id_usuario={id_usuario_nuevo})"
        )
        st.rerun()

    # ==========================
    # Listado de directivas
    # ==========================
    st.markdown("---")
    st.subheader("Directivas registradas en tus grupos")

    directivas = _listar_directivas_de_promotora(promotora["DUI"])
    if directivas:
        st.table(directivas)
    else:
        st.info("Aún no hay directivas registradas en tus grupos.")
        return  # nada más que gestionar

    # ============================================================
    # Eliminar directiva de un grupo (y opcionalmente su Usuario)
    # ============================================================
    st.markdown("---")
    st.subheader("Eliminar directiva de un grupo")

    opciones_dir = {
        f"{d['Id_directiva']} - {d['Nombre']} (Grupo {d['Id_grupo']} - {d['Grupo']}, DUI {d['DUI']})": d
        for d in directivas
    }

    etiqueta_dir = st.selectbox(
        "Selecciona la directiva que deseas eliminar",
        list(opciones_dir.keys()),
        key="sel_directiva_eliminar",
    )
    dir_sel = opciones_dir.get(etiqueta_dir)

    confirmar_elim = st.checkbox(
        "Confirmo que deseo eliminar esta directiva del grupo.",
        key="chk_eliminar_directiva",
    )

    if st.button(
        "Eliminar directiva",
        type="secondary",
        key="btn_eliminar_directiva",
    ):
        if not dir_sel:
            st.warning("Debes seleccionar una directiva.")
        elif not confirmar_elim:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            dui_dir = dir_sel["DUI"]

            # 1) Eliminar el registro de la tabla directiva
            execute(
                "DELETE FROM directiva WHERE Id_directiva = %s",
                (dir_sel["Id_directiva"],),
            )

            # 2) Verificar si todavía existe alguna directiva con ese mismo DUI
            aun_tiene_directivas = fetch_one(
                "SELECT Id_directiva FROM directiva WHERE DUI = %s LIMIT 1",
                (dui_dir,),
            )

            # 3) Si ya no tiene directivas, eliminar también al usuario con rol DIRECTIVA
            if not aun_tiene_directivas:
                execute(
                    """
                    DELETE u FROM Usuario u
                    JOIN rol r ON r.Id_rol = u.Id_rol
                    WHERE u.DUI = %s AND r.`Tipo de rol` = 'DIRECTIVA'
                    """,
                    (dui_dir,),
                )

            st.success("Directiva eliminada correctamente.")
            st.rerun()
