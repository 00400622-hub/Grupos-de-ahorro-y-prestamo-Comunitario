# modulos/directiva/panel.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, fetch_all, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# ============================================================
# Helpers de acceso a datos
# ============================================================

def _obtener_info_directiva_actual():
    """
    Devuelve la info de la directiva que está logueada,
    junto con el grupo al que pertenece.
    """
    user = get_user()
    if not user:
        return None

    sql = """
        SELECT
            d.Id_directiva,
            d.Nombre        AS Nombre_directiva,
            d.DUI           AS DUI_directiva,
            d.Creado_en     AS Fecha_creada_directiva,
            g.Id_grupo,
            g.Nombre        AS Nombre_grupo,
            g.Creado_en     AS Fecha_creacion_grupo
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE d.DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (user["DUI"],))


def _obtener_reglamento_por_grupo(id_grupo: int):
    """
    Devuelve el reglamento asociado a un grupo (si existe).
    """
    sql = """
        SELECT
            Id_reglamento,
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
            Plazo_maximo_meses
        FROM reglamento_grupo
        WHERE Id_grupo = %s
        LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _guardar_reglamento(id_grupo: int, datos: dict, id_reglamento: int | None):
    """
    Inserta o actualiza el reglamento para un grupo.
    `datos` debe traer TODAS las columnas de la tabla (excepto Id_reglamento).
    """
    valores = (
        id_grupo,
        datos["Nombre_comunidad"],
        datos["Fecha_formacion"],
        datos["Reunion_dia"],
        datos["Reunion_hora"],
        datos["Reunion_lugar"],
        datos["Reunion_frecuencia"],
        datos["Monto_multa"],
        datos["Ahorro_minimo"],
        datos["Condiciones_prestamo"],
        datos["Fecha_inicio_ciclo"],
        datos["Fecha_fin_ciclo"],
        datos["Meta_social"],
        datos["Interes_por_10"],
        datos["Prestamo_maximo"],
        datos["Plazo_maximo_meses"],
    )

    if id_reglamento is None:
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
                Plazo_maximo_meses
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        execute(sql, valores)
    else:
        # UPDATE
        sql = """
            UPDATE reglamento_grupo
            SET
                Id_grupo             = %s,
                Nombre_comunidad     = %s,
                Fecha_formacion      = %s,
                Reunion_dia          = %s,
                Reunion_hora         = %s,
                Reunion_lugar        = %s,
                Reunion_frecuencia   = %s,
                Monto_multa          = %s,
                Ahorro_minimo        = %s,
                Condiciones_prestamo = %s,
                Fecha_inicio_ciclo   = %s,
                Fecha_fin_ciclo      = %s,
                Meta_social          = %s,
                Interes_por_10       = %s,
                Prestamo_maximo      = %s,
                Plazo_maximo_meses   = %s
            WHERE Id_reglamento = %s
        """
        execute(sql, valores + (id_reglamento,))


def _eliminar_reglamento(id_reglamento: int):
    """
    Elimina el reglamento de la tabla reglamento_grupo.
    (Solo afecta esa tabla, no toca grupos ni directivas).
    """
    execute("DELETE FROM reglamento_grupo WHERE Id_reglamento = %s", (id_reglamento,))


# ============================================================
# UI – Sección Reglamento
# ============================================================

def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglamento del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]

    # Cargar reglamento existente (si hay)
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    st.info(
        f"Estás configurando el reglamento para el grupo "
        f"**{nombre_grupo}** (Id_grupo = {id_grupo})."
    )

    # Fecha de formación = fecha en que se creó el grupo (dato de la tabla grupos)
    fecha_formacion_def = info_dir.get("Fecha_creacion_grupo")
    if isinstance(fecha_formacion_def, dt.datetime):
        fecha_formacion_def = fecha_formacion_def.date()
    if not fecha_formacion_def:
        fecha_formacion_def = dt.date.today()

    # Valores por defecto (reglamento existente o vacío)
    nombre_comunidad = (
        reglamento["Nombre_comunidad"] if reglamento else ""
    )
    reunion_dia = reglamento["Reunion_dia"] if reglamento else ""
    reunion_hora = reglamento["Reunion_hora"] if reglamento else ""
    reunion_lugar = reglamento["Reunion_lugar"] if reglamento else ""
    reunion_frec = reglamento["Reunion_frecuencia"] if reglamento else ""
    monto_multa = float(reglamento["Monto_multa"]) if reglamento else 0.0
    ahorro_minimo = float(reglamento["Ahorro_minimo"]) if reglamento else 0.0
    condiciones_prestamo = (
        reglamento["Condiciones_prestamo"] if reglamento else ""
    )
    fecha_inicio_ciclo = (
        reglamento["Fecha_inicio_ciclo"]
        if reglamento
        else fecha_formacion_def
    )
    fecha_fin_ciclo = (
        reglamento["Fecha_fin_ciclo"]
        if reglamento
        else fecha_formacion_def + dt.timedelta(days=365)
    )
    meta_social = reglamento["Meta_social"] if reglamento else ""
    interes_por_10 = float(reglamento["Interes_por_10"]) if reglamento else 0.0
    prestamo_maximo = float(reglamento["Prestamo_maximo"]) if reglamento else 0.0
    plazo_maximo_meses = int(reglamento["Plazo_maximo_meses"]) if reglamento else 12

    # ------------------------------------------------------------------
    # Formulario
    # ------------------------------------------------------------------
    with st.form("form_reglamento_grupo"):
        st.markdown("### 1. Información general")

        nombre_comunidad = st.text_input(
            "Nombre de la comunidad",
            value=nombre_comunidad,
        )

        st.write("Fecha en que se formó el grupo de ahorro:")
        st.date_input(
            "Fecha en que se formó el grupo de ahorro",
            value=fecha_formacion_def,
            disabled=True,
            label_visibility="collapsed",
        )

        st.markdown("### 2. Reuniones")

        col1, col2 = st.columns(2)
        with col1:
            reunion_dia = st.text_input(
                "Día de reunión",
                value=reunion_dia,
                placeholder="Ejemplo: Lunes",
            )
        with col2:
            reunion_hora = st.text_input(
                "Hora de reunión",
                value=reunion_hora,
                placeholder="Ejemplo: 3:00 p.m.",
            )

        reunion_lugar = st.text_input(
            "Lugar de reunión",
            value=reunion_lugar,
            placeholder="Ejemplo: Casa comunal",
        )

        reunion_frec = st.text_input(
            "Frecuencia de la reunión",
            value=reunion_frec,
            placeholder="Ejemplo: Cada semana / cada 15 días",
        )

        st.markdown("### 3. Multa por inasistencia o retraso")

        monto_multa = st.number_input(
            "Monto de la multa (en dólares)",
            min_value=0.0,
            step=0.25,
            value=monto_multa,
        )

        st.markdown("### 4. Ahorro mínimo")

        ahorro_minimo = st.number_input(
            "Cantidad mínima de ahorro por reunión (USD)",
            min_value=0.0,
            step=0.25,
            value=ahorro_minimo,
        )

        st.markdown("### 5. Préstamos")

        interes_por_10 = st.number_input(
            "Pagamos ___ de interés por cada $10.00 prestados "
            "(tasa de interés por 10 dólares)",
            min_value=0.0,
            step=0.1,
            value=interes_por_10,
        )

        prestamo_maximo = st.number_input(
            "Solamente podemos tomar préstamos hasta la cantidad máxima de",
            min_value=0.0,
            step=10.0,
            value=prestamo_maximo,
        )

        plazo_maximo_meses = st.number_input(
            "Solamente podemos tomar préstamos por un plazo máximo de (meses)",
            min_value=1,
            step=1,
            value=plazo_maximo_meses,
        )

        condiciones_prestamo = st.text_area(
            "Condiciones adicionales de préstamo",
            value=condiciones_prestamo,
            placeholder="Otras condiciones para los préstamos...",
        )

        st.markdown("### 6. Ciclo y meta social")

        colc1, colc2 = st.columns(2)
        with colc1:
            fecha_inicio_ciclo = st.date_input(
                "Fecha de inicio de ciclo",
                value=fecha_inicio_ciclo,
            )
        with colc2:
            fecha_fin_ciclo = st.date_input(
                "Fecha de fin de ciclo",
                value=fecha_fin_ciclo,
            )

        meta_social = st.text_area(
            "Meta social",
            value=meta_social,
            placeholder="Escribe la meta social del grupo...",
        )

        st.markdown("---")
        col_guardar, col_eliminar = st.columns(2)
        with col_guardar:
            btn_guardar = st.form_submit_button("Guardar reglamento", type="primary")
        with col_eliminar:
            btn_eliminar = st.form_submit_button(
                "Eliminar reglamento", type="secondary"
            )

    # ------------------------------------------------------------------
    # Acciones del formulario
    # ------------------------------------------------------------------
    if btn_guardar:
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        datos = {
            "Nombre_comunidad": nombre_comunidad.strip(),
            "Fecha_formacion": fecha_formacion_def,
            "Reunion_dia": reunion_dia.strip(),
            "Reunion_hora": reunion_hora.strip(),
            "Reunion_lugar": reunion_lugar.strip(),
            "Reunion_frecuencia": reunion_frec.strip(),
            "Monto_multa": monto_multa,
            "Ahorro_minimo": ahorro_minimo,
            "Condiciones_prestamo": condiciones_prestamo.strip(),
            "Fecha_inicio_ciclo": fecha_inicio_ciclo,
            "Fecha_fin_ciclo": fecha_fin_ciclo,
            "Meta_social": meta_social.strip(),
            "Interes_por_10": interes_por_10,
            "Prestamo_maximo": prestamo_maximo,
            "Plazo_maximo_meses": plazo_maximo_meses,
        }

        _guardar_reglamento(
            id_grupo=id_grupo,
            datos=datos,
            id_reglamento=(reglamento["Id_reglamento"] if reglamento else None),
        )
        st.success("Reglamento guardado correctamente.")
        st.experimental_rerun()

    if btn_eliminar:
        if not reglamento:
            st.warning("Este grupo todavía no tiene reglamento guardado.")
        else:
            _eliminar_reglamento(reglamento["Id_reglamento"])
            st.success("Reglamento eliminado correctamente.")
            st.experimental_rerun()


# ============================================================
# Panel principal de DIRECTIVA
# ============================================================

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

    st.title("Panel de Directiva")

    st.caption(
        f"Directiva: {info_dir['Nombre_directiva']} — DUI: {info_dir['DUI_directiva']} "
        f"— Grupo: {info_dir['Nombre_grupo']}"
    )

    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            "Multas",
            "Caja",
            "Ahorros finales",
            "Cierre de ciclo",
        ]
    )

    # 1. Reglamento (implementado)
    with tabs[0]:
        _seccion_reglamento(info_dir)

    # 2–7: todavía en construcción, para implementar después
    with tabs[1]:
        st.info("Aquí se implementará el registro de miembros del grupo.")
    with tabs[2]:
        st.info("Aquí se implementará el registro de asistencia.")
    with tabs[3]:
        st.info("Aquí se implementará el manejo de multas.")
    with tabs[4]:
        st.info("Aquí se implementará el formulario de caja.")
    with tabs[5]:
        st.info("Aquí se implementará el formulario de ahorro final.")
    with tabs[6]:
        st.info("Aquí se implementará el formulario de cierre de ciclo.")
