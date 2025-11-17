import streamlit as st
from datetime import date

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, current_user


# ----------------- helpers básicos ----------------- #

def _solo_promotora():
    """Restringe el acceso solo a usuarios con rol PROMOTORA."""
    require_auth()
    if not has_role("PROMOTORA"):
        st.error("Acceso restringido a Promotoras.")
        st.stop()


def _titulo(txt: str):
    st.markdown(f"## {txt}")


# ----------------- CREAR GRUPO ----------------- #

def _crear_grupo():
    _titulo("Crear grupo")
    st.caption("Registrar un nuevo grupo de ahorro en un distrito.")

    # Cargar distritos creados por el Administrador
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre"
    )

    if not distritos:
        st.warning(
            "No hay distritos registrados. "
            "Pida al Administrador que cree al menos un distrito."
        )
        return

    opciones = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }

    with st.form("form_crear_grupo", clear_on_submit=True):
        nombre = st.text_input("Nombre del grupo")
        sel_dist = st.selectbox(
            "Distrito al que pertenece el grupo",
            list(opciones.keys())
        )
        enviar = st.form_submit_button("Crear grupo")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Debe ingresar el nombre del grupo.")
                return

            id_distrito = opciones[sel_dist]

            # evitar duplicado: mismo nombre en el mismo distrito
            existe = fetch_one(
                """
                SELECT Id_grupo
                FROM grupos
                WHERE LOWER(Nombre) = LOWER(%s)
                  AND Id_distrito = %s
                LIMIT 1
                """,
                (nom, id_distrito),
            )
            if existe:
                st.error("Ya existe un grupo con ese nombre en ese distrito.")
                return

            usuario = current_user()
            creado_por = usuario.get("Id_usuario") if usuario else None
            hoy = date.today()

            sql = """
                INSERT INTO grupos (Nombre, Id_distrito, Estado, Creado_por, Creado_en)
                VALUES (%s, %s, %s, %s, %s)
            """
            _, gid = execute(sql, (nom, id_distrito, "ACTIVO", creado_por, hoy))
            st.success(f"Grupo creado correctamente (Id_grupo={gid}).")


# ----------------- MIS GRUPOS (listar + eliminar) ----------------- #

def _mis_grupos():
    _titulo("Mis grupos")

    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en
        FROM grupos g
        LEFT JOIN distritos d ON d.Id_distrito = g.Id_distrito
        ORDER BY g.Id_grupo DESC
        """
    )

    if not grupos:
        st.info("Todavía no hay grupos registrados.")
        return

    st.subheader("Listado de grupos")
    st.dataframe(grupos, use_container_width=True)

    st.markdown("### Eliminar grupo")

    # opciones para el select
    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito'] or 'SIN DISTRITO'})": g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_eliminar_grupo"):
        sel = st.selectbox(
            "Seleccione el grupo a eliminar",
            list(opciones_grupo.keys())
        )
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar grupo", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                id_sel = opciones_grupo[sel]
                try:
                    sql = "DELETE FROM grupos WHERE Id_grupo = %s"
                    filas, _ = execute(sql, (id_sel,))
                    if filas > 0:
                        st.success(f"Grupo {sel} eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("No se encontró el grupo seleccionado.")
                except Exception as e:
                    # Si luego pones FKs desde otras tablas, aquí podrías
                    # capturar mysql.connector.IntegrityError específicamente
                    st.error(
                        "No se puede eliminar el grupo porque está siendo usado "
                        "por otros registros."
                    )
                    st.exception(e)


# ----------------- CREAR DIRECTIVA (placeholder) ----------------- #

def _crear_directiva():
    _titulo("Crear Directiva")
    st.info("Aquí luego podemos implementar la creación de la directiva del grupo.")


# ----------------- REPORTES (placeholder) ----------------- #

def _reportes():
    _titulo("Reportes")
    st.info("Aquí podrás ver o descargar reportes de los grupos.")


# ----------------- PANEL PRINCIPAL DE PROMOTORA ----------------- #

def promotora_panel():
    _solo_promotora()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"]
    )

    with tab1:
        _crear_grupo()
    with tab2:
        _mis_grupos()
    with tab3:
        _crear_directiva()
    with tab4:
        _reportes()
