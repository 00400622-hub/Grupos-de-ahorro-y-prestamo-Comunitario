# modulos/promotora/grupos.py
import streamlit as st
from datetime import date
import pandas as pd  # 👈 NUEVO

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user
from modulos.promotora.directiva import crear_directiva_panel  # 👈 ya estaba


# -------------------------------------------------------
# Helpers generales
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
    resultado: list[str] = []

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
    Obtiene la fila de 'promotora' correspondiente al usuario en sesión (por su DUI).
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


# ===== Helpers específicos para REPORTES (reutilizan la data existente) =====
def _obtener_reglamento_por_grupo(id_grupo: int) -> dict | None:
    return fetch_one(
        """
        SELECT *
        FROM reglamento_grupo
        WHERE Id_grupo = %s
        LIMIT 1
        """,
        (id_grupo,),
    )


def _obtener_cierres_ciclo_grupo(id_grupo: int):
    """
    Historial de cierres del grupo (para poder elegir ciclos pasados).
    """
    return fetch_all(
        """
        SELECT
            Id_cierre,
            Fecha_cierre,
            Fecha_inicio_ciclo,
            Fecha_fin_ciclo,
            Total_ahorro_grupo,
            Porcion_fondo_grupo
        FROM cierres_ciclo
        WHERE Id_grupo = %s
        ORDER BY Fecha_inicio_ciclo ASC, Id_cierre ASC
        """,
        (id_grupo,),
    )


def _obtener_caja_rango(id_grupo: int, fecha_inicio=None, fecha_fin=None):
    """
    Devuelve las filas de caja_reunion del grupo entre dos fechas (por fecha de reunión),
    con ingresos, egresos y saldo de cierre.
    """
    sql = """
        SELECT
            rg.Fecha AS Fecha,
            cr.Total_entradas AS Ingresos,
            cr.Total_salidas AS Egresos,
            cr.Saldo_cierre AS Saldo_cierre
        FROM caja_reunion cr
        JOIN reuniones_grupo rg ON rg.Id_reunion = cr.Id_reunion
        WHERE cr.Id_grupo = %s
    """
    params: list = [id_grupo]

    if fecha_inicio is not None and fecha_fin is not None:
        sql += " AND rg.Fecha BETWEEN %s AND %s"
        params.extend([fecha_inicio, fecha_fin])

    sql += " ORDER BY rg.Fecha ASC"
    return fetch_all(sql, tuple(params))


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
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )
    opciones = {d["Nombre"]: d["Id_distrito"] for d in distritos}
    nombre_distrito = (
        st.selectbox("Distrito", list(opciones.keys())) if opciones else None
    )
    id_distrito = opciones.get(nombre_distrito) if nombre_distrito else None

    # DUIs de promotoras asignadas al grupo (por defecto, la promotora actual)
    duis_por_defecto = promotora["DUI"]
    duis_input = st.text_input(
        "Promotoras asignadas al grupo (DUIs separados por coma)",
        value=duis_por_defecto,
        help=(
            "Por defecto se usa tu propio DUI. "
            "Si quieres que otra promotora también vea y gestione este grupo, "
            "escribe sus DUIs separados por coma."
        ),
    )

    if st.button("Guardar grupo", type="primary"):
        if not nombre.strip():
            st.warning("Debes ingresar el nombre del grupo.")
            return

        if not id_distrito:
            st.warning("Debes seleccionar un distrito.")
            return

        duis_lista = _parsear_duis(duis_input)

        # Aseguramos que al menos esté el DUI de la promotora que crea el grupo
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
# Sección: Mis grupos (listar / eliminar / gestionar promotoras)
# -------------------------------------------------------
def _mis_grupos(promotora: dict):
    st.subheader("Mis grupos")

    dui_actual = promotora["DUI"]

    # Solo grupos donde el DUI de la promotora aparezca en DUIs_promotoras
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
        WHERE FIND_IN_SET(%s, REPLACE(g.DUIs_promotoras, ' ', '')) > 0
        ORDER BY g.Id_grupo ASC
        """,
        (dui_actual,),
    )

    if not grupos:
        st.info("No tienes grupos asignados todavía.")
        return

    st.write(
        "Listado de grupos donde tu DUI aparece como promotora responsable."
    )
    st.table(grupos)

    # ---------------------------------------
    # Eliminar grupo
    # ---------------------------------------
    st.markdown("---")
    st.markdown("### Eliminar grupo")

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g for g in grupos
    }
    etiqueta_grupo_eliminar = st.selectbox(
        "Selecciona el grupo a eliminar",
        list(opciones_grupo.keys()),
        key="grupo_eliminar",
    )
    grupo_sel_eliminar = opciones_grupo.get(etiqueta_grupo_eliminar)

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer).",
        key="chk_eliminar_grupo",
    )

    if st.button("Eliminar grupo", type="secondary"):
        if not grupo_sel_eliminar:
            st.warning("Debes elegir un grupo.")
        elif not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            execute(
                "DELETE FROM grupos WHERE Id_grupo = %s",
                (grupo_sel_eliminar["Id_grupo"],),
            )
            st.success("Grupo eliminado correctamente.")
            st.rerun()

    # ---------------------------------------
    # Gestionar promotoras asignadas a un grupo
    # ---------------------------------------
    st.markdown("---")
    st.markdown("### Gestionar promotoras asignadas a un grupo")

    etiqueta_grupo_gestion = st.selectbox(
        "Selecciona el grupo a gestionar",
        list(opciones_grupo.keys()),
        key="grupo_gestion",
    )
    grupo_sel_gestion = opciones_grupo.get(etiqueta_grupo_gestion)

    if not grupo_sel_gestion:
        return

    duis_actuales = _parsear_duis(grupo_sel_gestion.get("DUIs_promotoras", ""))
    st.write(
        "DUIs asignados actualmente: ",
        ", ".join(duis_actuales) if duis_actuales else "Ninguno",
    )

    # ---- Agregar promotora ----
    nuevo_dui = st.text_input(
        "Agregar DUI de promotora",
        key="nuevo_dui",
        help="Escribe el DUI de la promotora que quieres agregar al grupo.",
    )
    if st.button("Agregar promotora al grupo", key="btn_agregar_promotora"):
        dui_limpio = _normalizar_dui(nuevo_dui)
        if not dui_limpio:
            st.warning("Debes escribir un DUI.")
        elif len(dui_limpio) != 9:
            st.warning("El DUI debe tener 9 dígitos.")
        elif dui_limpio in duis_actuales:
            st.info("Ese DUI ya está asignado al grupo.")
        else:
            duis_actuales.append(dui_limpio)
            duis_actuales_unicos = _parsear_duis(_serializar_duis(duis_actuales))
            execute(
                "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                (_serializar_duis(duis_actuales_unicos), grupo_sel_gestion["Id_grupo"]),
            )
            st.success("Promotora agregada al grupo.")
            st.rerun()

    # ---- Quitar promotoras ----
    st.write("")
    duis_a_quitar = st.multiselect(
        "Selecciona los DUIs que deseas quitar del grupo",
        duis_actuales,
        key="duis_quitar",
    )
    if st.button("Quitar DUIs seleccionados", key="btn_quitar_promotora"):
        if not duis_a_quitar:
            st.warning("No has seleccionado ningún DUI para quitar.")
        else:
            duis_restantes = [d for d in duis_actuales if d not in duis_a_quitar]
            if not duis_restantes:
                st.warning("El grupo debe tener al menos una promotora responsable.")
            else:
                execute(
                    "UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
                    (_serializar_duis(duis_restantes), grupo_sel_gestion["Id_grupo"]),
                )
                st.success("Se actualizaron las promotoras asignadas al grupo.")
                st.rerun()


# -------------------------------------------------------
# Sección: Reportes de promotora
# -------------------------------------------------------
def _seccion_reportes_promotora(promotora: dict):
    st.subheader("Reportes de grupos")

    dui_actual = promotora["DUI"]

    # Grupos a los que tiene acceso esta promotora
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
        WHERE FIND_IN_SET(%s, REPLACE(g.DUIs_promotoras, ' ', '')) > 0
        ORDER BY g.Id_grupo ASC
        """,
        (dui_actual,),
    )

    if not grupos:
        st.info("No tienes grupos asignados todavía, por eso no hay reportes.")
        return

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g for g in grupos
    }

    etiqueta_grupo = st.selectbox(
        "Selecciona el grupo del que deseas ver reportes",
        list(opciones_grupo.keys()),
        key="grupo_reportes",
    )
    grupo_sel = opciones_grupo.get(etiqueta_grupo)
    if not grupo_sel:
        return

    id_grupo = grupo_sel["Id_grupo"]

    st.markdown(
        f"**Grupo seleccionado:** {grupo_sel['Nombre']} "
        f"(Id_grupo {id_grupo}, Distrito {grupo_sel['Distrito']})"
    )

    # ------------------ Selección de ciclo ------------------
    reglamento = _obtener_reglamento_por_grupo(id_grupo)
    cierres = _obtener_cierres_ciclo_grupo(id_grupo)

    periodos = {}
    # Ciclo actual según reglamento
    if reglamento and reglamento.get("Fecha_inicio_ciclo") and reglamento.get(
        "Fecha_fin_ciclo"
    ):
        fi = reglamento["Fecha_inicio_ciclo"]
        ff = reglamento["Fecha_fin_ciclo"]
        periodos[
            f"Ciclo actual (reglamento): {fi} al {ff}"
        ] = (fi, ff)

    # Ciclos cerrados históricos
    for c in cierres:
        etiqueta = (
            f"Ciclo cerrado {c['Fecha_inicio_ciclo']} al {c['Fecha_fin_ciclo']} "
            f"(cierre {c['Fecha_cierre']})"
        )
        periodos[etiqueta] = (c["Fecha_inicio_ciclo"], c["Fecha_fin_ciclo"])

    if not periodos:
        st.info(
            "Este grupo aún no tiene fechas de ciclo definidas en el reglamento "
            "ni cierres de ciclo registrados. Se mostrará todo el historial de caja."
        )
        fecha_ini_sel = None
        fecha_fin_sel = None
    else:
        etiqueta_periodo = st.selectbox(
            "Selecciona el ciclo o periodo a analizar",
            list(periodos.keys()),
            key="periodo_reportes",
        )
        fecha_ini_sel, fecha_fin_sel = periodos[etiqueta_periodo]

    # ------------------ Data de caja ------------------
    datos_caja = _obtener_caja_rango(id_grupo, fecha_ini_sel, fecha_fin_sel)

    if not datos_caja:
        st.info(
            "No se encontraron registros de caja para el periodo seleccionado. "
            "Verifica que ya hayas registrado reuniones y caja para este grupo."
        )
        return

    df = pd.DataFrame(datos_caja)

    # Resumen numérico
    total_ingresos = float(df["Ingresos"].sum())
    total_egresos = float(df["Egresos"].sum())
    saldo_min = float(df["Saldo_cierre"].min())
    saldo_max = float(df["Saldo_cierre"].max())

    st.markdown("### Resumen del periodo seleccionado")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total ingresos", f"${total_ingresos:,.2f}")
    with col2:
        st.metric("Total egresos", f"${total_egresos:,.2f}")
    with col3:
        st.metric("Saldo mínimo", f"${saldo_min:,.2f}")
    with col4:
        st.metric("Saldo máximo", f"${saldo_max:,.2f}")

    # ------------ Gráfico de ingresos vs egresos ------------
    st.markdown("### Ingresos vs egresos por reunión")

    df_ie = df[["Fecha", "Ingresos", "Egresos"]].set_index("Fecha")
    st.line_chart(df_ie)

    # ------------ Gráfico consolidado (saldo) ------------
    st.markdown("### Saldo de caja del grupo (consolidado)")

    df_saldo = df[["Fecha", "Saldo_cierre"]].set_index("Fecha")
    st.line_chart(df_saldo)


# -------------------------------------------------------
# Panel principal de Promotora
# -------------------------------------------------------
@require_auth
@has_role("PROMOTORA")
def promotora_panel():
    promotora = _obtener_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario. "
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    st.title("Panel de Promotora")

    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

    with tabs[0]:
        _crear_grupo(promotora)

    with tabs[1]:
        _mis_grupos(promotora)

    # 👉 Aquí se muestra el panel de creación / gestión de directivas
    with tabs[2]:
        crear_directiva_panel(promotora)

    # 👉 NUEVO: reportes para los grupos de la promotora
    with tabs[3]:
        _seccion_reportes_promotora(promotora)
