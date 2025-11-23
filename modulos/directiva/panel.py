# modulos/directiva/panel.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _obtener_directiva_actual():
    """
    Busca la fila de 'directiva' correspondiente al usuario en sesión
    (por su DUI) y devuelve también info básica del grupo.
    """
    user = get_user()
    if not user:
        return None

    sql = """
        SELECT
            d.Id_directiva,
            d.Nombre      AS Nombre_directiva,
            d.DUI         AS DUI_directiva,
            d.Id_grupo,
            g.Nombre      AS Nombre_grupo,
            g.Creado_en   AS Grupo_creado_en
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE d.DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (user["DUI"],))


def _cargar_reglamento(id_grupo: int):
    """Devuelve el reglamento del grupo (o None si aún no existe)."""
    sql = """
        SELECT *
        FROM reglamento_grupo
        WHERE Id_grupo = %s
        LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


# -------------------------------------------------------------------
# Sección: Reglamento del grupo
# -------------------------------------------------------------------
def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglamento del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]
    fecha_creacion_grupo = info_dir["Grupo_creado_en"]

    if isinstance(fecha_creacion_grupo, dt.datetime):
        fecha_creacion_grupo = fecha_creacion_grupo.date()

    st.caption(
        f"Grupo: **{nombre_grupo}** — Fecha en que se formó el grupo de ahorro: "
        f"**{fecha_creacion_grupo}**"
    )

    reglamento = _cargar_reglamento(id_grupo)

    # Valores por defecto si ya existe reglamento
    comunidad_default = reglamento["Nombre_comunidad"] if reglamento else ""
    reunion_dia_default = reglamento["Reunion_dia"] if reglamento else ""
    reunion_hora_default = reglamento["Reunion_hora"] if reglamento else ""
    reunion_lugar_default = reglamento["Reunion_lugar"] if reglamento else ""
    reunion_frec_default = reglamento["Reunion_frecuencia"] if reglamento else ""

    monto_multa_default = float(reglamento["Monto_multa"]) if reglamento else 0.0
    ahorro_minimo_default = float(reglamento["Ahorro_minimo"]) if reglamento else 0.0

    condiciones_default = (
        reglamento["Condiciones_prestamo"] if reglamento else ""
    )

    fecha_ini_default = (
        reglamento["Fecha_inicio_ciclo"] if reglamento else fecha_creacion_grupo
    )
    fecha_fin_default = (
        reglamento["Fecha_fin_ciclo"]
        if reglamento
        else fecha_creacion_grupo + dt.timedelta(days=365)
    )

    meta_social_default = reglamento["Meta_social"] if reglamento else ""

    with st.form("form_reglamento_grupo"):
        # 1. Nombre de la comunidad
        nombre_comunidad = st.text_input(
            "Nombre de la comunidad",
            value=comunidad_default,
            help="Ejemplo: Comunidad Las Flores, Cantón X, etc.",
        )

        # 2. Fecha de formación (solo mostrar, se guarda igual con la del grupo)
        st.date_input(
            "Fecha en que se formó el grupo de ahorro",
            value=fecha_creacion_grupo,
            disabled=True,
        )

        st.markdown("---")
        st.markdown("### 3. Reuniones")

        reunion_dia = st.text_input(
            "Día de reunión",
            value=reunion_dia_default,
            help="Ejemplo: Lunes, Martes, cada 15 días en sábado, etc.",
        )
        reunion_hora = st.text_input(
            "Hora de reunión",
            value=reunion_hora_default,
            help="Ejemplo: 3:00 p.m.",
        )
        reunion_lugar = st.text_input(
            "Lugar de reunión",
            value=reunion_lugar_default,
            help="Ejemplo: Casa comunal, escuela, casa de la presidenta, etc.",
        )
        reunion_frecuencia = st.text_input(
            "Frecuencia de la reunión",
            value=reunion_frec_default,
            help="Ejemplo: Semanal, quincenal, mensual.",
        )

        st.markdown("---")
        st.markdown("### 4. Multas y ahorros")

        monto_multa = st.number_input(
            "Monto de la multa (por llegar tarde o faltar a la reunión)",
            min_value=0.0,
            step=0.25,
            value=monto_multa_default,
        )

        ahorro_minimo = st.number_input(
            "Cantidad mínima de ahorro por reunión",
            min_value=0.0,
            step=1.0,
            value=ahorro_minimo_default,
        )

        st.markdown("---")
        st.markdown("### 8. Condiciones de préstamos")

        condiciones_prestamo = st.text_area(
            "Condiciones de los préstamos",
            value=condiciones_default,
            help=(
                "Ejemplos: tasa de interés, monto máximo, plazo máximo, "
                "solamente un préstamo a la vez, etc."
            ),
            height=120,
        )

        st.markdown("---")
        st.markdown("### 9. Ciclo del grupo")

        fecha_inicio_ciclo = st.date_input(
            "Fecha de inicio de ciclo (fecha del primer depósito)",
            value=fecha_ini_default,
        )

        fecha_fin_ciclo = st.date_input(
            "Fecha de fin de ciclo (6 o 12 meses, según acuerden)",
            value=fecha_fin_default,
        )

        st.markdown("---")
        st.markdown("### 10. Meta social")

        meta_social = st.text_area(
            "Meta social del grupo",
            value=meta_social_default,
            help="Ejemplo: mejorar el ahorro familiar, apoyar a la comunidad, etc.",
            height=120,
        )

        enviado = st.form_submit_button(
            "Guardar reglamento",
            type="primary",
        )

    if enviado:
        # Validaciones sencillas
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return
        if fecha_fin_ciclo <= fecha_inicio_ciclo:
            st.warning("La fecha de fin de ciclo debe ser posterior a la fecha de inicio.")
            return

        ahora = dt.datetime.now()

        if reglamento:
            # UPDATE
            sql = """
                UPDATE reglamento_grupo
                SET Nombre_comunidad = %s,
                    Fecha_formacion   = %s,
                    Reunion_dia       = %s,
                    Reunion_hora      = %s,
                    Reunion_lugar     = %s,
                    Reunion_frecuencia = %s,
                    Monto_multa       = %s,
                    Ahorro_minimo     = %s,
                    Condiciones_prestamo = %s,
                    Fecha_inicio_ciclo = %s,
                    Fecha_fin_ciclo    = %s,
                    Meta_social        = %s,
                    Actualizado_en     = %s
                WHERE Id_reglamento = %s
            """
            execute(
                sql,
                (
                    nombre_comunidad.strip(),
                    fecha_creacion_grupo,
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
                    ahora,
                    reglamento["Id_reglamento"],
                ),
            )
            st.success("Reglamento actualizado correctamente.")
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
                    Creado_en
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """
            execute(
                sql,
                (
                    id_grupo,
                    nombre_comunidad.strip(),
                    fecha_creacion_grupo,
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
                    ahora,
                ),
            )
            st.success("Reglamento guardado correctamente.")
        st.rerun()


# -------------------------------------------------------------------
# Panel principal de DIRECTIVA
# -------------------------------------------------------------------
@require_auth
@has_role("DIRECTIVA")
def directiva_panel():
    info_dir = _obtener_directiva_actual()
    if not info_dir:
        st.error(
            "No se encontró una directiva asociada a este usuario. "
            "Verifica que el DUI exista en la tabla 'directiva'."
        )
        return

    st.title("Panel de Directiva")
    st.caption(
        f"Directiva: {info_dir['Nombre_directiva']} — "
        f"Grupo: {info_dir['Nombre_grupo']}"
    )

    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            "Caja",
            "Ahorro final",
            "Cierre de ciclo",
        ]
    )

    with tabs[0]:
        _seccion_reglamento(info_dir)

    # El resto lo vamos llenando poco a poco
    with tabs[1]:
        st.info("Aquí implementarás el registro de miembros del grupo.")
    with tabs[2]:
        st.info("Aquí implementarás asistencia y multas.")
    with tabs[3]:
        st.info("Aquí implementarás el formulario de caja.")
    with tabs[4]:
        st.info("Aquí implementarás el ahorro final.")
    with tabs[5]:
        st.info("Aquí implementarás el cierre de ciclo.")
