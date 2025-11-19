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
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
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
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
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
    # Formulario de creación (NUEVA DIRECTIVA + USUARIO)
    # ==========================
    with st.form("form_crear_directiva"):
        nombre_dir = st.text_input("Nombre de la persona de la directiva")
        dui_dir = st.text_input("DUI de la directiva (sin guiones o como lo manejes)")
        contr_dir = st.text_input("Contraseña para la directiva", type="password")

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
            "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1", (dui_dir,)
        )
        if existe_usuario:
            st.warning(
                "Ya existe un usuario con ese DUI. "
                "Si es una directiva previa, usa sus credenciales existentes "
                "o la sección de 'Asignar directiva existente a un grupo'."
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

    # ============================================================
    # >>> NUEVO: Eliminar directiva de un grupo
    # ============================================================
    if directivas:
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

        if st.button("Eliminar directiva", type="secondary", key="btn_eliminar_directiva"):
            if not dir_sel:
                st.warning("Debes seleccionar una directiva.")
            elif not confirmar_elim:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                execute(
                    "DELETE FROM directiva WHERE Id_directiva = %s",
                    (dir_sel["Id_directiva"],),
                )
                st.success("Directiva eliminada correctamente del grupo.")
                st.rerun()

    # ============================================================
    # >>> NUEVO: Asignar directiva EXISTENTE a un grupo ya creado
    # ============================================================
    st.markdown("---")
    st.subheader("Asignar directiva existente a un grupo ya creado")

    st.caption(
        "Usa esta sección cuando la persona que estaba a cargo se retira "
        "y quieres asignar a otra directiva que ya tiene usuario creado."
    )

    with st.form("form_asignar_directiva_existente"):
        dui_exist = st.text_input(
            "DUI de la directiva existente (debe tener usuario con rol DIRECTIVA)",
            key="dui_directiva_existente",
        )
        etiqueta_grupo2 = st.selectbox(
            "Grupo al que deseas asignarla",
            list(mapa_grupos.keys()),
            key="grupo_asignar_existente",
        )
        id_grupo_sel2 = mapa_grupos[etiqueta_grupo2]

        enviar_asignar = st.form_submit_button("Asignar directiva existente al grupo")

    if enviar_asignar:
        dui_exist = (dui_exist or "").strip()
        if not dui_exist:
            st.warning("Debes escribir el DUI de la directiva existente.")
            return

        # Verificar que exista como usuario con rol DIRECTIVA
        usuario_dir = fetch_one(
            """
            SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol`
            FROM Usuario u
            JOIN rol r ON r.Id_rol = u.Id_rol
            WHERE u.DUI = %s AND r.`Tipo de rol` = 'DIRECTIVA'
            LIMIT 1
            """,
            (dui_exist,),
        )

        if not usuario_dir:
            st.error(
                "No se encontró un usuario con ese DUI y rol 'DIRECTIVA'. "
                "Primero crea el usuario en la sección de arriba o pide al administrador que lo cree."
            )
            return

        # Verificar que no esté ya asignada esa directiva al grupo
        existe_dir_grupo = fetch_one(
            """
            SELECT Id_directiva 
            FROM directiva 
            WHERE DUI = %s AND Id_grupo = %s 
            LIMIT 1
            """,
            (dui_exist, id_grupo_sel2),
        )

        if existe_dir_grupo:
            st.info(
                "Esa directiva ya está registrada para el grupo seleccionado."
            )
            return

        # Insertar solo en tabla directiva (NO se crea usuario nuevo)
        hoy2 = dt.date.today()
        execute(
            """
            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
            VALUES (%s, %s, %s, %s)
            """,
            (usuario_dir["Nombre"], usuario_dir["DUI"], id_grupo_sel2, hoy2),
        )

        st.success(
            f"Directiva existente (DUI {usuario_dir['DUI']}) asignada correctamente "
            f"al grupo {etiqueta_grupo2}."
        )
        st.rerun()
