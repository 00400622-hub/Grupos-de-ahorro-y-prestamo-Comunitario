import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.promotora.directiva import crear_directiva_panel


# ----------------- Helpers comunes ----------------- #

def _get_usuario_actual():
    usuario = st.session_state.get("usuario")
    if not usuario:
        st.error("No hay una sesión activa.")
        st.stop()
    return usuario


def _get_promotora_actual():
    """
    Usa el DUI del usuario logueado para buscar su fila en la tabla 'promotora'.
    """
    usuario = _get_usuario_actual()
    dui = usuario["DUI"]

    promotora = fetch_one(
        "SELECT Id_promotora, Nombre FROM promotora WHERE DUI = %s",
        (dui,),
    )
    if not promotora:
        st.error(
            f"No se encontró una promotora registrada para el DUI {dui}. "
            "Pida al administrador que revise la tabla 'promotora'."
        )
        st.stop()

    return promotora


# ----------------- Crear grupo ----------------- #

def _crear_grupo():
    st.subheader("Registrar nuevo grupo de ahorro")

    promotora = _get_promotora_actual()
    id_promotora = promotora["Id_promotora"]
    usuario = _get_usuario_actual()
    dui_prom = usuario["DUI"]

    # Distritos disponibles
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )
    if not distritos:
        st.error(
            "No hay distritos registrados. "
            "El administrador debe crearlos primero en su panel."
        )
        return

    opciones_distrito = [
        (d["Id_distrito"], d["Nombre"]) for d in distritos
    ]

    with st.form("form_crear_grupo"):
        nombre = st.text_input("Nombre del grupo")
        id_distrito_sel = st.selectbox(
            "Distrito al que pertenece el grupo",
            options=[d[0] for d in opciones_distrito],
            format_func=lambda did: next(
                etiqueta for (idd, etiqueta) in opciones_distrito if idd == did
            ),
        )

        crear = st.form_submit_button("Crear grupo")

    if not crear:
        return

    if not nombre.strip():
        st.warning("Debes ingresar un nombre para el grupo.")
        return

    # Verificar que la promotora no tenga YA un grupo con ese nombre en ese distrito
    ya_existe = fetch_one(
        """
        SELECT Id_grupo
        FROM grupos
        WHERE Nombre = %s
          AND Id_distrito = %s
          AND Id_promotora = %s
        """,
        (nombre.strip(), id_distrito_sel, id_promotora),
    )
    if ya_existe:
        st.error(
            "Ya existe un grupo con ese nombre en ese distrito creado por esta promotora. "
            "Use otro nombre o revise la pestaña 'Mis grupos'."
        )
        return

    try:
        execute(
            """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado, Creado_por, Creado_en,
                 Id_promotora, DUIs_promotoras)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nombre.strip(),
                id_distrito_sel,
                "ACTIVO",
                id_promotora,           # usamos Id_promotora como 'Creado_por'
                date.today(),
                id_promotora,
                dui_prom,               # guardamos el DUI de la promotora creadora
            ),
        )
        st.success("Grupo creado correctamente.")
    except IntegrityError as e:
        st.error("Error de integridad al crear el grupo.")
        st.exception(e)
    except Exception as e:
        st.error("Ocurrió un error inesperado al crear el grupo.")
        st.exception(e)


# ----------------- Mis grupos + eliminar ----------------- #

def _mis_grupos():
    st.subheader("Listado de grupos de la promotora")

    promotora = _get_promotora_actual()
    id_promotora = promotora["Id_promotora"]

    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en
        FROM grupos g
        JOIN distritos d ON g.Id_distrito = d.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo ASC
        """,
        (id_promotora,),
    )

    if not grupos:
        st.info("Todavía no tiene grupos registrados.")
    else:
        st.table(grupos)

    st.markdown("---")
    st.subheader("Eliminar grupo")

    if not grupos:
        st.info("No hay grupos para eliminar.")
        return

    opciones = [
        (g["Id_grupo"], f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})")
        for g in grupos
    ]

    id_grupo_sel = st.selectbox(
        "Seleccione el grupo a eliminar",
        options=[g[0] for g in opciones],
        format_func=lambda gid: next(
            etiqueta for (idg, etiqueta) in opciones if idg == gid
        ),
    )

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
    )

    if st.button("Eliminar grupo"):
        if not confirmar:
            st.warning("Debe marcar la casilla de confirmación antes de eliminar.")
            return

        try:
            execute(
                "DELETE FROM grupos WHERE Id_grupo = %s AND Id_promotora = %s",
                (id_grupo_sel, id_promotora),
            )
            st.success(
                "Grupo eliminado correctamente. "
                "Actualice la página para ver los cambios en la tabla."
            )
        except IntegrityError as e:
            st.error(
                "No se pudo eliminar el grupo por restricciones de integridad. "
                "Revise si el grupo tiene información relacionada en otras tablas."
            )
            st.exception(e)
        except Exception as e:
            st.error("Ocurrió un error inesperado al eliminar el grupo.")
            st.exception(e)


# ----------------- Panel principal de PROMOTORA ----------------- #

def promotora_panel():
    """
    Función que debe llamar el router cuando el rol del usuario es PROMOTORA.
    Muestra las pestañas: Crear grupo, Mis grupos, Crear Directiva, Reportes.
    """
    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    # Pestaña 0: crear grupo
    with tabs[0]:
        _crear_grupo()

    # Pestaña 1: ver / eliminar grupos
    with tabs[1]:
        _mis_grupos()

    # Pestaña 2: crear usuario de directiva
    with tabs[2]:
        crear_directiva_panel()

    # Pestaña 3: placeholder para futuros reportes
    with tabs[3]:
        st.info("Módulo de reportes en construcción.")
