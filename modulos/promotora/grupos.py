# modulos/promotora/grupos.py

import streamlit as st
import pandas as pd
from datetime import date

from modulos.auth.rbac import require_auth
from modulos.config.conexion import fetch_all, execute
from modulos.promotora.directiva import crear_directiva_panel


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _normalizar_dui(txt: str) -> str:
    """Quita todo lo que no sea número del DUI."""
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _obtener_promotora_por_dui(dui: str):
    """Devuelve la fila de la tabla promotora para un DUI dado."""
    sql = "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s"
    filas = fetch_all(sql, (dui,))
    return filas[0] if filas else None


def _cargar_distritos():
    sql = "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre"
    return fetch_all(sql)


# ──────────────────────────────────────────────
# Crear grupo
# ──────────────────────────────────────────────

def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    dui_usuario = promotora["DUI"]
    prom = _obtener_promotora_por_dui(dui_usuario)

    if not prom:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    st.caption(f"Promotora principal: {prom['Nombre']} — DUI: {prom['DUI']}")

    # Nombre del grupo
    nombre_grupo = st.text_input(
        "Nombre del grupo",
        key="crear_grupo_nombre",
    )

    # Distritos
    distritos = _cargar_distritos()
    if distritos:
        opciones_dist = {
            d["Nombre"]: d["Id_distrito"] for d in distritos
        }
        nombre_dist_sel = st.selectbox(
            "Distrito",
            list(opciones_dist.keys()),
            key="crear_grupo_distrito",
        )
        id_distrito_sel = opciones_dist[nombre_dist_sel]
    else:
        st.warning("No hay distritos registrados en la tabla 'distritos'.")
        return

    if st.button("Guardar grupo", type="primary", key="btn_guardar_grupo"):
        if not nombre_grupo.strip():
            st.error("Debes ingresar un nombre para el grupo.")
            return

        hoy = date.today()
        dui_principal = _normalizar_dui(dui_usuario)

        try:
            # Estado se deja fijo como ACTIVO al crearse
            sql = """
                INSERT INTO grupos
                    (Nombre, Id_distrito, Estado, Creado_por, Creado_en, DUIs_promotoras, Id_promotora)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            execute(
                sql,
                (
                    nombre_grupo.strip(),
                    id_distrito_sel,
                    "ACTIVO",
                    prom["Id_promotora"],
                    hoy,
                    dui_principal,         # cadena CSV de DUIs de promotoras
                    prom["Id_promotora"],  # promotora principal
                ),
            )
            st.success("Grupo creado correctamente.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error al crear el grupo: {e}")


# ──────────────────────────────────────────────
# Mis grupos: listado, eliminar y gestionar promotoras
# ──────────────────────────────────────────────

def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    dui_prom = _normalizar_dui(promotora["DUI"])

    # Traer solo los grupos donde aparezca el DUI de la promotora
    sql = """
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
    """
    filas = fetch_all(sql, (dui_prom,))

    if not filas:
        st.info("Aún no hay grupos donde tu DUI aparezca como promotora responsable.")
        return

    # Tabla al estilo que ya usas
    df = pd.DataFrame(filas)
    df = df.rename(
        columns={
            "Id_grupo": "Id_grupo",
            "Nombre": "Nombre",
            "Distrito": "Distrito",
            "Estado": "Estado",
            "Creado_en": "Creado_en",
            "DUIs_promotoras": "DUIs_promotoras",
        }
    )

    st.markdown(
        "Listado de grupos donde tu DUI aparece como promotora responsable."
    )
    st.dataframe(df, use_container_width=True)

    # ──────────────────────────────────────────────
    # Eliminar grupo
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Eliminar grupo")

    opciones_grupos = {
        f"{row['Id_grupo']} - {row['Nombre']} ({row['Distrito']})": row["Id_grupo"]
        for row in filas
    }

    etiqueta_elim = st.selectbox(
        "Selecciona el grupo a eliminar",
        list(opciones_grupos.keys()),
        key="sel_grupo_eliminar",
    )
    id_grupo_elim = opciones_grupos[etiqueta_elim]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer).",
        key="chk_confirmar_eliminar_grupo",
    )

    if st.button(
        "Eliminar grupo",
        type="secondary",
        key="btn_eliminar_grupo",
        disabled=not confirmar,
    ):
        try:
            # Si quieres, aquí también puedes borrar otras tablas relacionadas (directiva, etc.)
            execute("DELETE FROM directiva WHERE Id_grupo = %s", (id_grupo_elim,))
            execute("DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_elim,))
            st.success("Grupo eliminado correctamente.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error al eliminar el grupo: {e}")

    # ──────────────────────────────────────────────
    # Gestionar promotoras asignadas a un grupo
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Gestionar promotoras asignadas a un grupo")

    etiqueta_gestion = st.selectbox(
        "Selecciona el grupo a gestionar",
        list(opciones_grupos.keys()),
        key="sel_grupo_gestion",
    )
    id_grupo_gestion = opciones_grupos[etiqueta_gestion]

    fila_sel = next(row for row in filas if row["Id_grupo"] == id_grupo_gestion)
    cadena_duis = fila_sel.get("DUIs_promotoras") or ""
    duis_actuales = [
        d.strip() for d in cadena_duis.split(",") if d.strip()
    ]

    if duis_actuales:
        st.write(
            "DUIs asignados actualmente:",
            ", ".join(duis_actuales),
        )
    else:
        st.write("Este grupo no tiene DUIs de promotoras asignados aún.")

    # Quitar promotoras
    st.markdown("#### Quitar promotoras del grupo")

    if duis_actuales:
        duis_quitar = st.multiselect(
            "Selecciona los DUIs que deseas quitar del grupo",
            duis_actuales,
            key="multisel_duis_quitar",
        )

        if st.button(
            "Quitar DUIs seleccionados",
            key="btn_quitar_duis",
            disabled=not duis_quitar,
        ):
            # Evitar que la promotora actual se quite a sí misma si es la única
            nuevos = [d for d in duis_actuales if d not in duis_quitar]

            if not nuevos:
                st.error(
                    "El grupo debe tener al menos una promotora asignada. "
                    "No puedes quitar todos los DUIs."
                )
            else:
                try:
                    nueva_cadena = ",".join(nuevos)
                    execute(
                        "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                        (nueva_cadena, id_grupo_gestion),
                    )
                    st.success("DUIs actualizados correctamente.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al actualizar DUIs de promotoras: {e}")
    else:
        st.info("No hay DUIs para quitar en este grupo.")

    # Agregar promotora
    st.markdown("#### Agregar promotora al grupo")

    dui_nuevo = st.text_input(
        "DUI de la promotora que deseas agregar (con o sin guiones)",
        key="txt_dui_agregar_promotora",
    )

    if st.button("Agregar promotora al grupo", key="btn_agregar_promotora"):
        dui_nuevo_norm = _normalizar_dui(dui_nuevo)

        if not dui_nuevo_norm:
            st.error("Debes ingresar un DUI válido.")
        elif dui_nuevo_norm in duis_actuales:
            st.warning("Ese DUI ya está asignado al grupo.")
        else:
            # Verificar que exista en la tabla promotora
            prom_add = _obtener_promotora_por_dui(dui_nuevo_norm)
            if not prom_add:
                st.error(
                    "No se encontró una promotora con ese DUI en la tabla 'promotora'."
                )
            else:
                try:
                    nuevos = duis_actuales + [dui_nuevo_norm]
                    nueva_cadena = ",".join(nuevos)
                    execute(
                        "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                        (nueva_cadena, id_grupo_gestion),
                    )
                    st.success("Promotora agregada correctamente al grupo.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al agregar promotora al grupo: {e}")


# ──────────────────────────────────────────────
# Panel principal de promotora
# ──────────────────────────────────────────────

@require_auth(["PROMOTORA"])
def promotora_panel(promotora: dict):
    """
    Panel de la promotora.
    'promotora' viene del login y contiene al menos:
    - promotora["Nombre"]
    - promotora["DUI"]
    - promotora["Rol"] (PROMOTORA)
    """
    st.title("Panel de Promotora")

    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    # Crear grupo
    with tabs[0]:
        _crear_grupo(promotora)

    # Mis grupos + gestión
    with tabs[1]:
        _mis_grupos(promotora)

    # Crear/gestionar directivas (implementado en directiva.py)
    with tabs[2]:
        crear_directiva_panel(promotora)

    # Reportes (placeholder)
    with tabs[3]:
        st.info("Módulo de reportes en construcción.")
