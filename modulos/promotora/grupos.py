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


def _promotora_actual():
    """
    Obtiene la promotora actual usando el DUI del usuario logueado.
    Retorna un diccionario con Id_promotora, Nombre, DUI.
    """
    u = current_user()
    if not u:
        st.error("No hay usuario en sesión.")
        st.stop()

    dui = u.get("DUI")
    if not dui:
        st.error("El usuario en sesión no tiene DUI registrado.")
        st.stop()

    prom = fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s LIMIT 1",
        (dui,)
    )
    if not prom:
        st.error(
            f"No se encontró una promotora en la tabla 'promotora' para el DUI {dui}. "
            "Verifique que la promotora esté registrada."
        )
        st.stop()

    return prom  # { "Id_promotora": ..., "Nombre": ..., "DUI": ... }


# ----------------- CREAR GRUPO ----------------- #

def _crear_grupo():
    _titulo("Crear grupo")
    st.caption("Registrar un nuevo grupo de ahorro en un distrito.")

    # promotora actual según DUI
    promotora = _promotora_actual()
    id_promotora = promotora["Id_promotora"]
    dui_prom = promotora["DUI"]

    st.info(f"Promotora actual: **{promotora['Nombre']}** (DUI {dui_prom})")

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

    opciones_dist = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }

    with st.form("form_crear_grupo", clear_on_submit=True):
        nombre = st.text_input("Nombre del grupo")
        sel_dist = st.selectbox(
            "Distrito al que pertenece el grupo",
            list(opciones_dist.keys())
        )
        enviar = st.form_submit_button("Crear grupo")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Debe ingresar el nombre del grupo.")
                return

            id_distrito = opciones_dist[sel_dist]
            hoy = date.today()

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

            sql = """
                INSERT INTO grupos (Nombre, Id_distrito, Estado, Id_promotora, Creado_en)
                VALUES (%s, %s, %s, %s, %s)
            """
            _, gid = execute(sql, (nom, id_distrito, "ACTIVO", id_promotora, hoy))
            st.success(f"Grupo creado correctamente (Id_grupo={gid}).")


# ----------------- MIS GRUPOS (filtrados por promotora) ----------------- #

def _mis_grupos():
    _titulo("Mis grupos")

    promotora = _promotora_actual()
    id_promotora = promotora["Id_promotora"]
    dui_prom = promotora["DUI"]

    st.caption(f"Mostrando solo grupos asignados a la promotora con DUI **{dui_prom}**")

    # Solo grupos de esta promotora (Id_promotora)
    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               p.DUI AS DUI_promotora
        FROM grupos g
        LEFT JOIN distritos d ON d.Id_distrito = g.Id_distrito
        LEFT JOIN promotora p ON p.Id_promotora = g.Id_promotora
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo DESC
        """,
        (id_promotora,)
    )

    if not grupos:
        st.info("Todavía no hay grupos registrados para esta promotora.")
        return

    st.subheader("Listado de mis grupos")
    st.dataframe(grupos, use_container_width=True)

    # ----------------- REASIGNAR GRUPO A OTRA PROMOTORA POR DUI ----------------- #
    st.markdown("### Reasignar grupo a otra promotora (por DUI)")

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_reasignar_grupo"):
        sel_grupo = st.selectbox(
            "Seleccione el grupo a reasignar",
            list(opciones_grupo.keys())
        )
        dui_nuevo = st.text_input(
            "DUI de la nueva promotora (debe existir en la tabla 'promotora')"
        )
        confirmar = st.checkbox(
            "Confirmo que deseo reasignar este grupo a otra promotora."
        )
        reasignar = st.form_submit_button("Reasignar grupo", type="secondary")

        if reasignar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
                return

            dui_nuevo = (dui_nuevo or "").strip()
            if not dui_nuevo:
                st.warning("Debes ingresar el DUI de la nueva promotora.")
                return

            # Buscar nueva promotora por DUI en tabla 'promotora'
            nueva_prom = fetch_one(
                "SELECT Id_promotora, Nombre FROM promotora WHERE DUI = %s LIMIT 1",
                (dui_nuevo,)
            )
            if not nueva_prom:
                st.error(
                    f"No se encontró una promotora con el DUI {dui_nuevo} "
                    "en la tabla 'promotora'."
                )
                return

            id_grupo_sel = opciones_grupo[sel_grupo]
            id_promotora_nueva = nueva_prom["Id_promotora"]

            try:
                sql = "UPDATE grupos SET Id_promotora = %s WHERE Id_grupo = %s"
                filas, _ = execute(sql, (id_promotora_nueva, id_grupo_sel))
                if filas > 0:
                    st.success(
                        f"Grupo reasignado correctamente a la promotora "
                        f"{nueva_prom['Nombre']} (DUI {dui_nuevo})."
                    )
                    st.rerun()
                else:
                    st.warning("No se encontró el grupo seleccionado.")
            except Exception as e:
                st.error(
                    "No se pudo reasignar el grupo por un error en la base de datos."
                )
                st.exception(e)


# ----------------- CREAR DIRECTIVA (placeholder) ----------------- #

def _crear_directiva():
    _titulo("Crear Directiva")
    st.info("Aquí luego podemos implementar la creación de la directiva del grupo.")


# ----------------- REPORTES (placeholder) ----------------- #

def _reportes():
    _titulo("Reportes")
    promotora = _promotora_actual()
    st.info(
        f"Aquí podrás ver o descargar reportes de los grupos asignados a la promotora "
        f"con DUI {promotora['DUI']}."
    )


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
