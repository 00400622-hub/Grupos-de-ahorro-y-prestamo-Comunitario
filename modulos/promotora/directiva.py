# modulos/promotora/directiva.py
from datetime import date

import streamlit as st
import pandas as pd  # <-- NUEVO

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import get_user


def _do_rerun():
    """Rerun compatible para distintas versiones de Streamlit."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def _cargar_grupos_promotora(dui_promotora: str):
    """
    Devuelve los grupos donde el DUI de la promotora aparece en DUIs_promotoras.
    """
    return fetch_all(
        """
        SELECT g.Id_grupo, g.Nombre
        FROM grupos g
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras) > 0
        ORDER BY g.Nombre
        """,
        (dui_promotora,),
    )


def _id_rol_directiva() -> int | None:
    """
    Devuelve el Id_rol asociado al rol DIRECTIVA.
    """
    row = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
    )
    return row["Id_rol"] if row else None


def crear_directiva_panel():
    """
    Panel dentro del modo PROMOTORA para:

    - Crear NUEVAS cuentas de directiva para un grupo (puede haber varias).
    - Eliminar directivas de un grupo.
    """
    user = get_user()
    if not user:
        st.error("No hay una sesión activa.")
        return

    dui_prom = (user.get("DUI") or "").strip()

    st.subheader("Creación y gestión de directivas de grupo")
    st.caption(f"Promotora actual: **{user['Nombre']}** — DUI: **{dui_prom}**")

    # ==============================
    #   Cargar grupos de la promotora
    # ==============================
    grupos = _cargar_grupos_promotora(dui_prom)
    if not grupos:
        st.info("Todavía no tienes grupos asignados.")
        return

    opciones_grupos = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos
    }

    # =========================================================
    #  TABLA "MIS DIRECTIVAS" (similar a la de Mis grupos)
    # =========================================================
    directivas_todas = fetch_all(
        """
        SELECT
            d.Id_directiva,
            g.Id_grupo,
            g.Nombre       AS Grupo,
            d.Nombre       AS Directiva,
            d.DUI,
            d.Creado_en
        FROM directiva d
        INNER JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras) > 0
        ORDER BY g.Id_grupo, d.Nombre
        """,
        (dui_prom,),
    )

    st.markdown("### Mis directivas")
    if not directivas_todas:
        st.info("Aún no hay directivas registradas en tus grupos.")
    else:
        df_dir = pd.DataFrame(directivas_todas)
        # Orden de columnas parecido al de tu tabla de grupos
        df_dir = df_dir[
            ["Id_directiva", "Id_grupo", "Grupo", "Directiva", "DUI", "Creado_en"]
        ]
        st.dataframe(df_dir, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # PESTAÑAS: CREAR Y ELIMINAR DIRECTIVAS
    # ------------------------------------------------------------------
    tab_crear, tab_eliminar = st.tabs(
        ["➕ Agregar directiva a grupo", "🗑 Eliminar directivas"]
    )

    # ------------------------------------------------------------------
    # TAB 1: CREAR / AGREGAR DIRECTIVA
    # ------------------------------------------------------------------
    with tab_crear:
        st.markdown("### Agregar nueva directiva a un grupo")

        label_sel = st.selectbox(
            "Selecciona el grupo donde se agregará la directiva",
            list(opciones_grupos.keys()),
            key="sel_grupo_directiva_crear",
        )
        id_grupo_sel = opciones_grupos[label_sel]

        nombre_dir = st.text_input(
            "Nombre de la directiva", key="nombre_dir_crear"
        )
        dui_dir_in = st.text_input(
            "DUI de la directiva (con o sin guiones)",
            key="dui_dir_crear",
        )
        password = st.text_input(
            "Contraseña para la cuenta de directiva",
            type="password",
            key="pass_dir_crear",
        )

        if st.button(
            "Guardar nueva directiva para este grupo",
            key="btn_crear_directiva",
        ):
            if not nombre_dir or not dui_dir_in or not password:
                st.warning("Todos los campos son obligatorios.")
            else:
                # Normalizamos DUI (solo dígitos)
                dui_dir = "".join(ch for ch in dui_dir_in if ch.isdigit())

                if len(dui_dir) != 9:
                    st.warning("El DUI debe tener exactamente 9 dígitos.")
                else:
                    id_rol_dir = _id_rol_directiva()
                    if not id_rol_dir:
                        st.error(
                            "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'."
                        )
                    else:
                        # 1) Crear / actualizar usuario en tabla Usuario
                        usu = fetch_one(
                            "SELECT Id_usuario FROM Usuario WHERE DUI = %s",
                            (dui_dir,),
                        )
                        if usu:
                            # Ya existe el usuario → actualizamos nombre, contraseña y rol
                            execute(
                                """
                                UPDATE Usuario
                                SET Nombre = %s,
                                    Contraseña = %s,
                                    Id_rol = %s
                                WHERE Id_usuario = %s
                                """,
                                (
                                    nombre_dir.strip(),
                                    password,
                                    id_rol_dir,
                                    usu["Id_usuario"],
                                ),
                            )
                        else:
                            # No existe → lo creamos
                            execute(
                                """
                                INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (
                                    nombre_dir.strip(),
                                    dui_dir,
                                    password,
                                    id_rol_dir,
                                ),
                                return_last_id=True,
                            )

                        # 2) Insertar registro en tabla directiva (puede haber varias por grupo)
                        hoy = date.today()
                        execute(
                            """
                            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                nombre_dir.strip(),
                                dui_dir,
                                id_grupo_sel,
                                hoy,
                            ),
                        )

                        st.success(
                            "Directiva creada y asociada al grupo correctamente."
                        )
                        _do_rerun()

    # ------------------------------------------------------------------
    # TAB 2: ELIMINAR DIRECTIVAS
    # ------------------------------------------------------------------
    with tab_eliminar:
        st.markdown("### Eliminar directivas de un grupo")

        label_sel2 = st.selectbox(
            "Selecciona el grupo a gestionar",
            list(opciones_grupos.keys()),
            key="sel_grupo_directiva_eliminar",
        )
        id_grupo_sel2 = opciones_grupos[label_sel2]

        directivas = fetch_all(
            """
            SELECT Id_directiva, Nombre, DUI
            FROM directiva
            WHERE Id_grupo = %s
            ORDER BY Nombre
            """,
            (id_grupo_sel2,),
        )

        if not directivas:
            st.info("Este grupo aún no tiene directivas registradas.")
            return

        opciones_dir = {
            f"{d['Nombre']} — DUI {d['DUI']} (Id {d['Id_directiva']})": d[
                "Id_directiva"
            ]
            for d in directivas
        }

        seleccion = st.multiselect(
            "Selecciona las directivas que deseas eliminar",
            list(opciones_dir.keys()),
            key="multiselect_directivas_eliminar",
        )

        ids_seleccionados = [opciones_dir[s] for s in seleccion]

        if st.button(
            "Eliminar directivas seleccionadas", key="btn_eliminar_directivas"
        ):
            if not ids_seleccionados:
                st.warning("No has seleccionado ninguna directiva.")
            else:
                placeholders = ",".join(["%s"] * len(ids_seleccionados))
                execute(
                    f"DELETE FROM directiva WHERE Id_directiva IN ({placeholders})",
                    tuple(ids_seleccionados),
                )
                st.success("Directivas eliminadas correctamente.")
                _do_rerun()
