# modulos/promotora/grupos.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# ==========================
#  Utilidades
# ==========================

def _obtener_promotora_actual():
    """
    Busca la promotora asociada al usuario en sesión,
    usando el DUI del usuario.
    """
    user = get_user()
    if not user:
        return None, None

    dui = user.get("DUI")
    if not dui:
        return user, None

    promotora = fetch_one(
        """
        SELECT Id_promotora, Nombre, DUI
        FROM promotora
        WHERE DUI = %s
        LIMIT 1
        """,
        (dui,),
    )
    return user, promotora


def _normalizar_duis(cadena: str) -> str:
    """
    Limpia una cadena de DUIs separados por comas:
    - Quita espacios
    - Elimina elementos vacíos
    - Devuelve de nuevo separados por comas
    """
    if not cadena:
        return ""
    partes = [p.strip() for p in cadena.split(",")]
    partes = [p for p in partes if p]
    return ",".join(partes)


# ==========================
#  Crear grupo
# ==========================

def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    nombre = st.text_input("Nombre del grupo")

    # Distritos
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )
    mapa_distritos = {d["Nombre"]: d["Id_distrito"] for d in distritos}
    distrito_sel = st.selectbox(
        "Distrito",
        list(mapa_distritos.keys()) if mapa_distritos else [],
    )

    # DUI(s) de promotoras
    duis_default = promotora["DUI"] if promotora else ""
    duis_promotoras_input = st.text_input(
        "DUI(s) de promotora(s) responsables (separados por comas)",
        value=duis_default,
        help=(
            "Por defecto se coloca tu DUI. "
            "Si quieres que otra promotora también vea este grupo, "
            "agrega su DUI separado por comas."
        ),
    )

    if st.button("Guardar grupo"):
        if not nombre.strip():
            st.warning("Debes escribir el nombre del grupo.")
            return

        if not distrito_sel:
            st.warning("Debes seleccionar un distrito.")
            return

        if not promotora:
            st.error(
                "No se encontró una promotora asociada a tu usuario. "
                "Verifica que tu DUI exista en la tabla 'promotora'."
            )
            return

        duis_norm = _normalizar_duis(duis_promotoras_input)

        execute(
            """
            INSERT INTO grupos
                (Nombre, Id_distrito, Estado,
                 Creado_por, Creado_en,
                 DUIs_promotoras, Id_promotora)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nombre.strip(),
                mapa_distritos[distrito_sel],
                "ACTIVO",
                promotora["Id_promotora"],
                dt.date.today(),
                duis_norm,
                promotora["Id_promotora"],
            ),
        )
        st.success("Grupo creado correctamente.")
        st.rerun()   # <--- antes estaba st.experimental_rerun()


# ==========================
#  Mis grupos (filtrados por DUI)
# ==========================

def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    if not promotora:
        st.error(
            "No se encontró una promotora asociada a tu usuario. "
            "Verifica que tu DUI exista en la tabla 'promotora'."
        )
        return

    dui = promotora["DUI"]

    # Filtra los grupos donde el DUI actual está en la lista DUIs_promotoras
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
        WHERE FIND_IN_SET(%s, REPLACE(IFNULL(g.DUIs_promotoras,''), ' ', '')) > 0
        ORDER BY g.Id_grupo DESC
        """,
        (dui,),
    )

    if not grupos:
        st.info("Todavía no tienes grupos asignados con tu DUI.")
        return

    st.write("Listado de grupos donde tu DUI aparece como promotora responsable.")
    st.dataframe(grupos)

    # =========
    # Edición sólo de DUIs_promotoras
    # =========
    st.write("---")
    st.write("### Editar promotoras asignadas a un grupo")

    opciones = {
        f"{g['Id_grupo']} - {g['Nombre']}": g for g in grupos
    }
    etiqueta_sel = st.selectbox(
        "Elige el grupo que quieres modificar",
        list(opciones.keys()),
    )
    grupo_sel = opciones[etiqueta_sel]

    nuevos_duis = st.text_input(
        "DUI(s) de promotora(s) para este grupo (separados por comas)",
        value=grupo_sel.get("DUIs_promotoras") or "",
        help=(
            "Modifica la lista de DUIs para agregar o quitar promotoras. "
            "Usa comas para separar varios DUIs."
        ),
    )

    if st.button("Guardar cambios en promotoras"):
        duis_norm = _normalizar_duis(nuevos_duis)
        execute(
            "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
            (duis_norm, grupo_sel["Id_grupo"]),
        )
        st.success("Promotoras actualizadas para el grupo.")
        st.rerun()   # <--- antes estaba st.experimental_rerun()


# ==========================
#  Panel principal de Promotora
# ==========================

@require_auth
@has_role("PROMOTORA")
def promotora_panel():
    user, promotora = _obtener_promotora_actual()

    if not user:
        st.error("No hay una sesión activa.")
        return

    st.title("Panel de Promotora")

    if promotora:
        st.caption(
            f"Promotora: {promotora['Nombre']} — DUI: {promotora['DUI']}"
        )
    else:
        st.warning(
            "Tu usuario no está vinculado a ninguna promotora en la tabla "
            "'promotora' (no se encontró tu DUI)."
        )

    pestañas = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with pestañas[0]:
        if promotora:
            _crear_grupo(promotora)
        else:
            st.error(
                "No puedes crear grupos porque tu DUI no está registrado como promotora."
            )

    with pestañas[1]:
        _mis_grupos(promotora)

    # Las otras pestañas las puedes llenar después
    with pestañas[2]:
        st.info("Aquí luego implementamos la creación de Directiva del grupo.")

    with pestañas[3]:
        st.info("Aquí luego implementamos los reportes.")
