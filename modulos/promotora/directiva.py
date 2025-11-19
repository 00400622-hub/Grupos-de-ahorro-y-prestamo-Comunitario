import streamlit as st
import bcrypt
from datetime import date
import pandas as pd

from modulos.config.conexion import fetch_all, execute

# Ajusta este ID según tu tabla "rol"
ID_ROL_DIRECTIVA = 3


def _limpiar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def crear_directiva_panel(promotora: dict) -> None:
    """
    Panel de creación y gestión de directivas.
    Se asume que 'promotora' viene del login y contiene al menos:
    - promotora["Nombre"]
    - promotora["DUI"]
    """
    st.subheader("Creación y gestión de directivas de grupo")
    st.caption(f"Promotora actual: {promotora['Nombre']} — DUI: {promotora['DUI']}")

    tab_alta, tab_baja = st.tabs(["➕ Agregar directiva a grupo", "🗑️ Eliminar directivas"])

    dui_prom = promotora["DUI"]

    # ──────────────────────────────────────────────
    # Grupos donde la promotora tiene su DUI asociado
    # ──────────────────────────────────────────────
    sql_grupos = """
        SELECT Id_grupo, Nombre, DUIs_promotoras
        FROM grupos
        WHERE FIND_IN_SET(%s, DUIs_promotoras)
        ORDER BY Nombre
    """
    grupos = fetch_all(sql_grupos, (dui_prom,))

    opciones_grupos = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos
    }

    # ╔══════════════════════════════════════════╗
    # ║ TAB 1: AGREGAR DIRECTIVA A UN GRUPO     ║
    # ╚══════════════════════════════════════════╝
    with tab_alta:
        st.markdown("#### Agregar nueva directiva a un grupo")

        if not opciones_grupos:
            st.info("No tienes grupos asociados todavía.")
        else:
            etiqueta = st.selectbox(
                "Selecciona el grupo donde se agregará la directiva",
                list(opciones_grupos.keys()),
                key="sel_grupo_alta_dir",
            )
            id_grupo_sel = opciones_grupos[etiqueta]

            nombre_dir = st.text_input("Nombre de la directiva", key="dir_nombre")
            dui_dir = st.text_input(
                "DUI de la directiva (con o sin guiones)",
                key="dir_dui",
                max_chars=20,
            )
            pwd = st.text_input(
                "Contraseña para la cuenta de directiva",
                type="password",
                key="dir_pwd",
            )

            if st.button("Guardar nueva directiva para este grupo", type="primary"):
                if not (nombre_dir.strip() and dui_dir.strip() and pwd):
                    st.error("Todos los campos son obligatorios.")
                else:
                    dui_limpio = _limpiar_dui(dui_dir)
                    hoy = date.today()

                    # Encriptar contraseña
                    pwd_hash = bcrypt.hashpw(
                        pwd.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")

                    try:
                        # 1) Crear usuario para la directiva
                        sql_user = """
                            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                            VALUES (%s, %s, %s, %s)
                        """
                        execute(
                            sql_user,
                            (nombre_dir.strip(), dui_limpio, pwd_hash, ID_ROL_DIRECTIVA),
                        )

                        # 2) Insertar en la tabla directiva
                        sql_dir = """
                            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                            VALUES (%s, %s, %s, %s)
                        """
                        execute(
                            sql_dir,
                            (nombre_dir.strip(), dui_limpio, id_grupo_sel, hoy),
                        )

                        st.success("Directiva creada correctamente.")
                        st.experimental_rerun()

                    except Exception as e:
                        st.error(f"Error al crear la directiva: {e}")

    # ╔══════════════════════════════════════════╗
    # ║ TAB 2: LISTAR Y ELIMINAR DIRECTIVAS      ║
    # ╚══════════════════════════════════════════╝
    with tab_baja:
        st.markdown("#### Directivas de tus grupos")

        if not grupos:
            st.info("No tienes grupos asociados todavía.")
            return

        # Directivas solo de grupos donde aparezca el DUI de la promotora
        sql_list = """
            SELECT d.Id_directiva,
                   d.Nombre       AS Nombre_directiva,
                   d.DUI          AS DUI_directiva,
                   d.Id_grupo,
                   g.Nombre       AS Grupo,
                   d.Creado_en
            FROM directiva d
            JOIN grupos g ON g.Id_grupo = d.Id_grupo
            WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
            ORDER BY g.Nombre, d.Nombre
        """
        filas = fetch_all(sql_list, (dui_prom,))

        if not filas:
            st.info("Aún no hay directivas registradas para tus grupos.")
            return

        # Mostrar tabla como la de "Mis grupos"
        df = pd.DataFrame(filas)
        df = df.rename(
            columns={
                "Id_directiva": "Id_directiva",
                "Nombre_directiva": "Nombre",
                "DUI_directiva": "DUI",
                "Grupo": "Grupo",
                "Creado_en": "Creado_en",
            }
        )
        st.dataframe(df, use_container_width=True)

        st.markdown("#### Eliminar una directiva")

        opciones_dir = {
            f"{row['Id_directiva']} - {row['Nombre_directiva']} ({row['Grupo']})":
            row["Id_directiva"]
            for row in filas
        }

        etiqueta_dir = st.selectbox(
            "Selecciona la directiva que deseas eliminar",
            list(opciones_dir.keys()),
            key="sel_directiva_baja",
        )
        id_dir_sel = opciones_dir[etiqueta_dir]

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar esta directiva (incluye su usuario)."
        )

        if st.button(
            "Eliminar directiva seleccionada",
            type="secondary",
            disabled=not confirmar,
        ):
            try:
                # Obtener DUI de la directiva para borrar también el usuario
                sql_dui = "SELECT DUI FROM directiva WHERE Id_directiva = %s"
                fila = fetch_all(sql_dui, (id_dir_sel,))
                dui_borrar = fila[0]["DUI"] if fila else None

                if dui_borrar:
                    execute("DELETE FROM Usuario WHERE DUI = %s", (dui_borrar,))

                execute("DELETE FROM directiva WHERE Id_directiva = %s", (id_dir_sel,))
                st.success("Directiva eliminada correctamente.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al eliminar la directiva: {e}")
