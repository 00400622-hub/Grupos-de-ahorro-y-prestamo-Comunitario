# modulos/directiva/panel.py

from datetime import date
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# =========================================================
# Helpers comunes
# =========================================================

def _obtener_info_directiva_actual() -> dict | None:
    """
    Usa el usuario en sesión (DUI) para encontrar la directiva y su grupo.
    """
    user = get_user()
    if not user:
        return None

    dui = user.get("DUI")
    if not dui:
        return None

    sql = """
        SELECT
            d.Id_directiva,
            d.Nombre        AS Nombre_directiva,
            d.DUI           AS DUI_directiva,
            g.Id_grupo,
            g.Nombre        AS Nombre_grupo
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE d.DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (dui,))


# =========================================================
# REGLAMENTO
# Tabla: reglamento_grupo
# =========================================================

def _obtener_reglamento_por_grupo(id_grupo: int):
    sql = """
        SELECT *
        FROM reglamento_grupo
        WHERE Id_grupo = %s
        LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _guardar_reglamento(
    id_grupo: int,
    nombre_comunidad: str,
    fecha_formacion: date,
    reunion_dia: str,
    reunion_hora: str,
    reunion_lugar: str,
    reunion_frecuencia: str,
    monto_multa: float,
    ahorro_minimo: float,
    condiciones_prestamo: str,
    fecha_inicio_ciclo: date,
    fecha_fin_ciclo: date,
    meta_social: str,
    interes_por_10: float | None,
    prestamo_maximo: float | None,
    plazo_max_meses: int | None,
):
    existente = _obtener_reglamento_por_grupo(id_grupo)

    if existente:
        # UPDATE
        sql = """
            UPDATE reglamento_grupo
            SET
                Nombre_comunidad   = %s,
                Fecha_formacion    = %s,
                Reunion_dia        = %s,
                Reunion_hora       = %s,
                Reunion_lugar      = %s,
                Reunion_frecuencia = %s,
                Monto_multa        = %s,
                Ahorro_minimo      = %s,
                Condiciones_prestamo = %s,
                Fecha_inicio_ciclo = %s,
                Fecha_fin_ciclo    = %s,
                Meta_social        = %s,
                Interes_por_10     = %s,
                Prestamo_maximo    = %s,
                Plazo_max_meses    = %s
            WHERE Id_grupo = %s
        """
        execute(
            sql,
            (
                nombre_comunidad.strip(),
                fecha_formacion,
                reunion_dia.strip(),
                reunion_hora.strip(),
                reunion_lugar.strip(),
                reunion_frecuencia.strip(),
                monto_multa,
                ahorro_minimo,
                condiciones_prestamo.strip(),
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
                interes_por_10,
                prestamo_maximo,
                plazo_max_meses,
                id_grupo,
            ),
        )
    else:
        # INSERT
        sql = """
            INSERT INTO reglamento_grupo (
                Id_grupo,
                Nombre_comunidad,
                Fecha_formacion,
                Reunion_dia,
                Reunion_hora,
                Reunion_lugar,
                Reunion_frecuencia,
                Monto_multa,
                Ahorro_minimo,
                Condiciones_prestamo,
                Fecha_inicio_ciclo,
                Fecha_fin_ciclo,
                Meta_social,
                Interes_por_10,
                Prestamo_maximo,
                Plazo_max_meses
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
        """
        execute(
            sql,
            (
                id_grupo,
                nombre_comunidad.strip(),
                fecha_formacion,
                reunion_dia.strip(),
                reunion_hora.strip(),
                reunion_lugar.strip(),
                reunion_frecuencia.strip(),
                monto_multa,
                ahorro_minimo,
                condiciones_prestamo.strip(),
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
                interes_por_10,
                prestamo_maximo,
                plazo_max_meses,
            ),
        )


def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglamento del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]

    st.caption(
        f"Directiva: {info_dir['Nombre_directiva']} — "
        f"Grupo: {nombre_grupo}"
    )

    regl = _obtener_reglamento_por_grupo(id_grupo)

    # valores por defecto
    nombre_comunidad = (regl["Nombre_comunidad"] if regl else "") or ""
    fecha_formacion = regl["Fecha_formacion"] if regl else date.today()
    reunion_dia = (regl["Reunion_dia"] if regl else "") or ""
    reunion_hora = (regl["Reunion_hora"] if regl else "") or ""
    reunion_lugar = (regl["Reunion_lugar"] if regl else "") or ""
    reunion_frecuencia = (regl["Reunion_frecuencia"] if regl else "") or ""
    monto_multa = float(regl["Monto_multa"]) if regl else 0.0
    ahorro_minimo = float(regl["Ahorro_minimo"]) if regl else 0.0
    condiciones_prestamo = (regl["Condiciones_prestamo"] if regl else "") or ""
    fecha_inicio_ciclo = regl["Fecha_inicio_ciclo"] if regl else date.today()
    fecha_fin_ciclo = regl["Fecha_fin_ciclo"] if regl else date.today()
    meta_social = (regl["Meta_social"] if regl else "") or ""
    interes_por_10 = (
        float(regl["Interes_por_10"])
        if regl and regl["Interes_por_10"] is not None
        else 0.0
    )
    prestamo_maximo = (
        float(regl["Prestamo_maximo"])
        if regl and regl["Prestamo_maximo"] is not None
        else 0.0
    )
    plazo_max_meses = (
        int(regl["Plazo_max_meses"])
        if regl and regl["Plazo_max_meses"] is not None
        else 0
    )

    with st.form("form_reglamento"):
        st.markdown("### 1. Información general")
        nombre_comunidad_in = st.text_input(
            "Nombre de la comunidad", value=nombre_comunidad
        )
        fecha_formacion_in = st.date_input(
            "Fecha en que se formó el grupo de ahorro",
            value=fecha_formacion,
        )

        st.markdown("### 3. Reuniones")
        reunion_dia_in = st.text_input("Día de reunión", value=reunion_dia)
        reunion_hora_in = st.text_input("Hora de reunión", value=reunion_hora)
        reunion_lugar_in = st.text_input("Lugar de reunión", value=reunion_lugar)
        reunion_frecuencia_in = st.text_input(
            "Frecuencia de la reunión", value=reunion_frecuencia
        )

        st.markdown("### 5. Multas y ahorros")
        monto_multa_in = st.number_input(
            "Monto de la multa por inasistencia",
            min_value=0.0,
            step=0.01,
            value=monto_multa,
        )
        ahorro_minimo_in = st.number_input(
            "Cantidad mínima de ahorro por reunión",
            min_value=0.0,
            step=0.01,
            value=ahorro_minimo,
        )

        st.markdown("### 8. Préstamos")
        interes_por_10_in = st.number_input(
            "Pagamos __% de interés por cada $10.00 prestados",
            min_value=0.0,
            step=0.01,
            value=interes_por_10,
        )
        prestamo_maximo_in = st.number_input(
            "Solamente podemos tomar préstamos hasta la cantidad máxima de",
            min_value=0.0,
            step=0.01,
            value=prestamo_maximo,
        )
        plazo_max_meses_in = st.number_input(
            "Solamente podemos tomar préstamos por un plazo máximo de (meses)",
            min_value=0,
            step=1,
            value=plazo_max_meses,
        )
        condiciones_prestamo_in = st.text_area(
            "Condiciones adicionales de préstamo",
            value=condiciones_prestamo,
        )

        st.markdown("### 9. Ciclo")
        fecha_inicio_ciclo_in = st.date_input(
            "Empezamos ciclo el (fecha del primer depósito)",
            value=fecha_inicio_ciclo,
        )
        fecha_fin_ciclo_in = st.date_input(
            "Terminamos el ciclo el",
            value=fecha_fin_ciclo,
        )

        st.markdown("### 10. Meta social")
        meta_social_in = st.text_area(
            "Meta social",
            value=meta_social,
            help="Escribe la meta social del grupo.",
        )

        col1, col2 = st.columns(2)
        guardar = col1.form_submit_button("Guardar reglamento", type="primary")
        eliminar = col2.form_submit_button(
            "Eliminar reglamento", type="secondary"
        )

    if guardar:
        if not nombre_comunidad_in.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        _guardar_reglamento(
            id_grupo=id_grupo,
            nombre_comunidad=nombre_comunidad_in,
            fecha_formacion=fecha_formacion_in,
            reunion_dia=reunion_dia_in,
            reunion_hora=reunion_hora_in,
            reunion_lugar=reunion_lugar_in,
            reunion_frecuencia=reunion_frecuencia_in,
            monto_multa=monto_multa_in,
            ahorro_minimo=ahorro_minimo_in,
            condiciones_prestamo=condiciones_prestamo_in,
            fecha_inicio_ciclo=fecha_inicio_ciclo_in,
            fecha_fin_ciclo=fecha_fin_ciclo_in,
            meta_social=meta_social_in,
            interes_por_10=interes_por_10_in,
            prestamo_maximo=prestamo_maximo_in,
            plazo_max_meses=plazo_max_meses_in,
        )
        st.success("Reglamento guardado correctamente.")
        st.rerun()

    if eliminar and regl:
        execute("DELETE FROM reglamento_grupo WHERE Id_grupo = %s", (id_grupo,))
        st.success("Reglamento eliminado.")
        st.rerun()


# =========================================================
# MIEMBROS
# Tabla: miembros
# =========================================================

def _obtener_miembros_de_grupo(id_grupo: int):
    sql = """
        SELECT Id_miembro, Nombre, DUI, Sexo, Cargo, Activo
        FROM miembros
        WHERE Id_grupo = %s
        ORDER BY Nombre
    """
    return fetch_all(sql, (id_grupo,))


def _seccion_miembros(info_dir: dict):
    st.subheader("Miembros del grupo")

    id_grupo = info_dir["Id_grupo"]

    miembros = _obtener_miembros_de_grupo(id_grupo)

    if miembros:
        st.markdown("### Miembros registrados")
        st.table(miembros)
    else:
        st.info("Todavía no hay miembros registrados para este grupo.")

    st.markdown("---")
    st.markdown("### Registrar nuevo miembro")

    cargos_posibles = [
        "PRESIDENTA",
        "SECRETARIA",
        "TESORERA",
        "VOCAL",
        "ASOCIADO",
    ]

    with st.form("form_nuevo_miembro"):
        nombre_m = st.text_input("Nombre completo")
        dui_m = st.text_input("DUI (puede ser con o sin guiones)")
        sexo_m = st.selectbox("Sexo", ["F", "M", "Otro"])
        cargo_m = st.selectbox("Cargo en el grupo", cargos_posibles)
        enviar_m = st.form_submit_button("Agregar miembro")

    if enviar_m:
        if not nombre_m.strip():
            st.warning("Debes indicar el nombre del miembro.")
            return

        # si el cargo no es ASOCIADO, verificar que no exista otro con ese cargo
        if cargo_m != "ASOCIADO":
            existe_cargo = fetch_one(
                """
                SELECT Id_miembro
                FROM miembros
                WHERE Id_grupo = %s
                  AND Cargo = %s
                  AND Activo = 1
                LIMIT 1
                """,
                (id_grupo, cargo_m),
            )
            if existe_cargo:
                st.error(
                    f"Ya existe un miembro activo con el cargo {cargo_m}. "
                    "Primero márcalo como inactivo o cambiale el cargo."
                )
                return

        execute(
            """
            INSERT INTO miembros (Id_grupo, Nombre, DUI, Sexo, Cargo, Activo)
            VALUES (%s, %s, %s, %s, %s, 1)
            """,
            (id_grupo, nombre_m.strip(), dui_m.strip(), sexo_m, cargo_m),
        )
        st.success("Miembro agregado correctamente.")
        st.rerun()

    # Baja lógica de miembro
    st.markdown("---")
    st.markdown("### Dar de baja / cambiar estado de un miembro")

    miembros_activos = [
        m for m in miembros if m["Activo"] == 1
    ] if miembros else []

    if not miembros_activos:
        st.info("No hay miembros activos para dar de baja.")
        return

    opciones = {
        f"{m['Nombre']} — {m['Cargo']}": m["Id_miembro"]
        for m in miembros_activos
    }
    etiqueta_sel = st.selectbox(
        "Selecciona el miembro a dar de baja",
        list(opciones.keys()),
        key="miembro_baja",
    )
    id_miembro_sel = opciones[etiqueta_sel]

    if st.button("Marcar como inactivo", type="secondary"):
        execute(
            "UPDATE miembros SET Activo = 0 WHERE Id_miembro = %s",
            (id_miembro_sel,),
        )
        st.success("Miembro marcado como inactivo.")
        st.rerun()


# =========================================================
# ASISTENCIA
# Tablas: reuniones_grupo, asistencia_miembro
# =========================================================

def _seccion_asistencia(info_dir: dict):
    st.subheader("Asistencia a reuniones")

    id_grupo = info_dir["Id_grupo"]

    # -----------------------------
    # Crear / seleccionar reunión
    # -----------------------------
    st.markdown("#### Crear o abrir reunión")

    with st.form("form_reunion"):
        fecha_reu = st.date_input(
            "Fecha de la reunión",
            value=date.today()
        )
        num_reu = st.number_input(
            "Número de reunión en el ciclo",
            min_value=1,
            step=1,
            value=1
        )
        tema_reu = st.text_input(
            "Tema u observaciones (opcional)",
            ""
        )
        enviar_reu = st.form_submit_button("Crear / abrir esta reunión")

    if enviar_reu:
        # ¿Ya existe una reunión con esa fecha para este grupo?
        existente = fetch_one(
            """
            SELECT Id_reunion
            FROM reuniones_grupo
            WHERE Id_grupo = %s AND Fecha = %s
            LIMIT 1
            """,
            (id_grupo, fecha_reu),
        )
        if existente:
            id_reunion = existente["Id_reunion"]
            st.info("Ya existía una reunión en esa fecha, se abrió para editar asistencia.")
        else:
            id_reunion = execute(
                """
                INSERT INTO reuniones_grupo (Id_grupo, Fecha, Numero_reunion, Tema)
                VALUES (%s, %s, %s, %s)
                """,
                (id_grupo, fecha_reu, num_reu, tema_reu),
                return_last_id=True,
            )
            st.success("Reunión creada correctamente.")

        st.session_state["reunion_abierta"] = id_reunion
        st.rerun()

    # -----------------------------
    # Listar reuniones del grupo
    # -----------------------------
    reuniones = fetch_all(
        """
        SELECT Id_reunion, Fecha, Numero_reunion, Tema
        FROM reuniones_grupo
        WHERE Id_grupo = %s
        ORDER BY Fecha DESC, Id_reunion DESC
        """,
        (id_grupo,),
    )

    if not reuniones:
        st.info("Todavía no hay reuniones registradas para este grupo.")
        return

    mapa_reu = {
        f"{r['Fecha']}  (Reunión #{r['Numero_reunion'] or ''} - {r['Tema'] or 'sin tema'})":
            r["Id_reunion"]
        for r in reuniones
    }

    id_reunion_default = st.session_state.get("reunion_abierta")
    claves = list(mapa_reu.keys())
    valores = list(mapa_reu.values())

    if id_reunion_default and id_reunion_default in valores:
        idx_default = valores.index(id_reunion_default)
    else:
        idx_default = 0

    etiqueta_reu = st.selectbox(
        "Reunión a trabajar",
        claves,
        index=idx_default,
        key="sel_reunion_asistencia",
    )
    id_reunion_sel = mapa_reu[etiqueta_reu]

    st.markdown("---")

    # -----------------------------
    # Asistencia de miembros
    # -----------------------------
    st.markdown("#### Lista de miembros y asistencia")

    miembros = _obtener_miembros_de_grupo(id_grupo)
    if not miembros:
        st.warning("No hay miembros registrados para este grupo.")
        return

    # Asistencia ya guardada para esta reunión
    registros = fetch_all(
        """
        SELECT Id_miembro, Presente
        FROM asistencia_miembro
        WHERE Id_reunion = %s
        """,
        (id_reunion_sel,),
    )
    asist_map = {r["Id_miembro"]: bool(r["Presente"]) for r in registros}

    with st.form("form_asistencia"):
        estados = {}
        for m in miembros:
            texto = f"{m['Nombre']} — {m['Sexo']} — {m['Cargo']}"
            estados[m["Id_miembro"]] = st.checkbox(
                texto,
                value=asist_map.get(m["Id_miembro"], False),
                key=f"asis_{id_reunion_sel}_{m['Id_miembro']}",
            )

        guardar_asis = st.form_submit_button("Guardar asistencia")

    if guardar_asis:
        # Borramos la asistencia previa de esa reunión y reinsertamos
        execute(
            "DELETE FROM asistencia_miembro WHERE Id_reunion = %s",
            (id_reunion_sel,),
        )

        for id_m, presente in estados.items():
            execute(
                """
                INSERT INTO asistencia_miembro (Id_reunion, Id_miembro, Presente)
                VALUES (%s, %s, %s)
                """,
                (id_reunion_sel, id_m, 1 if presente else 0),
            )

        st.success("Asistencia guardada correctamente.")
        st.session_state["reunion_abierta"] = id_reunion_sel
        st.rerun()

    # -----------------------------
    # Resumen rápidos
    # -----------------------------
    total_presentes = sum(1 for v in estados.values() if v)
    st.metric("Total presentes en esta reunión", total_presentes)

    # Botón para eliminar reunión completa (opcional)
    with st.expander("Opciones avanzadas"):
        if st.button("Eliminar esta reunión (incluye asistencia)", type="secondary"):
            execute(
                "DELETE FROM reuniones_grupo WHERE Id_reunion = %s",
                (id_reunion_sel,),
            )
            st.success("Reunión eliminada.")
            if "reunion_abierta" in st.session_state:
                del st.session_state["reunion_abierta"]
            st.rerun()


# =========================================================
# PANEL PRINCIPAL DE DIRECTIVA
# =========================================================

@require_auth
@has_role("DIRECTIVA")
def directiva_panel():
    info_dir = _obtener_info_directiva_actual()
    if not info_dir:
        st.error(
            "No se encontró una directiva asociada a este usuario. "
            "Verifica que el DUI exista en la tabla 'directiva'."
        )
        return

    st.title(f"Panel de Directiva — Grupo {info_dir['Nombre_grupo']}")

    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            # Después agregaremos: Ahorros, Caja, Multas, Cierre de ciclo, etc.
        ]
    )

    with tabs[0]:
        _seccion_reglamento(info_dir)

    with tabs[1]:
        _seccion_miembros(info_dir)

    with tabs[2]:
        _seccion_asistencia(info_dir)
