# modulos/promotora/directiva.py
import datetime as dt
import mysql.connector
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# ---------------------------------------
# Utilidades
# ---------------------------------------
def _grupos_de_promotora(dui_promotora: str):
    """
    Devuelve los grupos donde el DUI de la promotora aparece en la columna
    DUIs_promotoras (lista de DUIs separada por comas).
    """
    sql = """
        SELECT Id_grupo, Nombre
        FROM grupos
        WHERE FIND_IN_SET(%s, DUIs_promotoras)
        ORDER BY Nombre
    """
    return fetch_all(sql, (dui_promotora,))


def _id_rol_directiva() -> int | None:
    fila = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
    )
    return fila["Id_rol"] if fila else None


# ---------------------------------------
# Panel de directiva para PROMOTORA
# ---------------------------------------
@require_auth
@has_role("PROMOTORA")
def crear_directiva_panel():
    user = get_user()
    dui_prom = user.get("DUI")
    nombre_prom = user.get("Nombre")

    st.title("Gestión de Directivas")

    st.caption(
        f"Promotora: **{nombre_prom}** — DUI: **{dui_prom}**"
    )

    # ==========================
    # 1. Crear nueva directiva
    # ==========================
    st.subheader("Crear nueva directiva para un grupo")

    grupos = _grupos_de_promotora(dui_prom or "")

    if not grupos:
        st.info(
            "No tienes grupos asignados todavía. "
            "Primero crea/asígnate a un grupo para poder crear directivas."
        )
    else:
        # Mapeo para el select
        opciones_grupos = {
            f'{g["Id_grupo"]} - {g["Nombre"]}': g["Id_grupo"] for g in grupos
        }
        etiqueta_sel = st.selectbox(
            "Grupo al que pertenecerá la directiva",
            list(opciones_grupos.keys()),
        )
        id_grupo_sel = opciones_grupos[etiqueta_sel]

        nombre_dir = st.text_input("Nombre de la persona de la directiva")
        dui_dir = st.text_input("DUI de la directiva")
        contr_dir = st.text_input(
            "Contraseña para el usuario de la directiva", type="password"
        )

        if st.button("Guardar nueva directiva"):
            if not (nombre_dir.strip() and dui_dir.strip() and contr_dir.strip()):
                st.warning("Completa todos los campos para crear la directiva.")
            else:
                id_rol_dir = _id_rol_directiva()
                if not id_rol_dir:
                    st.error(
                        "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                        "Pídele al administrador que lo cree."
                    )
                else:
                    hoy = dt.date.today()
                    try:
                        # 1) Crear usuario para la directiva
                        execute(
                            """
                            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (nombre_dir.strip(), dui_dir.strip(),
                             contr_dir.strip(), id_rol_dir),
                        )

                        # 2) Crear registro en tabla directiva
                        execute(
                            """
                            INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (nombre_dir.strip(), dui_dir.strip(),
                             id_grupo_sel, hoy),
                        )

                        st.success(
                            f"Directiva creada correctamente para el grupo "
                            f"{etiqueta_sel}."
                        )
                        st.experimental_rerun()

                    except mysql.connector.IntegrityError as err:
                        # 1062 = duplicate entry (índice único)
                        if err.errno == 1062:
                            st.error(
                                "Ya existe un usuario o directiva con ese DUI. "
                                "Usa un DUI diferente."
                            )
                        else:
                            st.error(
                                f"Error de integridad en la BD: {err.errno} - {err.msg}"
                            )
                    except mysql.connector.Error as err:
                        st.error(
                            f"Error de base de datos al crear la directiva: "
                            f"{err.errno} - {err.msg}"
                        )

    st.markdown("---")

    # ==========================
    # 2. Listar y eliminar directivas
    # ==========================
    st.subheader("Directivas de mis grupos (agregar/eliminar)")

    # Directivas de los grupos donde participa la promotora
    directivas = fetch_all(
        """
        SELECT
            d.Id_directiva,
            d.Nombre      AS Nombre_directiva,
            d.DUI         AS DUI_directiva,
            g.Id_grupo,
            g.Nombre      AS Nombre_grupo
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Nombre, d.Nombre
        """,
        (dui_prom,),
    )

    if not directivas:
        st.info(
            "Todavía no hay directivas creadas en los grupos donde eres promotora."
        )
        return

    # Mostrar tabla
    st.write("### Directivas registradas")
    st.table([
        {
            "Id_directiva": d["Id_directiva"],
            "Grupo": d["Nombre_grupo"],
            "Nombre": d["Nombre_directiva"],
            "DUI": d["DUI_directiva"],
        }
        for d in directivas
    ])

    # 2.a Eliminar directiva
    st.write("---")
    st.write("#### Eliminar una directiva")

    opciones_directivas = {
        f'{d["Id_directiva"]} - {d["Nombre_directiva"]} '
        f'({d["DUI_directiva"]}) - Grupo: {d["Nombre_grupo"]}': d
        for d in directivas
    }

    etiqueta_dir = st.selectbox(
        "Selecciona la directiva a eliminar",
        list(opciones_directivas.keys()),
    )
    dir_sel = opciones_directivas[etiqueta_dir]

    confirmar_borrado = st.checkbox(
        "Confirmo que deseo eliminar a esta directiva "
        "y su usuario asociado (esta acción no se puede deshacer)."
    )

    if st.button("Eliminar directiva seleccionada"):
        if not confirmar_borrado:
            st.warning("Marca la casilla de confirmación para eliminar.")
        else:
            dui_objetivo = dir_sel["DUI_directiva"]
            id_dir = dir_sel["Id_directiva"]

            try:
                # Borrar registro de directiva
                execute(
                    "DELETE FROM directiva WHERE Id_directiva = %s",
                    (id_dir,),
                )

                # Borrar también el usuario correspondiente (si existe)
                id_rol_dir = _id_rol_directiva()
                if id_rol_dir:
                    execute(
                        """
                        DELETE FROM Usuario
                        WHERE DUI = %s AND Id_rol = %s
                        """,
                        (dui_objetivo, id_rol_dir),
                    )

                st.success("Directiva eliminada correctamente.")
                st.experimental_rerun()

            except mysql.connector.Error as err:
                st.error(
                    f"Error al eliminar la directiva: {err.errno} - {err.msg}"
                )
