import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.promotora.directiva import crear_directiva_panel


# ----------------- Helpers comunes ----------------- #

def _get_usuario_actual():
    """Devuelve el diccionario de usuario guardado en sesión."""
    return st.session_state.get("usuario")


def _get_promotora_actual():
    """
    Devuelve el registro de la promotora asociada al usuario logueado
    (usando el DUI del usuario).
    """
    user = _get_usuario_actual()
    if not user:
        return None

    dui = user.get("DUI")
    if not dui:
        return None

    prom = fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s",
        (dui,),
    )
    return prom


def _cargar_distritos():
    """Devuelve la lista de distritos (Id_distrito, Nombre)."""
    return fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Id_distrito ASC"
    )


# ----------------- Pestaña: Crear grupo ----------------- #

def _crear_grupo():
    st.header("Crear grupo")

    # 1. Validar promotora actual
    promotora = _get_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI de este usuario exista en la tabla 'promotora'."
        )
        return

    id_promotora = promotora["Id_promotora"]
    dui_promotora = promotora["DUI"]

    st.info(
        f"Sesión de promotora: **{promotora['Nombre']}** "
        f"(DUI: {dui_promotora}, Id_promotora: {id_promotora})"
    )

    # 2. Cargar distritos
    distritos = _cargar_distritos()
    if not distritos:
        st.warning(
            "No hay distritos registrados todavía. "
            "Pide al administrador que cree los distritos primero."
        )
        return

    opciones_distrito = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }

    # 3. Formulario
    with st.form("form_crear_grupo"):
        nombre = st.text_input("Nombre del grupo")
        etiqueta_dist = st.selectbox(
            "Distrito al que pertenece el grupo",
            list(opciones_distrito.keys())
        )
        id_distrito = opciones_distrito[etiqueta_dist]

        crear_btn = st.form_submit_button("Crear grupo")

    if not crear_btn:
        return

    if not nombre.strip():
        st.error("El nombre del grupo es obligatorio.")
        return

    hoy = date.today()
    usuario = _get_usuario_actual()
    id_usuario = usuario.get("Id_usuario") if usuario else None

    # 4. Insertar grupo
    try:
        sql = """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado, Creado_por, Creado_en,
                 Id_promotora, DUIs_promotoras)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # DUIs_promotoras: empezamos con el DUI de esta promotora
        gid = execute(
            sql,
            (
                nombre.strip(),
                id_distrito,
                "ACTIVO",
                id_usuario,
                hoy,
                id_promotora,
                dui_promotora,
            ),
        )
    except IntegrityError:
        # Por si tienes un UNIQUE (Nombre, Id_distrito)
        st.error(
            "Ya existe un grupo con ese nombre en el mismo distrito. "
            "Elige otro nombre o distrito."
        )
        return

    st.success(
        f"Grupo creado correctamente (Id_grupo={gid}) "
        f"en el distrito {etiqueta_dist}."
    )


# ----------------- Pestaña: Mis grupos ----------------- #

def _mis_grupos():
    st.header("Mis grupos")

    promotora = _get_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI exista en la tabla 'promotora'."
        )
        return

    id_promotora = promotora["Id_promotora"]
    dui_promotora = promotora["DUI"]

    st.caption(
        f"Mostrando grupos donde esta promotora está asociada "
        f"(Id_promotora={id_promotora}, DUI {dui_promotora})."
    )

    # Filtrado por Id_promotora (grupos creados por ella)
    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               g.DUIs_promotoras
        FROM grupos g
        JOIN distritos d ON g.Id_distrito = d.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo ASC
        """,
        (id_promotora,),
    )

    if not grupos:
        st.info("Todavía no tienes grupos registrados.")
        return

    # Mostrar tabla
    st.subheader("Listado de grupos")
    st.table(grupos)

    # ------------ Sección para eliminar grupo ------------ #
    st.subheader("Eliminar grupo")

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    etiqueta_sel = st.selectbox(
        "Seleccione el grupo a eliminar",
        list(opciones_grupo.keys())
    )
    id_grupo_sel = opciones_grupo[etiqueta_sel]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
    )

    if st.button("Eliminar grupo"):
        if not confirmar:
            st.warning("Marca la casilla de confirmación antes de eliminar.")
            return

        # Podrías validar que no haya registros dependientes (directiva, etc.)
        execute("DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_sel,))
        st.success(f"Grupo {etiqueta_sel} eliminado correctamente.")
        st.experimental_rerun()


# ----------------- Pestaña: Reportes (placeholder) ----------------- #

def _reportes_promotora():
    st.header("Reportes de promotora")
    st.info(
        "Aquí puedes implementar más adelante reportes por distrito, "
        "cantidad de grupos, etc. De momento es solo un espacio reservado."
    )


# ----------------- Panel principal de promotora ----------------- #

def promotora_panel():
    """
    Panel principal que se llama desde app.py cuando el rol es PROMOTORA.
    Muestra las pestañas:
      - Crear grupo
      - Mis grupos
      - Crear Directiva
      - Reportes
    """
    st.title("Panel de Promotora")

    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with tabs[0]:
        _crear_grupo()

    with tabs[1]:
        _mis_grupos()

    with tabs[2]:
        # 👉 Llamamos al panel para crear usuarios de directiva
        crear_directiva_panel()

    with tabs[3]:
        _reportes_promotora()
