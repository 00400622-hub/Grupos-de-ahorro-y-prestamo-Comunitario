# modulos/promotora/grupos.py
import datetime as dt
from typing import Optional, Dict, List

import streamlit as st
import pandas as pd

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import get_user, require_auth, has_role


# ============================================================
#   Helpers
# ============================================================

def _obtener_promotora_actual(dui_usuario: str) -> Optional[Dict]:
    """
    Busca en la tabla 'promotora' usando el DUI del usuario logueado.
    Devuelve el registro de promotora o None.
    """
    if not dui_usuario:
        return None

    sql = """
        SELECT Id_promotora, Nombre, DUI
        FROM promotora
        WHERE DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (dui_usuario,))


def _obtener_distritos() -> List[Dict]:
    return fetch_all("""
        SELECT Id_distrito, Nombre
        FROM distritos
        ORDER BY Nombre ASC
    """)


# ============================================================
#   Crear grupo
# ============================================================

def _crear_grupo(promotora: Dict):
    st.subheader("Crear grupo")

    st.caption(
        f"Promotora principal: **{promotora['Nombre']}** — DUI: **{promotora['DUI']}**"
    )

    nombre = st.text_input("Nombre del grupo")

    # Distritos en combo
    distritos = _obtener_distritos()
    if not distritos:
        st.warning("No hay distritos registrados. Pide al administrador que cree distritos.")
        return

    opciones = {d["Nombre"]: d["Id_distrito"] for d in distritos}
    nombre_dist = st.selectbox("Distrito", list(opciones.keys()))
    id_distrito = opciones[nombre_dist]

    if st.button("Guardar grupo", type="primary"):
        if not nombre.strip():
            st.warning("Debes escribir un nombre para el grupo.")
            return

        hoy = dt.date.today()
        dui_prom = promotora["DUI"]
        id_prom = promotora["Id_promotora"]

        # Insertamos el grupo. La promotora actual es la principal y además
        # la primera en la lista DUIs_promotoras
        sql = """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado, Creado_por, Creado_en,
                 DUIs_promotoras, Id_promotora)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        execute(
            sql,
            (
                nombre.strip(),
                id_distrito,
                "ACTIVO",
                id_prom,
                hoy,
                dui_prom,     # primer y único DUI al crear
                id_prom,
            ),
        )
        st.success("Grupo creado correctamente.")
        st.experimental_rerun()


# ============================================================
#   Mis grupos (listar, eliminar grupo, quitar promotoras)
# ============================================================

def _mis_grupos(promotora: Dict):
    st.subheader("Mis grupos")

    dui_actual = promotora["DUI"]

    grupos = fetch_all(
        """
        SELECT
            g.Id_grupo,
            g.Nombre,
            d.Nombre AS Distrito,
            g.Estado,
            g.Creado_en,
            g.DUIs_promotoras
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, g.DUIs_promotoras) > 0
        ORDER BY g.Id_grupo ASC
        """,
        (dui_actual,),
    )

    if not grupos:
        st.info("No hay grupos donde tu DUI aparezca como promotora responsable.")
        return

    # Mostrar tabla
    df = pd.DataFrame(grupos)
    st.write(
        "Listado de grupos donde tu DUI aparece como promotora responsable."
    )
    st.dataframe(df, use_container_width=True)

    # --------------------------------------------------------
    # 1) Eliminar grupo
    # --------------------------------------------------------
    st.write("---")
    st.subheader("Eliminar grupo")

    opciones = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }
    etiqueta_sel = st.selectbox(
        "Selecciona el grupo a eliminar",
        list(opciones.keys()),
        key="grupo_eliminar",
    )
    id_grupo_eliminar = opciones[etiqueta_sel]

    confirmar_elim = st.checkbox(
        "Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer).",
        key="chk_eliminar_grupo",
    )

    if st.button("Eliminar grupo", type="secondary"):
        if not confirmar_elim:
            st.warning("Debes marcar la casilla de confirmación para eliminar el grupo.")
        else:
            execute("DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_eliminar,))
            st.success("Grupo eliminado correctamente.")
            st.experimental_rerun()

    # --------------------------------------------------------
    # 2) Quitar promotoras asignadas a un grupo
    # --------------------------------------------------------
    st.write("---")
    st.subheader("Gestionar promotoras asignadas a un grupo")

    etiqueta_gestion = st.selectbox(
        "Selecciona el grupo a gestionar",
        list(opciones.keys()),
        key="grupo_gestionar",
    )
    id_grupo_gestion = opciones[etiqueta_gestion]

    # Obtenemos los DUIs actuales del grupo
    grp = fetch_one(
        """
        SELECT DUIs_promotoras
        FROM grupos
        WHERE Id_grupo = %s
        """,
        (id_grupo_gestion,),
    )

    duis_str = (grp["DUIs_promotoras"] or "").strip()
    if not duis_str:
        st.info("Este grupo no tiene promotoras asignadas en la lista DUIs_promotoras.")
        return

    lista_duis = [d.strip() for d in duis_str.split(",") if d.strip()]

    st.write(f"DUIs asignados actualmente: `{', '.join(lista_duis)}`")

    duis_a_quitar = st.multiselect(
        "Selecciona los DUIs que deseas quitar del grupo",
        options=lista_duis,
        default=[],
        key="duis_a_quitar",
    )

    if st.button("Quitar promotoras seleccionadas"):
        if not duis_a_quitar:
            st.warning("No has seleccionado ningún DUI para quitar.")
        else:
            nueva_lista = [d for d in lista_duis if d not in duis_a_quitar]

            nuevo_valor = ",".join(nueva_lista) if nueva_lista else ""

            execute(
                "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                (nuevo_valor, id_grupo_gestion),
            )
            st.success("Lista de promotoras actualizada correctamente.")
            st.experimental_rerun()


# ============================================================
#   Placeholder para otras pestañas
# ============================================================

def _crear_directiva_placeholder():
    st.subheader("Crear Directiva")
    st.info("Más adelante se implementará la creación de la directiva del grupo.")


def _reportes_placeholder():
    st.subheader("Reportes")
    st.info("Aquí podrás descargar reportes de tus grupos.")


# ============================================================
#   Panel principal de PROMOTORA
# ============================================================

@require_auth()
@has_role("PROMOTORA")
def promotora_panel():
    user = get_user()
    dui_usuario = user.get("DUI")

    promotora = _obtener_promotora_actual(dui_usuario)
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    st.title("Panel de Promotora")
    st.caption(f"Promotora: **{promotora['Nombre']}** — DUI: **{promotora['DUI']}**")

    tab_crear, tab_mis_grupos, tab_directiva, tab_reportes = st.tabs(
        ["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"]
    )

    with tab_crear:
        _crear_grupo(promotora)

    with tab_mis_grupos:
        _mis_grupos(promotora)

    with tab_directiva:
        _crear_directiva_placeholder()

    with tab_reportes:
        _reportes_placeholder()
