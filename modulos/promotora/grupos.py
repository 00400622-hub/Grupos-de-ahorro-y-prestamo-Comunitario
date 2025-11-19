# modulos/promotora/grupos.py
import streamlit as st
from datetime import date

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def _normalizar_dui(dui: str) -> str:
    """Deja solo dígitos en el DUI."""
    return "".join(ch for ch in (dui or "") if ch.isdigit())


def _parsear_duis(cadena: str) -> list[str]:
    """
    Convierte '004006223, 004006220' -> ['004006223', '004006220']
    quitando espacios, vacíos y duplicados.
    """
    if not cadena:
        return []

    vistos = set()
    resultado = []

    for parte in cadena.split(","):
        d = _normalizar_dui(parte)
        if len(d) == 9 and d not in vistos:
            vistos.add(d)
            resultado.append(d)

    return resultado


def _serializar_duis(lista: list[str]) -> str:
    """Convierte lista a cadena CSV normalizada."""
    return ",".join(lista)


def _obtener_promotora_actual() -> dict | None:
    """
    Obtiene la fila de 'promotora' correspondiente al usuario en sesión.
    """
    user = get_user()
    if not user:
        return None

    return fetch_one(
        """
        SELECT Id_promotora, Nombre, DUI
        FROM promotora
        WHERE DUI = %s
        LIMIT 1
        """,
        (user["DUI"],),
    )


# -------------------------------------------------------
# Sección: Crear grupo
# -------------------------------------------------------
def _crear_grupo(promotora: dict):
    st.subheader("Crear grupo")

    st.write(
        f"**Promotora principal:** {promotora['Nombre']} — **DUI:** {promotora['DUI']}"
    )

    nombre = st.text_input("Nombre del grupo")

    # Distritos
    distritos = fetch_all("SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC")
    opciones = {d["Nombre"]: d["Id_distrito"] for d in distritos}

    nombre_distrito = st.selectbox("Distrito", list(opciones.keys())) if opciones else None
    id_distrito = opciones.get(nombre_distrito) if nombre_distrito else None

    # DUIs de promotoras asignadas al grupo
    duis_por_defecto = promotora["DUI"]
    duis_input = st.text_input(
        "Promotoras asignadas al grupo (DUIs separados por coma)",
        value=duis_por_defecto,
        help="Coloca los DUIs separados por coma. Por defecto se agrega tu DUI.",
    )

    if st.button("Guardar grupo", type="primary"):
        if not nombre.strip():
            st.warning("Debes ingresar el nombre del grupo.")
            return

        if not id_distrito:
            st.warning("Debes seleccionar un distrito.")
            return

        duis_lista = _parsear_duis(duis_input)

        if promotora["DUI"] not in duis_lista:
            duis_lista.insert(0, promotora["DUI"])

        duis_final = _serializar_duis(duis_lista)

        execute(
            """
            INSERT INTO grupos
            (Nombre, Id_distrito, Estado, Creado_en, DUIs_promotoras, Id_promotora)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nombre.strip(),
                id_distrito,
                "ACTIVO",
                date.today(),
                duis_final,
                promotora["Id_promotora"],
            ),
        )

        st.success("Grupo creado correctamente.")
        st.rerun()


# -------------------------------------------------------
# Sección: Mis grupos
# -------------------------------------------------------
def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en,
               g.DUIs_promotoras
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE FIND_IN_SET(%s, REPLACE(g.DUIs_promotoras,' ',''))
        ORDER BY g.Id_grupo ASC
        """,
        (promotora["DUI"],),
    )

    if not grupos:
        st.info("No tienes grupos asignados todavía.")
        return

    st.write("Listado de grupos donde tu DUI aparece como promotora responsable.")
    st.table(grupos)

    # ---------------------------------------------------
    # Eliminar grupo
    # ---------------------------------------------------
    st.markdown("---")
    st.subheader("Eliminar grupo")

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g for g in grupos
    }

    seleccion = st.selectbox(
        "Selecciona el grupo a eliminar",
        list(opciones_grupo.keys()),
        key="sel_eliminar_grupo",
    )

    grupo_sel = opciones_grupo.get(seleccion)

    confirmar = st.checkbox("Confirmo que deseo eliminar este grupo.")

    if st.button("Eliminar grupo"):
        if not confirmar:
            st.warning("Debes confirmar para eliminar.")
        else:
            execute("DELETE FROM grupos WHERE Id_grupo = %s", (grupo_sel["Id_grupo"],))
            st.success("Grupo eliminado.")
            st.rerun()

    # ---------------------------------------------------
    # Gestionar promotoras asignadas
    # ---------------------------------------------------
    st.markdown("---")
    st.subheader("Gestionar promotoras asignadas al grupo")

    seleccion2 = st.selectbox(
        "Selecciona grupo",
        list(opciones_grupo.keys()),
        key="sel_gestion_grupo",
    )

    gsel = opciones_grupo.get(seleccion2)

    if not gsel:
        return

    duis_actuales = _parsear_duis(gsel["DUIs_promotoras"])

    st.write("DUIs asignados actualmente:", ", ".join(duis_actuales))

    # Agregar promotora
    nuevo_dui = st.text_input("Agregar DUI", key="input_agregar_dui")

    if st.button("Agregar promotora"):
        dui = _normalizar_dui(nuevo_dui)
        if len(dui) != 9:
            st.warning("DUI inválido.")
        else:
            if dui in duis_actuales:
                st.info("Este DUI ya está en el grupo.")
            else:
                duis_actuales.append(dui)
                execute(
                    "UPDATE grupos SET DUIs_promotoras=%s WHERE Id_grupo=%s",
                    (_serializar_duis(duis_actuales), gsel["Id_grupo"]),
                )
                st.success("Promotora agregada.")
                st.rerun()

    # Quitar promotoras
    quitar = st.multiselect("Selecciona DUIs a quitar", duis_actuales)

    if st.button("Quitar DUIs seleccionados"):
        restantes = [d for d in duis_actuales if d not in quitar]

        if not restantes:
            st.warning("Debe quedar al menos una promotora responsable.")
        else:
            execute(
                "UPDATE grupos SET DUIs_promotoras=%s WHERE Id_grupo=%s",
                (_serializar_duis(restantes), gsel["Id_grupo"]),
            )
            st.success("Promotoras actualizadas.")
            st.rerun()


# -------------------------------------------------------
# Panel principal
# -------------------------------------------------------
@require_auth
@has_role("PROMOTORA")
def promotora_panel():
    promotora = _obtener_promotora_actual()

    if not promotora:
        st.error("No existe una promotora asociada al DUI del usuario.")
        return

    st.title("Panel de Promotora")

    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with tabs[0]:
        _crear_grupo(promotora)

    with tabs[1]:
        _mis_grupos(promotora)

    with tabs[2]:
        st.info("Aquí se implementará la creación de directiva.")

    with tabs[3]:
        st.info("Aquí irán los reportes.")
