# modulos/directiva/panel.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, fetch_all, execute
from modulos.auth.rbac import get_user, require_auth, has_role


# -------------------------------------------------------
# Helpers de base de datos
# -------------------------------------------------------

def _obtener_info_directiva_actual() -> dict | None:
    """
    Obtiene la información de la directiva logueada y del grupo al que pertenece.
    Se usa el DUI que viene guardado en la sesión (get_user()).
    """
    user = get_user()
    if not user:
        return None

    sql = """
        SELECT 
            u.Id_usuario,
            u.Nombre       AS Usuario,
            u.DUI          AS DUI_usuario,
            d.Id_directiva,
            d.Nombre       AS Nombre_directiva,
            d.Id_grupo,
            g.Nombre       AS Nombre_grupo
        FROM Usuario u
        JOIN directiva d ON d.DUI = u.DUI
        JOIN grupos   g ON g.Id_grupo = d.Id_grupo
        WHERE u.DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (user["DUI"],))


def _obtener_reglamento_por_grupo(id_grupo: int) -> dict | None:
    sql = """
        SELECT *
        FROM reglamento
        WHERE Id_grupo = %s
        LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _parsear_condiciones_prestamo(valor: str) -> tuple[float, float, str, str]:
    """
    Internamente guardamos Condiciones_prestamo como:
    'interes|monto_max|plazo_max|extra'
    para aprovechar tu única columna TEXT.

    Si aún no hay nada guardado, devolvemos valores por defecto.
    """
    if not valor:
        return 0.0, 0.0, "", ""

    partes = valor.split("|")
    try:
        interes = float(partes[0]) if partes[0] else 0.0
    except ValueError:
        interes = 0.0

    try:
        monto_max = float(partes[1]) if len(partes) > 1 and partes[1] else 0.0
    except ValueError:
        monto_max = 0.0

    plazo_max = partes[2] if len(partes) > 2 else ""
    extra = partes[3] if len(partes) > 3 else ""

    return interes, monto_max, plazo_max, extra


def _serializar_condiciones_prestamo(
    interes: float, monto_max: float, plazo_max: str, extra: str
) -> str:
    """
    Convierte los cuatro campos a una sola cadena para la columna TEXT.
    """
    return f"{interes}|{monto_max}|{plazo_max}|{extra}"


# -------------------------------------------------------
# Sección REGLAMENTO
# -------------------------------------------------------

def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglamento del grupo")

    id_grupo = info_dir["Id_grupo"]
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    st.caption(f"Grupo: {info_dir['Nombre_grupo']}")

    # ---- Valores por defecto (si no hay reglamento aún) ----
    nombre_comunidad = ""
    fecha_formacion = dt.date.today()
    reunion_dia = ""
    reunion_hora = ""
    reunion_lugar = ""
    reunion_frecuencia = ""
    monto_multa = 0.0
    ahorro_minimo = 0.0
    interes_10 = 0.0
    prestamo_max = 0.0
    plazo_max = ""
    extra_prestamo = ""
    fecha_inicio_ciclo = dt.date.today()
    fecha_fin_ciclo = dt.date.today()
    meta_social = ""

    id_reglamento = None

    if reglamento:
        id_reglamento = reglamento["Id_reglamento"]
        nombre_comunidad = reglamento["Nombre_comunidad"]
        fecha_formacion = reglamento["Fecha_formacion"]
        reunion_dia = reglamento["Reunion_dia"]
        reunion_hora = reglamento["Reunion_hora"]
        reunion_lugar = reglamento["Reunion_lugar"]
        reunion_frecuencia = reglamento["Reunion_frecuencia"]
        monto_multa = float(reglamento["Monto_multa"])
        ahorro_minimo = float(reglamento["Ahorro_minimo"])
        fecha_inicio_ciclo = reglamento["Fecha_inicio_ciclo"]
        fecha_fin_ciclo = reglamento["Fecha_fin_ciclo"]
        meta_social = reglamento["Meta_social"]

        interes_10, prestamo_max, plazo_max, extra_prestamo = _parsear_condiciones_prestamo(
            reglamento["Condiciones_prestamo"]
        )

    # =======================================================
    # Formulario de reglamento
    # =======================================================
    with st.form("form_reglamento"):

        # 1. Nombre comunidad y fecha formación
        nombre_comunidad = st.text_input(
            "Nombre de la comunidad",
            value=nombre_comunidad,
        )
        fecha_formacion = st.date_input(
            "Fecha en que se formó el grupo de ahorro",
            value=fecha_formacion,
        )

        st.markdown("### Reuniones")
        reunion_dia = st.text_input("Día de reunión", value=reunion_dia)
        reunion_hora = st.text_input("Hora de reunión", value=reunion_hora)
        reunion_lugar = st.text_input("Lugar de reunión", value=reunion_lugar)
        reunion_frecuencia = st.text_input(
            "Frecuencia de la reunión",
            value=reunion_frecuencia,
            help="Ej.: cada 15 días, cada semana, una vez al mes…",
        )

        st.markdown("### Multas y ahorro mínimo")
        monto_multa = st.number_input(
            "Monto de la multa por inasistencia o retraso",
            min_value=0.0,
            step=0.25,
            value=monto_multa,
        )
        ahorro_minimo = st.number_input(
            "Cantidad mínima de ahorro por reunión",
            min_value=0.0,
            step=0.25,
            value=ahorro_minimo,
        )

        st.markdown("### Condiciones de préstamo")

        col1, col2 = st.columns(2)
        with col1:
            interes_10 = st.number_input(
                "Interés que pagamos por cada $10.00 prestados",
                min_value=0.0,
                step=0.1,
                value=interes_10,
                help="Ejemplo: 1 significa que pagamos $1 por cada $10 prestados.",
            )
        with col2:
            prestamo_max = st.number_input(
                "Cantidad máxima de préstamo",
                min_value=0.0,
                step=1.0,
                value=prestamo_max,
            )

        plazo_max = st.text_input(
            "Plazo máximo para devolver el préstamo",
            value=plazo_max,
            help="Ejemplo: '3 meses', '10 reuniones', etc.",
        )
        extra_prestamo = st.text_area(
            "Condiciones adicionales de préstamo",
            value=extra_prestamo,
            height=80,
        )

        st.markdown("### Ciclo y meta social")
        fecha_inicio_ciclo = st.date_input(
            "Fecha de inicio del ciclo (primer depósito)",
            value=fecha_inicio_ciclo,
        )
        fecha_fin_ciclo = st.date_input(
            "Fecha de finalización del ciclo (6 o 12 meses)",
            value=fecha_fin_ciclo,
        )
        meta_social = st.text_area(
            "Meta social",
            value=meta_social,
            help="Describe la meta social del grupo (por ejemplo, actividades comunitarias).",
        )

        guardar = st.form_submit_button("Guardar reglamento")

    # =======================================================
    # Guardar / actualizar reglamento
    # =======================================================

    if guardar:
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        condiciones_serializadas = _serializar_condiciones_prestamo(
            interes_10, prestamo_max, plazo_max, extra_prestamo
        )

        if id_reglamento is None:
            # INSERT
            sql = """
                INSERT INTO reglamento
                (Id_grupo, Nombre_comunidad, Fecha_formacion,
                 Reunion_dia, Reunion_hora, Reunion_lugar, Reunion_frecuencia,
                 Monto_multa, Ahorro_minimo, Condiciones_prestamo,
                 Fecha_inicio_ciclo, Fecha_fin_ciclo, Meta_social)
                VALUES
                (%s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s)
            """
            params = (
                id_grupo,
                nombre_comunidad.strip(),
                fecha_formacion,
                reunion_dia.strip(),
                reunion_hora.strip(),
                reunion_lugar.strip(),
                reunion_frecuencia.strip(),
                monto_multa,
                ahorro_minimo,
                condiciones_serializadas,
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
            )
        else:
            # UPDATE
            sql = """
                UPDATE reglamento
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
                    Meta_social        = %s
                WHERE Id_reglamento = %s
            """
            params = (
                nombre_comunidad.strip(),
                fecha_formacion,
                reunion_dia.strip(),
                reunion_hora.strip(),
                reunion_lugar.strip(),
                reunion_frecuencia.strip(),
                monto_multa,
                ahorro_minimo,
                condiciones_serializadas,
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
                id_reglamento,
            )

        execute(sql, params)
        st.success("Reglamento guardado correctamente.")
        st.experimental_rerun()

    # =======================================================
    # Botón para ELIMINAR reglamento
    # =======================================================

    if id_reglamento is not None:
        st.markdown("---")
        st.warning("Zona peligrosa: eliminar reglamento")
        col_del1, col_del2 = st.columns([1, 2])
        with col_del1:
            confirmar = st.checkbox(
                "Confirmo que deseo eliminar el reglamento de este grupo."
            )
        with col_del2:
            if st.button("Eliminar reglamento"):
                if not confirmar:
                    st.warning("Debes marcar la casilla de confirmación.")
                else:
                    execute(
                        "DELETE FROM reglamento WHERE Id_reglamento = %s",
                        (id_reglamento,),
                    )
                    st.success("Reglamento eliminado correctamente.")
                    st.experimental_rerun()


# -------------------------------------------------------
# PANEL PRINCIPAL DE DIRECTIVA
# -------------------------------------------------------

@require_auth
@has_role("DIRECTIVA")
def directiva_panel():
    """
    Panel que verá el usuario con rol DIRECTIVA.
    Por ahora solo implementamos la pestaña de REGLAMENTO.
    Las demás pestañas quedan como placeholders.
    """
    info_dir = _obtener_info_directiva_actual()
    if not info_dir:
        st.error(
            "No se encontró información de directiva asociada a este usuario. "
            "Verifica que la tabla 'directiva' tenga el DUI correcto."
        )
        return

    st.title("Panel de Directiva")
    st.caption(
        f"Directiva: {info_dir['Nombre_directiva']} — Grupo: {info_dir['Nombre_grupo']}"
    )

    tabs = st.tabs(
        [
            "Reglamento",
            "Asistencia",
            "Ahorros",
            "Préstamos",
            "Caja",
            "Cierre de ciclo",
        ]
    )

    # Pestaña 0: Reglamento
    with tabs[0]:
        _seccion_reglamento(info_dir)

    # Las demás pestañas las iremos implementando después
    with tabs[1]:
        st.info("Aquí se implementará el registro de asistencia.")
    with tabs[2]:
        st.info("Aquí se implementará el registro de ahorros.")
    with tabs[3]:
        st.info("Aquí se implementará el módulo de préstamos.")
    with tabs[4]:
        st.info("Aquí se implementará el manejo de caja.")
    with tabs[5]:
        st.info("Aquí se implementará el cierre de ciclo.")
