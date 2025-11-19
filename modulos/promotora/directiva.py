# modulos/promotora/directiva.py

import datetime as dt
import streamlit as st
import bcrypt

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import get_user


# -------------------------------------------------------------------
#   Helpers
# -------------------------------------------------------------------

def _get_id_rol_directiva() -> int | None:
    """Devuelve el Id_rol para DIRECTIVA (según la tabla 'rol')."""
    fila = fetch_one("SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1")
    return fila["Id_rol"] if fila else None


def _normalizar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _grupos_de_promotora_actual():
    """Grupos donde la promotora logueada está asignada en DUIs_promotoras."""
    user = get_user()
    dui = _normalizar_dui(user.get("DUI", ""))

    if not dui:
        return []

    return fetch_all(
        """
        SELECT g.Id_grupo, g.Nombre
        FROM grupos g
        WHERE FIND_IN_SET(%s, COALESCE(g.DUIs_promotoras, '')) > 0
        ORDER BY g.Nombre
        """,
        (dui,),
    )


def _grupos_sin_directiva_para_promotora():
    """Grupos de la promotora actual que aún NO tienen ninguna directiva."""
    grupos = _grupos_de_promotora_actual()
    if not grupos:
        return []

    ids = [g["Id_grupo"] for g in grupos]
    placeholders = ",".join(["%s"] * len(ids))

    sql = f"""
        SELECT g.Id_grupo, g.Nombre
        FROM grupos g
        LEFT JOIN directiva d ON d.Id_grupo = g.Id_grupo
        WHERE g.Id_grupo IN ({placeholders})
          AND d.Id_grupo IS NULL
        ORDER BY g.Nombre
    """
    return fetch_all(sql, tuple(ids))


def _hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


# -------------------------------------------------------------------
#   Pantalla de Directivas
# -------------------------------------------------------------------

def crear_directiva_panel():
    """
    Panel dentro del Panel de Promotora para:
    - Crear la primera directiva de un grupo
    - Agregar nuevas directivas a un grupo ya existente
    - Eliminar directivas existentes
    """

    st.subheader("Gestión de directiva de grupo")

    id_rol_dir = _get_id_rol_directiva()
    if not id_rol_dir:
        st.error("No se encontró el rol 'DIRECTIVA' en la tabla 'rol'.")
        return

    grupos_prom = _grupos_de_promotora_actual()
    if not grupos_prom:
        st.info("No tienes grupos asignados todavía.")
        return

    tab_crear, tab_gestionar = st.tabs(
        ["➕ Crear primera directiva del grupo", "👥 Agregar / eliminar directivas"]
    )

    # ------------------------------------------------------------------
    # 1) Crear PRIMERA directiva de un grupo que aún no tiene
    # ------------------------------------------------------------------
    with tab_crear:
        st.markdown("### Crear primera directiva del grupo")

        grupos_sin_dir = _grupos_sin_directiva_para_promotora()
        if not grupos_sin_dir:
            st.info("Todos tus grupos ya tienen al menos una directiva registrada.")
        else:
            opciones = {
                f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos_sin_dir
            }
            label_grupo = st.selectbox(
                "Selecciona el grupo", list(opciones.keys()), key="sel_grupo_sin_dir"
            )
            id_grupo_sel = opciones[label_grupo]

            nombre_dir = st.text_input("Nombre de la directiva")
            dui_dir = st.text_input("DUI de la directiva")
            pwd_dir = st.text_input(
                "Contraseña para la cuenta de directiva", type="password"
            )

            if st.button("Guardar directiva para este grupo"):
                if not (nombre_dir.strip() and dui_dir.strip() and pwd_dir.strip()):
                    st.warning("Completa todos los campos.")
                else:
                    dui_norm = _normalizar_dui(dui_dir)
                    hoy = dt.date.today()

                    try:
                        # 1) Crear usuario
                        hash_pwd = _hash_password(pwd_dir)
                        id_usuario = execute(
                            """
                            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (nombre_dir.strip(), dui_norm, hash_pwd, id_rol_dir),
                            return_last_id=True,
                        )

                        # 2) Crear directiva ligada al grupo
                        execute(
                            """
                            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (nombre_dir.strip(), dui_norm, id_grupo_sel, hoy),
                        )

                        st.success(
                            f"Directiva creada correctamente para el grupo {label_grupo}. "
                            f"(Id_usuario={id_usuario})"
                        )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error al crear la directiva: {e}")

    # ------------------------------------------------------------------
    # 2) Agregar / Eliminar directivas para un grupo
    # ------------------------------------------------------------------
    with tab_gestionar:
        st.markdown("### Agregar o eliminar directivas de un grupo")

        # Selector de grupo (cualquiera de la promotora)
        opciones = {
            f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos_prom
        }
        label_grupo2 = st.selectbox(
            "Selecciona el grupo a gestionar", list(opciones.keys()), key="sel_grupo_gestion"
        )
        id_grupo_gest = opciones[label_grupo2]

        # Directivas ya existentes del grupo
        directivas = fetch_all(
            """
            SELECT Id_directiva, Nombre, DUI, Creado_en
            FROM directiva
            WHERE Id_grupo = %s
            ORDER BY Id_directiva
            """,
            (id_grupo_gest,),
        )

        if not directivas:
            st.info("Este grupo aún no tiene directivas registradas.")
        else:
            st.write("#### Directivas actuales del grupo")
            st.table(directivas)

        st.write("---")
        st.markdown("#### Agregar nueva directiva a este grupo")

        nombre_dir2 = st.text_input(
            "Nombre de la nueva directiva", key="nombre_dir_extra"
        )
        dui_dir2 = st.text_input("DUI de la nueva directiva", key="dui_dir_extra")
        pwd_dir2 = st.text_input(
            "Contraseña para la nueva cuenta de directiva",
            type="password",
            key="pwd_dir_extra",
        )

        if st.button("Guardar nueva directiva para este grupo"):
            if not (nombre_dir2.strip() and dui_dir2.strip() and pwd_dir2.strip()):
                st.warning("Completa todos los campos para la nueva directiva.")
            else:
                dui_norm2 = _normalizar_dui(dui_dir2)
                hoy = dt.date.today()
                try:
                    hash_pwd2 = _hash_password(pwd_dir2)

                    # Usuario
                    id_usuario2 = execute(
                        """
                        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (nombre_dir2.strip(), dui_norm2, hash_pwd2, id_rol_dir),
                        return_last_id=True,
                    )

                    # Directiva asociada
                    execute(
                        """
                        INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (nombre_dir2.strip(), dui_norm2, id_grupo_gest, hoy),
                    )

                    st.success(
                        f"Nueva directiva agregada al grupo {label_grupo2}. "
                        f"(Id_usuario={id_usuario2})"
                    )
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al crear la nueva directiva: {e}")

        st.write("---")
        st.markdown("#### Eliminar directiva del grupo")

        if not directivas:
            st.info("No hay directivas para eliminar en este grupo.")
        else:
            opciones_dir = {
                f"{d['Id_directiva']} - {d['Nombre']} ({d['DUI']})": d["Id_directiva"]
                for d in directivas
            }
            label_dir_del = st.selectbox(
                "Selecciona la directiva a eliminar",
                list(opciones_dir.keys()),
                key="dir_a_eliminar",
            )
            id_dir_del = opciones_dir[label_dir_del]

            confirmar = st.checkbox(
                "Confirmo que deseo eliminar esta directiva (no se puede deshacer).",
                key="chk_eliminar_dir",
            )

            if st.button("Eliminar directiva seleccionada"):
                if not confirmar:
                    st.warning("Debes marcar la casilla de confirmación.")
                else:
                    try:
                        # Obtener DUI para borrar también el usuario, si existe
                        fila_dir = fetch_one(
                            "SELECT DUI FROM directiva WHERE Id_directiva = %s",
                            (id_dir_del,),
                        )
                        dui_borrar = fila_dir["DUI"] if fila_dir else None

                        execute(
                            "DELETE FROM directiva WHERE Id_directiva = %s",
                            (id_dir_del,),
                        )

                        if dui_borrar:
                            execute(
                                "DELETE FROM Usuario WHERE DUI = %s AND Id_rol = %s",
                                (dui_borrar, id_rol_dir),
                            )

                        st.success("Directiva eliminada correctamente.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error al eliminar la directiva: {e}")
