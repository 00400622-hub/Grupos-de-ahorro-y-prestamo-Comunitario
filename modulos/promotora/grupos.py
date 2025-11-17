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

    usuario = current_user()
    if not usuario:
        st.error("No hay usuario en sesión.")
        st.stop()

    dui = (usuario.get("DUI") or "").strip()
    nombre_usuario = usuario.get("Nombre") or ""

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
        nombre_grupo = st.text_input("Nombre del grupo")

        sel_dist = st.selectbox(
            "Distrito al que pertenece el grupo",
            list(opciones_dist.keys())
        )

        # TERCERA OPCIÓN: usuario (DUI + nombre) solo lectura
        st.text_input(
            "Promotora responsable (DUI)",
            value=f"{dui} - {nombre_usuario}",
            disabled=True
        )

        enviar = st.form_submit_button("Crear grupo")

        if enviar:
            nom = (nombre_grupo or "").strip()
            if not nom:
                st.warning("Debe ingresar el nombre del grupo.")
                return

            if not dui:
                st.error("El usuario actual no tiene DUI registrado.")
                return

            id_distrito = opciones_dist[sel_dist]
            hoy = date.today()
            id_usuario = usuario.get("Id_usuario")

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

            # IMPORTANTE: guardamos el DUI de la promotora en DUIs_promotoras
            # y también, si lo tienes, el Id_usuario como Creado_por
            sql = """
                INSERT INTO grupos
                    (Nombre, Id_distrito, Estado, Creado_por, Creado_en, DUIs_promotoras)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            _, gid = execute(
                sql,
                (nom, id_distrito, "ACTIVO", id_usuario, hoy, dui)
            )
            st.success(f"Grupo creado correctamente (Id_grupo={gid}).")


# ----------------- MIS GRUPOS (listar + eliminar + editar DUIs) ----------------- #

def _mis_grupos():
    _titulo("Mis grupos")

    usuario = current_user()
    if not usuario:
        st.error("No hay usuario en sesión.")
        st.stop()

    dui_actual = (usuario.get("DUI") or "").strip()
    if not dui_actual:
        st.error("El usuario en sesión no tiene DUI registrado.")
        st.stop()

    st.caption(
        f"Se muestran solo los grupos donde el DUI **{dui_actual}** "
        f"está asignado en la lista de promotoras."
    )

    # Solo grupos donde DUIs_promotoras contiene el DUI actual.
    # Usamos FIND_IN_SET sobre una versión sin espacios.
    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               g.DUIs_promotoras
        FROM grupos g
        LEFT JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, REPLACE(IFNULL(g.DUIs_promotoras, ''), ' ', '')) > 0
        ORDER BY g.Id_grupo DESC
        """,
        (dui_actual,)
    )

    if not grupos:
        st.info("Todavía no hay grupos registrados para este DUI.")
        return

    st.subheader("Listado de grupos")
    st.dataframe(grupos, use_container_width=True)

    # ----------------- ELIMINAR GRUPO ----------------- #

    st.markdown("### Eliminar grupo")

    opciones_eliminar = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito'] or 'SIN DISTRITO'})":
        g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_eliminar_grupo"):
        sel_elim = st.selectbox(
            "Seleccione el grupo a eliminar",
            list(opciones_eliminar.keys())
        )
        confirmar_elim = st.checkbox(
            "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar grupo", type="secondary")

        if eliminar:
            if not confirmar_elim:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                id_sel = opciones_eliminar[sel_elim]
                try:
                    sql = "DELETE FROM grupos WHERE Id_grupo = %s"
                    filas, _ = execute(sql, (id_sel,))
                    if filas > 0:
                        st.success(f"Grupo {sel_elim} eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("No se encontró el grupo seleccionado.")
                except Exception as e:
                    st.error(
                        "No se puede eliminar el grupo porque está siendo usado "
                        "por otros registros."
                    )
                    st.exception(e)

    st.markdown("---")

    # ----------------- EDITAR DUIs DE PROMOTORAS ASIGNADAS ----------------- #

    st.markdown("### Editar promotoras (DUIs) asignadas al grupo")

    # Diccionario con info completa del grupo
    grupos_dict = {
        f"{g['Id_grupo']} - {g['Nombre']}": g for g in grupos
    }

    with st.form("form_editar_duis"):
        sel_edit = st.selectbox(
            "Seleccione el grupo a editar",
            list(grupos_dict.keys())
        )
        grupo_sel = grupos_dict[sel_edit]
        duis_actuales = grupo_sel.get("DUIs_promotoras") or ""

        ayuda_texto = (
            "DUIs de promotoras asignadas al grupo, separados por coma "
            "(ejemplo: 065251519,012345678). "
            "Procura NO dejar espacios."
        )

        nuevos_duis = st.text_input(
            "DUIs (separados por coma)",
            value=duis_actuales,
            help=ayuda_texto,
        )

        guardar = st.form_submit_button("Guardar cambios")

        if guardar:
            # Normalizamos: quitamos espacios y duplicados
            partes = [d.strip() for d in (nuevos_duis or "").split(",") if d.strip()]
            partes_unicas = []
            for d in partes:
                if d not in partes_unicas:
                    partes_unicas.append(d)
            valor_final = ",".join(partes_unicas)

            try:
                sql = "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s"
                filas, _ = execute(sql, (valor_final, grupo_sel["Id_grupo"]))
                if filas > 0:
                    st.success("Lista de DUIs actualizada correctamente.")
                    st.rerun()
                else:
                    st.warning("No se encontró el grupo seleccionado.")
            except Exception as e:
                st.error(
                    "No se pudo actualizar la lista de DUIs por un error en la base de datos."
                )
                st.exception(e)


# ----------------- CREAR DIRECTIVA (placeholder) ----------------- #

def _crear_directiva():
    _titulo("Crear Directiva")
    st.info("Aquí luego podemos implementar la creación de la directiva del grupo.")


# ----------------- REPORTES (placeholder) ----------------- #

def _reportes():
    _titulo("Reportes")
    st.info("Aquí podrás ver o descargar reportes de tus grupos.")


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
