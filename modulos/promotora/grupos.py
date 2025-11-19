# modulos/promotora/grupos.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# ==========================
# Utilidades
# ==========================


def _obtener_promotora_por_dui(dui: str) -> dict | None:
    """
    Devuelve la fila de la tabla 'promotora' cuyo DUI coincida.
    """
    return fetch_one(
        """
        SELECT Id_promotora, Nombre, DUI
        FROM promotora
        WHERE DUI = %s
        LIMIT 1
        """,
        (dui,),
    )


def _grupos_de_promotora_por_dui(dui: str):
    """
    Devuelve los grupos donde el DUI indicado aparece en la columna DUIs_promotoras.
    """
    return fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               g.DUIs_promotoras
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
        ORDER BY g.Id_grupo
        """,
        (dui,),
    )


# ==========================
# Crear grupo
# ==========================


def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    st.caption(
        f"Promotora principal: {promotora['Nombre']} — DUI: {promotora['DUI']}"
    )

    nombre = st.text_input("Nombre del grupo")

    # Cargar distritos
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )
    if not distritos:
        st.error(
            "No hay distritos registrados en la tabla 'distritos'. "
            "Primero crea distritos desde el panel de administración."
        )
        return

    mapa_distritos = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }
    etiqueta_distrito = st.selectbox(
        "Distrito al que pertenece el grupo", list(mapa_distritos.keys())
    )
    id_distrito = mapa_distritos[etiqueta_distrito]

    if st.button("Guardar grupo"):
        nombre_ok = nombre.strip()
        if not nombre_ok:
            st.warning("Ingresa un nombre de grupo válido.")
            return

        hoy = dt.date.today()

        # Insertar grupo: promotora principal = DUI de la promotora actual
        execute(
            """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado, Creado_en, DUIs_promotoras, Id_promotora)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            """,
            (
                nombre_ok,
                id_distrito,
                "ACTIVO",
                hoy,
                promotora["DUI"],        # primer DUI en la lista
                promotora["Id_promotora"],
            ),
        )

        st.success("Grupo creado correctamente.")
        st.experimental_rerun()


# ==========================
# Mis grupos (listar / eliminar / gestionar promotoras)
# ==========================


def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    grupos = _grupos_de_promotora_por_dui(promotora["DUI"])

    if not grupos:
        st.info(
            "No se encontraron grupos donde tu DUI aparezca como promotora responsable."
        )
        return

    # ---- Tabla con los grupos ----
    st.write("Listado de grupos donde tu DUI aparece como promotora responsable.")
    st.table(grupos)

    # ==========================
    # Sección: Eliminar grupo
    # ==========================
    st.write("---")
    st.markdown("### Eliminar grupo")

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }
    etiqueta_eliminar = st.selectbox(
        "Selecciona el grupo a eliminar", list(opciones_grupo.keys())
    )
    id_grupo_eliminar = opciones_grupo[etiqueta_eliminar]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer)."
    )

    if st.button("Eliminar grupo"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación para eliminar.")
        else:
            execute(
                "DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_eliminar,)
            )
            st.success("Grupo eliminado correctamente.")
            st.experimental_rerun()

    # ==========================
    # Sección: Gestionar promotoras asignadas
    # ==========================
    st.write("---")
    st.markdown("### Gestionar promotoras asignadas a un grupo")

    etiqueta_gestion = st.selectbox(
        "Selecciona el grupo a gestionar",
        list(opciones_grupo.keys()),
        key="sel_grupo_gestion",
    )
    id_grupo_gestion = opciones_grupo[etiqueta_gestion]

    fila_grupo = next(
        (g for g in grupos if g["Id_grupo"] == id_grupo_gestion), None
    )
    duis_str = (fila_grupo or {}).get("DUIs_promotoras") or ""
    duis_lista = [d.strip() for d in duis_str.split(",") if d.strip()]

    if duis_lista:
        st.write("DUIs asignados actualmente:", ", ".join(duis_lista))
    else:
        st.write("Actualmente no hay DUIs de promotoras asignados a este grupo.")

    # ---- Agregar DUIs ----
    st.markdown("#### Agregar promotoras al grupo")
    nuevos_duis_str = st.text_input(
        "Ingresa nuevos DUIs separados por coma (ejemplo: 004006221, 004006220)",
        key="txt_nuevos_duis",
    )

    if st.button("Agregar promotoras al grupo"):
        nuevos = [
            d.strip()
            for d in nuevos_duis_str.split(",")
            if d.strip()
        ]
        if not nuevos:
            st.warning("Debes ingresar al menos un DUI válido para agregar.")
        else:
            # Evitar duplicados
            conjunto = set(duis_lista)
            for d in nuevos:
                conjunto.add(d)
            duis_actualizados = ",".join(sorted(conjunto))

            execute(
                "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                (duis_actualizados, id_grupo_gestion),
            )
            st.success("Promotoras agregadas correctamente al grupo.")
            st.experimental_rerun()

    # ---- Quitar DUIs ----
    st.markdown("#### Quitar promotoras del grupo")
    if duis_lista:
        duis_a_quitar = st.multiselect(
            "Selecciona los DUIs que deseas quitar del grupo",
            duis_lista,
            key="msel_quitar_duis",
        )

        if st.button("Quitar promotoras seleccionadas"):
            if not duis_a_quitar:
                st.warning("Selecciona al menos un DUI para quitar.")
            else:
                duis_restantes = [
                    d for d in duis_lista if d not in duis_a_quitar
                ]
                duis_actualizados = ",".join(duis_restantes)

                execute(
                    "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                    (duis_actualizados, id_grupo_gestion),
                )
                st.success("Promotoras quitadas correctamente del grupo.")
                st.experimental_rerun()
    else:
        st.info("No hay DUIs para quitar en este grupo.")


# ==========================
# Panel principal de Promotora
# ==========================


@require_auth()
@has_role("PROMOTORA")
def promotora_panel():
    """
    Panel general para la PROMOTORA:
    - Crear grupo
    - Ver / eliminar grupos
    - Gestionar promotoras de grupos
    - Crear directiva
    """
    user = get_user()
    if not user:
        st.error("No hay una sesión activa.")
        st.stop()

    promotora = _obtener_promotora_por_dui(user["DUI"])
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    st.title("Panel de Promotora")

       pestañas = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with pestañas[0]:
        _crear_grupo(promotora)

    with pestañas[1]:
        _mis_grupos(promotora)

    with pestañas[2]:
        from modulos.promotora.directiva import crear_directiva_panel
        crear_directiva_panel(promotora)

    with pestañas[3]:
        st.info("Aquí más adelante puedes agregar reportes específicos para la promotora.")
