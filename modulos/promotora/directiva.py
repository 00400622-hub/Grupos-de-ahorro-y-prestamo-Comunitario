# modulos/promotora/directiva.py
import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def _promotora_actual():
    """Obtiene la promotora actual a partir del usuario en sesión."""
    user = get_user()
    if not user:
        return None

    return fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s LIMIT 1",
        (user["DUI"],),
    )


def _id_rol_directiva():
    """Devuelve el Id_rol correspondiente al rol DIRECTIVA."""
    fila = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
    )
    return fila["Id_rol"] if fila else None


def _crear_usuario_y_directiva(nombre, dui, contrasenia, id_grupo):
    """
    Crea (o actualiza) el usuario de DIRECTIVA y luego inserta una fila en la tabla directiva.
    Permite tener varias directivas en el mismo grupo.
    """
    id_rol_dir = _id_rol_directiva()
    if not id_rol_dir:
        raise RuntimeError(
            "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
            "Crea ese rol primero."
        )

    # ¿Ya existe un usuario con ese DUI?
    existente = fetch_one("SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1", (dui,))
    if existente:
        id_usuario = existente["Id_usuario"]
        # Actualizamos nombre, contraseña y rol por si cambian
        execute(
            """
            UPDATE Usuario
            SET Nombre = %s,
                Contraseña = %s,
                Id_rol = %s
            WHERE Id_usuario = %s
            """,
            (nombre, contrasenia, id_rol_dir, id_usuario),
        )
    else:
        # Creamos usuario nuevo
        id_usuario = execute(
            """
            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, dui, contrasenia, id_rol_dir),
            return_last_id=True,
        )

    # Insertamos la directiva (PUEDEN existir varias directivas por grupo)
    hoy = dt.date.today()
    execute(
        """
        INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre, dui, id_grupo, hoy),
    )


# -------------------------------------------------------
# Panel de creación / gestión de directivas
# -------------------------------------------------------
@require_auth
@has_role("PROMOTORA")
def crear_directiva_panel():
    st.subheader("Crear y gestionar directivas de grupo")

    prom = _promotora_actual()
    if not prom:
        st.error(
            "No se encontró una promotora asociada al usuario actual. "
            "Verifica la tabla 'promotora'."
        )
        return

    dui_prom = prom["DUI"]

    # Grupos donde aparece el DUI de la promotora
    grupos = fetch_all(
        """
        SELECT Id_grupo, Nombre
        FROM grupos
        WHERE FIND_IN_SET(%s, DUIs_promotoras) > 0
        ORDER BY Nombre
        """,
        (dui_prom,),
    )

    if not grupos:
        st.info("Todavía no tienes grupos asignados para gestionar directivas.")
        return

    opciones_grupo = {
        f'{g["Id_grupo"]} - {g["Nombre"]}': g["Id_grupo"] for g in grupos
    }

    tab_crear, tab_eliminar = st.tabs(
        ["➕ Agregar directiva a un grupo", "🗑 Eliminar directiva de un grupo"]
    )

    # ---------------------------------------------------
    # TAB 1: Agregar directiva (pueden ser varias por grupo)
    # ---------------------------------------------------
    with tab_crear:
        st.write("### Agregar nueva directiva a uno de tus grupos")

        etiqueta_grupo = st.selectbox(
            "Selecciona el grupo",
            list(opciones_grupo.keys()),
            key="dir_crear_grupo",
        )
        id_grupo_sel = opciones_grupo[etiqueta_grupo]

        nombre_dir = st.text_input(
            "Nombre de la directiva",
            key="dir_crear_nombre",
        )
        dui_dir = st.text_input(
            "DUI de la directiva",
            key="dir_crear_dui",
        )
        contr_dir = st.text_input(
            "Contraseña para la cuenta de directiva",
            type="password",
            key="dir_crear_contrasenia",
        )

        if st.button("Guardar directiva", type="primary", key="btn_dir_crear"):
            if not (nombre_dir.strip() and dui_dir.strip() and contr_dir.strip()):
                st.warning("Completa todos los campos antes de guardar.")
            else:
                try:
                    _crear_usuario_y_directiva(
                        nombre_dir.strip(),
                        dui_dir.strip(),
                        contr_dir.strip(),
                        id_grupo_sel,
                    )
                    st.success("Directiva creada correctamente.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al crear la directiva: {e}")

    # ---------------------------------------------------
    # TAB 2: Eliminar directiva
    # ---------------------------------------------------
    with tab_eliminar:
        st.write("### Eliminar directiva de un grupo")

        etiqueta_grupo2 = st.selectbox(
            "Selecciona el grupo",
            list(opciones_grupo.keys()),
            key="dir_eliminar_grupo",
        )
        id_grupo2 = opciones_grupo[etiqueta_grupo2]

        directivas = fetch_all(
            """
            SELECT Id_directiva, Nombre, DUI
            FROM directiva
            WHERE Id_grupo = %s
            ORDER BY Nombre
            """,
            (id_grupo2,),
        )

        if not directivas:
            st.info("Ese grupo todavía no tiene directivas registradas.")
            return

        opciones_dir = {
            f'{d["Nombre"]} — {d["DUI"]} (Id {d["Id_directiva"]})': d["Id_directiva"]
            for d in directivas
        }

        etiqueta_dir = st.selectbox(
            "Selecciona la directiva a eliminar",
            list(opciones_dir.keys()),
            key="dir_eliminar_select",
        )
        id_dir_sel = opciones_dir[etiqueta_dir]

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar esta directiva del grupo.",
            key="dir_eliminar_confirmar",
        )

        if st.button("Eliminar directiva", key="btn_dir_eliminar"):
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                try:
                    execute(
                        "DELETE FROM directiva WHERE Id_directiva = %s",
                        (id_dir_sel,),
                    )
                    st.success("Directiva eliminada correctamente.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al eliminar la directiva: {e}")
