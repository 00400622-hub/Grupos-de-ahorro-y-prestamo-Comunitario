# modulos/promotora/directiva.py

import streamlit as st
import bcrypt
import pandas as pd

from modulos.config.conexion import fetch_all, execute


def _normalizar_dui(txt: str) -> str:
    """Deja solo dígitos en el DUI."""
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _obtener_grupos_de_promotora(dui_promotora: str):
    """
    Devuelve los grupos donde el DUI de la promotora aparece
    en la columna DUIs_promotoras.
    """
    sql = """
        SELECT
            Id_grupo,
            Nombre,
            Estado,
            Creado_en,
            DUIs_promotoras
        FROM grupos
        WHERE FIND_IN_SET(%s, DUIs_promotoras)
        ORDER BY Id_grupo
    """
    return fetch_all(sql, (dui_promotora,))


def _obtener_directivas_de_grupo(id_grupo: int):
    """
    Devuelve las directivas de un grupo específico.
    """
    sql = """
        SELECT
            Id_directiva,
            Nombre,
            DUI,
            Id_grupo,
            Creado_en
        FROM directiva
        WHERE Id_grupo = %s
        ORDER BY Id_directiva
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_directivas_de_promotora(dui_promotora: str):
    """
    Devuelve todas las directivas de los grupos donde la promotora
    actual participa (según DUIs_promotoras).
    """
    sql = """
        SELECT
            d.Id_directiva,
            d.Nombre       AS Nombre_directiva,
            d.DUI          AS DUI_directiva,
            g.Id_grupo,
            g.Nombre       AS Grupo,
            d.Creado_en
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Id_grupo, d.Id_directiva
    """
    return fetch_all(sql, (dui_promotora,))


def _crear_usuario_directiva(nombre: str, dui: str, password: str, id_rol_directiva: int = 3):
    """
    Crea el usuario en la tabla Usuario para la directiva.
    Ajusta id_rol_directiva si en tu tabla de roles la directiva tiene otro Id.
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    sql = """
        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
        VALUES (%s, %s, %s, %s)
    """
    execute(sql, (nombre.strip(), dui, hashed, id_rol_directiva), return_last_id=False)


def _crear_directiva(nombre: str, dui: str, id_grupo: int):
    """
    Inserta el registro de la directiva en la tabla directiva.
    """
    sql = """
        INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
        VALUES (%s, %s, %s, CURDATE())
    """
    execute(sql, (nombre.strip(), dui, id_grupo), return_last_id=False)


def _eliminar_directiva(id_directiva: int, dui: str):
    """
    Elimina la directiva del grupo y su usuario asociado.
    """
    # 1) borrar de directiva
    sql_dir = "DELETE FROM directiva WHERE Id_directiva = %s"
    execute(sql_dir, (id_directiva,), return_last_id=False)

    # 2) borrar de Usuario por DUI
    sql_usr = "DELETE FROM Usuario WHERE DUI = %s"
    execute(sql_usr, (dui,), return_last_id=False)


def crear_directiva_panel(promotora: dict):
    """
    Panel de creación y gestión de directivas, visible desde el panel de promotora.
    La variable `promotora` viene del login e incluye al menos:
      - promotora["Nombre"]
      - promotora["DUI"]
    """
    nombre_prom = promotora.get("Nombre", "")
    dui_prom = _normalizar_dui(promotora.get("DUI", ""))

    st.header("Creación y gestión de directivas de grupo")
    st.caption(f"Promotora actual: {nombre_prom} — DUI: {dui_prom}")

    # ==========================
    # 1. Grupos de la promotora
    # ==========================
    grupos = _obtener_grupos_de_promotora(dui_prom)

    if not grupos:
        st.info(
            "No se encontraron grupos asociados a tu DUI en la tabla `grupos`. "
            "Primero debes crear grupos y asignarte como promotora."
        )
        return

    # Diccionario para selects
    opciones_grupos = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos
    }

    tab_agregar, tab_eliminar, tab_listado = st.tabs(
        ["➕ Agregar directiva a grupo", "🗑️ Eliminar directivas", "📋 Directivas existentes"]
    )

    # ========================
    # TAB 1: AGREGAR DIRECTIVA
    # ========================
    with tab_agregar:
        st.subheader("Agregar nueva directiva a un grupo")

        etiqueta_grupo = st.selectbox(
            "Selecciona el grupo donde se agregará la directiva",
            list(opciones_grupos.keys()),
            key="dir_sel_grupo_agregar",
        )
        id_grupo_sel = opciones_grupos[etiqueta_grupo]

        nombre_dir = st.text_input("Nombre de la directiva", key="dir_nombre_agregar")
        dui_dir_in = st.text_input("DUI de la directiva (con o sin guiones)", key="dir_dui_agregar")
        password_dir = st.text_input(
            "Contraseña para la cuenta de directiva",
            type="password",
            key="dir_pass_agregar",
        )

        if st.button("Guardar nueva directiva para este grupo", type="primary", key="btn_guardar_directiva"):
            dui_dir = _normalizar_dui(dui_dir_in)

            if not nombre_dir.strip() or not dui_dir or not password_dir:
                st.error("Debes completar nombre, DUI y contraseña.")
            elif len(dui_dir) != 9:
                st.error("El DUI debe tener exactamente 9 dígitos (sin contar guiones).")
            else:
                try:
                    # Crear usuario + registro de directiva
                    _crear_usuario_directiva(nombre_dir, dui_dir, password_dir)
                    _crear_directiva(nombre_dir, dui_dir, id_grupo_sel)
                    st.success("Directiva creada correctamente para el grupo seleccionado.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al crear la directiva: {e}")

    # ============================
    # TAB 2: ELIMINAR DIRECTIVAS
    # ============================
    with tab_eliminar:
        st.subheader("Eliminar directivas de un grupo")

        etiqueta_grupo2 = st.selectbox(
            "Selecciona el grupo cuyas directivas quieres gestionar",
            list(opciones_grupos.keys()),
            key="dir_sel_grupo_eliminar",
        )
        id_grupo_sel2 = opciones_grupos[etiqueta_grupo2]

        directivas_grupo = _obtener_directivas_de_grupo(id_grupo_sel2)

        if not directivas_grupo:
            st.info("Este grupo aún no tiene directivas registradas.")
        else:
            # Tabla para referencia
            df_dir = pd.DataFrame(directivas_grupo)
            df_dir = df_dir.rename(
                columns={
                    "Id_directiva": "Id_directiva",
                    "Nombre": "Nombre",
                    "DUI": "DUI",
                    "Id_grupo": "Id_grupo",
                    "Creado_en": "Creado_en",
                }
            )
            st.dataframe(df_dir, use_container_width=True)

            # Selección de directiva a eliminar
            opciones_dir = {
                f"{d['Id_directiva']} - {d['Nombre']} ({d['DUI']})": (d["Id_directiva"], d["DUI"])
                for d in directivas_grupo
            }

            etiqueta_dir = st.selectbox(
                "Selecciona la directiva a eliminar",
                list(opciones_dir.keys()),
                key="dir_a_eliminar",
            )
            id_dir_sel, dui_dir_sel = opciones_dir[etiqueta_dir]

            confirmar = st.checkbox(
                "Confirmo que deseo eliminar esta directiva y su usuario asociado (acción irreversible).",
                key="chk_confirmar_eliminar_dir",
            )

            if st.button("Eliminar directiva seleccionada", type="secondary", key="btn_eliminar_directiva"):
                if not confirmar:
                    st.warning("Debes marcar la casilla de confirmación antes de eliminar.")
                else:
                    try:
                        _eliminar_directiva(id_dir_sel, dui_dir_sel)
                        st.success("Directiva eliminada correctamente.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Ocurrió un error al eliminar la directiva: {e}")

    # ============================
    # TAB 3: LISTADO DE DIRECTIVAS
    # ============================
    with tab_listado:
        st.subheader("Directivas existentes en tus grupos")

        todas_dir = _obtener_directivas_de_promotora(dui_prom)

        if not todas_dir:
            st.info("Aún no hay directivas registradas en tus grupos.")
        else:
            df = pd.DataFrame(todas_dir)
            df = df.rename(
                columns={
                    "Id_directiva": "Id_directiva",
                    "Nombre_directiva": "Nombre",
                    "DUI_directiva": "DUI",
                    "Id_grupo": "Id_grupo",
                    "Grupo": "Grupo",
                    "Creado_en": "Creado_en",
                }
            )
            # Orden y presentación parecida a la tabla de grupos
            df = df[["Id_directiva", "Nombre", "DUI", "Id_grupo", "Grupo", "Creado_en"]]
            st.dataframe(df, use_container_width=True)
