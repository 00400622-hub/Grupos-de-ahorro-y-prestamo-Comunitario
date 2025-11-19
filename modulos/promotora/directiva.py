# modulos/promotora/directiva.py

import datetime as dt
import mysql.connector
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import get_user


# -------------------------------------------------
# Utilidades
# -------------------------------------------------
def _promotora_actual_por_dui(dui: str) -> dict | None:
    """Fila de la tabla promotora para el DUI dado."""
    return fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s LIMIT 1",
        (dui,),
    )


def _grupos_de_promotora_por_dui(dui_prom: str):
    """Grupos donde el DUI aparece en DUIs_promotoras."""
    sql = """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Id_grupo
    """
    return fetch_all(sql, (dui_prom,))


def _obtener_id_rol_directiva() -> int | None:
    fila = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
    )
    return fila["Id_rol"] if fila else None


# -------------------------------------------------
# Panel de creación / gestión de directiva
# -------------------------------------------------
def crear_directiva_panel():
    """
    Vista para que la PROMOTORA:
      - elija uno de sus grupos
      - pueda CREAR cuentas de directiva para ese grupo
      - pueda ELIMINAR directivas ya existentes
    """
    user = get_user()
    dui_prom = (user.get("DUI") or "").strip()

    prom_row = _promotora_actual_por_dui(dui_prom)
    if not prom_row:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    st.subheader("Crear y gestionar directiva de grupo")

    # 1) Seleccionar grupo de esta promotora
    grupos = _grupos_de_promotora_por_dui(dui_prom)
    if not grupos:
        st.info("Aún no tienes grupos asignados para crear directiva.")
        return

    opciones_grupos = {
        f'{g["Id_grupo"]} - {g["Nombre"]} ({g["Distrito"]})': g["Id_grupo"]
        for g in grupos
    }

    etiqueta_sel = st.selectbox(
        "Selecciona el grupo para gestionar su directiva",
        list(opciones_grupos.keys()),
    )
    id_grupo_sel = opciones_grupos[etiqueta_sel]

    st.markdown("---")

    # 2) Mostrar directivas existentes de ese grupo
    directivas = fetch_all(
        """
        SELECT Id_directiva, Nombre, DUI, Id_grupo, Creado_en
        FROM directiva
        WHERE Id_grupo = %s
        ORDER BY Id_directiva
        """,
        (id_grupo_sel,),
    )

    st.write("### Directiva(s) actual(es) del grupo seleccionado")
    if directivas:
        st.table(directivas)
    else:
        st.info("Este grupo aún no tiene directivas registradas.")

    st.markdown("---")

    # 3) CREAR nueva directiva para este grupo
    st.write("### Crear nueva directiva para este grupo")

    nombre_dir = st.text_input("Nombre de la directiva")
    dui_dir = st.text_input("DUI de la directiva")
    contrasenia_dir = st.text_input("Contraseña para la cuenta de directiva", type="password")

    if st.button("Guardar nueva directiva para este grupo"):
        if not (nombre_dir.strip() and dui_dir.strip() and contrasenia_dir.strip()):
            st.warning("Debes completar nombre, DUI y contraseña.")
        else:
            id_rol_dir = _obtener_id_rol_directiva()
            if not id_rol_dir:
                st.error(
                    "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                    "Configúralo primero en la base de datos."
                )
                return

            dui_normalizado = dui_dir.strip()

            # Verificamos si ya existe un usuario con ese DUI
            existe_usr = fetch_one(
                "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
                (dui_normalizado,),
            )
            if existe_usr:
                st.error(
                    "Ya existe un usuario con ese DUI. Usa otro DUI "
                    "o elimina primero la cuenta existente si corresponde."
                )
                return

            hoy = dt.date.today()

            try:
                # 1) Crear usuario con rol DIRECTIVA
                id_usuario = execute(
                    """
                    INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre_dir.strip(), dui_normalizado, contrasenia_dir.strip(), id_rol_dir),
                    return_last_id=True,
                )

                # 2) Crear registro en tabla directiva
                execute(
                    """
                    INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre_dir.strip(), dui_normalizado, id_grupo_sel, hoy),
                )

                st.success(
                    f"Directiva creada correctamente para el grupo "
                    f"({etiqueta_sel}). Id_usuario = {id_usuario}."
                )
                st.experimental_rerun()

            except mysql.connector.Error as err:
                st.error(
                    f"Error al crear la directiva: {err.errno} - {err.msg}"
                )

    st.markdown("---")

    # 4) ELIMINAR directiva(s) de este grupo
    st.write("### Eliminar una directiva de este grupo")

    if not directivas:
        st.info("No hay directivas para eliminar en este grupo.")
        return

    opciones_dir = {
        f'{d["Id_directiva"]} - {d["Nombre"]} (DUI: {d["DUI"]})': d
        for d in directivas
    }

    etiqueta_dir_sel = st.selectbox(
        "Selecciona la directiva a eliminar",
        list(opciones_dir.keys()),
        key="select_directiva_eliminar",
    )
    dir_sel = opciones_dir[etiqueta_dir_sel]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar esta directiva y su cuenta de usuario.",
        key="chk_confirma_eliminar_directiva",
    )

    if st.button("Eliminar directiva seleccionada"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación para eliminar.")
            return

        try:
            # Borramos de tabla directiva
            execute(
                "DELETE FROM directiva WHERE Id_directiva = %s",
                (dir_sel["Id_directiva"],),
            )

            # Borramos también al usuario con ese DUI y rol DIRECTIVA (si existe)
            id_rol_dir = _obtener_id_rol_directiva()
            if id_rol_dir:
                execute(
                    "DELETE FROM Usuario WHERE DUI = %s AND Id_rol = %s",
                    (dir_sel["DUI"], id_rol_dir),
                )

            st.success("Directiva eliminada correctamente.")
            st.experimental_rerun()

        except mysql.connector.Error as err:
            st.error(
                f"Error al eliminar la directiva: {err.errno} - {err.msg}"
            )
