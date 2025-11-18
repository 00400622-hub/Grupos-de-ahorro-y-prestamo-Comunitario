# modulos/promotora/grupos.py

import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.promotora.directiva import crear_directiva_panel


# -------------------------------------------------------------------
# Helpers de sesión / rol
# -------------------------------------------------------------------
def _get_usuario_actual():
    """Devuelve el usuario logueado desde session_state o detiene la app."""
    usuario = st.session_state.get("usuario")
    if not usuario:
        st.error("No hay una sesión activa.")
        st.stop()
    return usuario


def _solo_promotora():
    """Verifica que el usuario actual sea PROMOTORA."""
    usuario = _get_usuario_actual()
    rol = str(usuario.get("Rol") or usuario.get("rol") or "").upper()
    if rol != "PROMOTORA":
        st.error("Solo las promotoras pueden acceder a este módulo.")
        st.stop()
    return usuario


def _get_promotora_id(usuario):
    """
    Busca el Id_promotora en la tabla promotora usando el DUI del usuario.
    Tabla promotora: Id_promotora, Nombre, DUI
    """
    dui = usuario["DUI"]
    prom = fetch_one(
        "SELECT Id_promotora FROM promotora WHERE DUI = %s",
        (dui,),
    )
    if not prom:
        st.warning(
            "Este usuario todavía no está registrado en la tabla 'promotora'. "
            "Primero debe crearse como promotora desde el módulo de ADMINISTRADOR."
        )
        st.stop()
    return prom["Id_promotora"]


# -------------------------------------------------------------------
# Pantalla: Crear grupo
# -------------------------------------------------------------------
def _crear_grupo(usuario, id_promotora):
    st.subheader("Registrar nuevo grupo")

    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )

    if not distritos:
        st.info("Todavía no hay distritos creados. El administrador debe crearlos primero.")
        return

    opciones = {f'{d["Id_distrito"]} - {d["Nombre"]}': d["Id_distrito"] for d in distritos}

    with st.form("form_crear_grupo"):
        nombre = st.text_input("Nombre del grupo")
        opcion = st.selectbox("Distrito al que pertenece el grupo", list(opciones.keys()))
        enviado = st.form_submit_button("Crear grupo")

    if not enviado:
        return

    if not nombre.strip():
        st.warning("Debes ingresar el nombre del grupo.")
        return

    id_distrito = opciones[opcion]
    hoy = date.today()
    dui_promotora = usuario["DUI"]

    sql = """
        INSERT INTO grupos
            (Nombre, Id_distrito, Estado, Creado_por, Creado_en, Id_promotora, DUIs_promotoras)
        VALUES
            (%s,      %s,         %s,     %s,        %s,        %s,           %s)
    """

    try:
        _, gid = execute(
            sql,
            (
                nombre.strip(),
                id_distrito,
                "ACTIVO",
                usuario["Nombre"],
                hoy,
                id_promotora,
                dui_promotora,
            ),
        )
        st.success(f"✅ Grupo creado correctamente (Id_grupo={gid}).")
    except IntegrityError as e:
        st.error(
            "No se pudo crear el grupo. "
            "Posiblemente ya exista un grupo con ese nombre/ combinación de datos."
        )


# -------------------------------------------------------------------
# Pantalla: Mis grupos (listar + eliminar)
# -------------------------------------------------------------------
def _mis_grupos(id_promotora):
    st.subheader("Mis grupos")

    grupos = fetch_all(
        """
        SELECT
            g.Id_grupo,
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
        st.info("Aún no tienes grupos registrados.")
        return

    st.write("### Listado de grupos")
    st.dataframe(grupos, use_container_width=True)

    # ---- Eliminar grupo ----
    st.write("### Eliminar grupo")
    mapa_opciones = {
        f'{g["Id_grupo"]} - {g["Nombre"]} ({g["Distrito"]})': g["Id_grupo"]
        for g in grupos
    }

    etiqueta = st.selectbox(
        "Seleccione el grupo a eliminar",
        list(mapa_opciones.keys()),
    )
    id_grupo_sel = mapa_opciones[etiqueta]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
    )
    if st.button("Eliminar grupo", type="primary", disabled=not confirmar):
        try:
            execute(
                "DELETE FROM grupos WHERE Id_grupo = %s AND Id_promotora = %s",
                (id_grupo_sel, id_promotora),
            )
            st.success("Grupo eliminado correctamente. Recarga la página para actualizar la tabla.")
        except IntegrityError:
            st.error(
                "No se pudo eliminar el grupo. "
                "Es posible que tenga información relacionada (por ejemplo directiva, reuniones, etc.)."
            )


# -------------------------------------------------------------------
# Panel principal de PROMOTORA
# -------------------------------------------------------------------
def promotora_panel():
    """
    Punto de entrada desde app.router() cuando el rol es PROMOTORA.
    Muestra pestañas:
    - Crear grupo
    - Mis grupos
    - Crear Directiva
    - Reportes
    """
    usuario = _solo_promotora()
    id_promotora = _get_promotora_id(usuario)

    tabs = st.tabs(
        ["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"]
    )

    with tabs[0]:
        _crear_grupo(usuario, id_promotora)

    with tabs[1]:
        _mis_grupos(id_promotora)

    with tabs[2]:
        # Llama al módulo de directiva
        crear_directiva_panel(usuario, id_promotora)

    with tabs[3]:
        st.info("Módulo de reportes para promotora pendiente de implementar.")
