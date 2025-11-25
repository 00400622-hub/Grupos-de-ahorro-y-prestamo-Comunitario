# modulos/promotora/grupos.py
import streamlit as st
from datetime import date

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user
from modulos.promotora.directiva import crear_directiva_panel  # 👈 NUEVO


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


# -------------------------------------------------------
# Helpers para reportes (reglamento + caja)
# -------------------------------------------------------
def _obtener_reglamento_por_grupo(id_grupo: int) -> dict | None:
    """
    Copia del helper de directiva: trae el reglamento de un grupo.
    """
    sql = """
    SELECT *
    FROM reglamento_grupo
    WHERE Id_grupo = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _obtener_caja_por_rango(id_grupo: int, fecha_ini, fecha_fin):
    """
    Trae la caja (entradas / salidas) por reunión dentro de un rango de fechas.
    IMPORTANTE: usamos DATE(rg.Fecha) para que el eje X del gráfico no muestre horas.
    """
    sql = """
    SELECT 
        DATE(rg.Fecha) AS Fecha,
        cr.Total_entradas,
        cr.Total_salidas
    FROM caja_reunion cr
    JOIN reuniones_grupo rg ON rg.Id_reunion = cr.Id_reunion
    WHERE cr.Id_grupo = %s
      AND rg.Fecha BETWEEN %s AND %s
    ORDER BY rg.Fecha
    """
    return fetch_all(sql, (id_grupo, fecha_ini, fecha_fin))


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
# Sección: Reportes para promotora
# -------------------------------------------------------
def _seccion_reportes_promotora(promotora: dict):
    st.subheader("Reportes de mis grupos")

    dui_actual = promotora["DUI"]

    # Grupos donde la promotora participa
    grupos = fetch_all(
        """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito
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

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    etiqueta = st.selectbox(
        "Selecciona el grupo del que deseas ver los reportes",
        list(opciones_grupo.keys()),
    )
    id_grupo_sel = opciones_grupo[etiqueta]

    st.markdown(f"**Grupo seleccionado:** {etiqueta}")

    # Fechas del ciclo según reglamento
    reglamento = _obtener_reglamento_por_grupo(id_grupo_sel)
    if not reglamento:
        st.warning("Este grupo aún no tiene reglamento definido.")
        return

    fecha_ini = reglamento.get("Fecha_inicio_ciclo")
    fecha_fin = reglamento.get("Fecha_fin_ciclo")

    if not fecha_ini or not fecha_fin:
        st.warning(
            "El reglamento del grupo no tiene definidas las fechas de inicio y fin de ciclo."
        )
        return

    st.write(f"Ciclo considerado: **{fecha_ini} → {fecha_fin}**")

    datos = _obtener_caja_por_rango(id_grupo_sel, fecha_ini, fecha_fin)
    if not datos:
        st.info("No hay registros de caja para este grupo en el ciclo seleccionado.")
        return

    fechas = [d["Fecha"] for d in datos]
    ingresos = [float(d["Total_entradas"] or 0) for d in datos]
    egresos = [float(d["Total_salidas"] or 0) for d in datos]
    consolidado = [ingresos[i] - egresos[i] for i in range(len(ingresos))]

    st.markdown("## Ingresos vs egresos por reunión")
    st.line_chart(
        {
            "Ingresos": ingresos,
            "Egresos": egresos,
        },
        x=fechas,
    )

    st.markdown("## Consolidado por reunión")
    st.line_chart(
        {
            "Consolidado": consolidado,
        },
        x=fechas,
    )


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

    # 👉 AQUÍ ya se muestra el panel de creación / gestión de directivas
    with tabs[2]:
        crear_directiva_panel(promotora)

    with tabs[3]:
        _seccion_reportes_promotora(promotora)
