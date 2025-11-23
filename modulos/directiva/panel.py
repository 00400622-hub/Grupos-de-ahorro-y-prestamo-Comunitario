# modulos/directiva/panel.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, execute
from modulos.auth.rbac import get_user, require_auth, has_role


# --------------------------------------------------------------------
# Helpers de base de datos
# --------------------------------------------------------------------
def _obtener_info_directiva():
    """
    Devuelve la información básica de la directiva actualmente logueada
    y el grupo al que pertenece.
    """
    user = get_user()
    if not user:
        return None

    sql = """
        SELECT
            d.Id_directiva,
            d.Nombre,
            d.DUI,
            d.Id_grupo,
            g.Nombre AS Grupo,
            g.Creado_en AS Fecha_creacion_grupo
        FROM directiva d
        JOIN grupos g ON g.Id_grupo = d.Id_grupo
        WHERE d.DUI = %s
        LIMIT 1
    """
    return fetch_one(sql, (user["DUI"],))


def _obtener_reglamento_por_grupo(id_grupo: int):
    """
    Busca si ya existe un reglamento para el grupo.
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
            Meta_social
        FROM reglamento
        WHERE Id_grupo = %s
        LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _guardar_reglamento(
    id_grupo: int,
    nombre_comunidad: str,
    fecha_formacion: dt.date,
    reunion_dia: str,
    reunion_hora: str,
    reunion_lugar: str,
    reunion_frecuencia: str,
    monto_multa: float,
    ahorro_minimo: float,
    texto_condiciones_prestamo: str,
    fecha_inicio_ciclo: dt.date,
    fecha_fin_ciclo: dt.date,
    meta_social: str,
    id_reglamento: int | None = None,
):
    """
    Inserta o actualiza el reglamento de un grupo.
    """
    if id_reglamento is None:
        # INSERT
        sql = """
            INSERT INTO reglamento (
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
                Meta_social
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            id_grupo,
            nombre_comunidad,
            fecha_formacion,
            reunion_dia,
            reunion_hora,
            reunion_lugar,
            reunion_frecuencia,
            monto_multa,
            ahorro_minimo,
            texto_condiciones_prestamo,
            fecha_inicio_ciclo,
            fecha_fin_ciclo,
            meta_social,
        )
    else:
        # UPDATE
        sql = """
            UPDATE reglamento
            SET
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
                Meta_social          = %s
            WHERE Id_reglamento = %s
        """
        params = (
            nombre_comunidad,
            fecha_formacion,
            reunion_dia,
            reunion_hora,
            reunion_lugar,
            reunion_frecuencia,
            monto_multa,
            ahorro_minimo,
            texto_condiciones_prestamo,
            fecha_inicio_ciclo,
            fecha_fin_ciclo,
            meta_social,
            id_reglamento,
        )

    execute(sql, params)


# --------------------------------------------------------------------
# Sección: Reglamento
# --------------------------------------------------------------------
def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglas internas del grupo")

    id_grupo = info_dir["Id_grupo"]

    # Traer reglamento si ya existe
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    # Fecha de formación por defecto = fecha de creación del grupo
    fecha_creacion_grupo = info_dir.get("Fecha_creacion_grupo") or dt.date.today()
    fecha_formacion_default = (
        reglamento["Fecha_formacion"] if reglamento else fecha_creacion_grupo
    )

    # Valores iniciales
    nombre_comunidad = reglamento["Nombre_comunidad"] if reglamento else ""
    reunion_dia = reglamento["Reunion_dia"] if reglamento else ""
    reunion_hora = reglamento["Reunion_hora"] if reglamento else ""
    reunion_lugar = reglamento["Reunion_lugar"] if reglamento else ""
    reunion_frecuencia = reglamento["Reunion_frecuencia"] if reglamento else ""
    monto_multa = float(reglamento["Monto_multa"]) if reglamento else 0.0
    ahorro_minimo = float(reglamento["Ahorro_minimo"]) if reglamento else 0.0
    condiciones_previas = (
        reglamento["Condiciones_prestamo"] if reglamento else ""
    )
    fecha_inicio_ciclo = (
        reglamento["Fecha_inicio_ciclo"] if reglamento else fecha_creacion_grupo
    )
    fecha_fin_ciclo = (
        reglamento["Fecha_fin_ciclo"]
        if reglamento
        else fecha_creacion_grupo.replace(year=fecha_creacion_grupo.year + 1)
    )
    meta_social = reglamento["Meta_social"] if reglamento else ""

    with st.form("form_reglamento"):
        st.markdown("**1. Nombre de la comunidad**")
        nombre_comunidad = st.text_input(
            "Nombre de la comunidad", value=nombre_comunidad
        )

        st.markdown("**2. Fecha en que se formó el grupo de ahorro**")
        fecha_formacion = st.date_input(
            "Fecha en que se formó el grupo de ahorro",
            value=fecha_formacion_default,
            format="YYYY-MM-DD",
        )

        st.markdown("**3. Reuniones**")
        col1, col2 = st.columns(2)
        with col1:
            reunion_dia = st.text_input("Día", value=reunion_dia)
            reunion_lugar = st.text_input("Lugar", value=reunion_lugar)
        with col2:
            reunion_hora = st.text_input("Hora", value=reunion_hora)
            reunion_frecuencia = st.text_input(
                "Frecuencia de la reunión", value=reunion_frecuencia
            )

        st.markdown("**6. Asistencia – Multas**")
        monto_multa = st.number_input(
            "Monto de la multa por faltar a una reunión",
            min_value=0.0,
            step=0.25,
            value=monto_multa,
        )

        st.markdown("**7. Ahorros**")
        ahorro_minimo = st.number_input(
            "Cantidad mínima de ahorros por reunión",
            min_value=0.0,
            step=0.25,
            value=ahorro_minimo,
        )

        st.markdown("**8. Préstamos**")
        interes_por_10 = st.number_input(
            "Pagamos ___ de interés por cada $10.00 prestados.",
            min_value=0.0,
            step=0.1,
            value=0.0,
            help=(
                "Este valor no se guarda en una columna separada, "
                "se incluye en el texto de Condiciones de préstamo."
            ),
        )
        monto_max_prestamo = st.number_input(
            "Solamente podemos tomar préstamos hasta la cantidad máxima de:",
            min_value=0.0,
            step=1.0,
            value=0.0,
        )
        plazo_max_prestamo = st.number_input(
            "Solamente podemos tomar préstamos por un plazo máximo de (meses):",
            min_value=1,
            step=1,
            value=12,
        )
        condiciones_adicionales = st.text_area(
            "Condiciones adicionales de préstamo",
            value=condiciones_previas,
            height=120,
        )

        # Armamos el texto completo que irá a la columna Condiciones_prestamo
        texto_condiciones_prestamo = (
            f"Pagamos {interes_por_10} de interés por cada $10.00 prestados. "
            f"Solamente podemos tomar préstamos hasta la cantidad máxima de "
            f"{monto_max_prestamo}. "
            f"Solamente podemos tomar préstamos por un plazo máximo de "
            f"{plazo_max_prestamo} meses. "
            f"Condiciones adicionales: {condiciones_adicionales}"
        )

        st.markdown("**9. Ciclo**")
        cols_ciclo = st.columns(2)
        with cols_ciclo[0]:
            fecha_inicio_ciclo = st.date_input(
                "Empezamos ciclo el (fecha del primer depósito)",
                value=fecha_inicio_ciclo,
                format="YYYY-MM-DD",
            )
        with cols_ciclo[1]:
            fecha_fin_ciclo = st.date_input(
                "Terminamos el ciclo el (6 o 12 meses)",
                value=fecha_fin_ciclo,
                format="YYYY-MM-DD",
            )

        st.markdown("**10. Meta social**")
        meta_social = st.text_area(
            "Meta social del grupo",
            value=meta_social,
            height=120,
        )

        guardar = st.form_submit_button(
            "Guardar reglamento", type="primary"
        )

    if guardar:
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        _guardar_reglamento(
            id_grupo=id_grupo,
            nombre_comunidad=nombre_comunidad.strip(),
            fecha_formacion=fecha_formacion,
            reunion_dia=reunion_dia.strip(),
            reunion_hora=reunion_hora.strip(),
            reunion_lugar=reunion_lugar.strip(),
            reunion_frecuencia=reunion_frecuencia.strip(),
            monto_multa=monto_multa,
            ahorro_minimo=ahorro_minimo,
            texto_condiciones_prestamo=texto_condiciones_prestamo,
            fecha_inicio_ciclo=fecha_inicio_ciclo,
            fecha_fin_ciclo=fecha_fin_ciclo,
            meta_social=meta_social.strip(),
            id_reglamento=reglamento["Id_reglamento"] if reglamento else None,
        )
        st.success("Reglamento guardado correctamente.")
        st.rerun()

    # Botón para eliminar reglamento
    st.markdown("---")
    if reglamento:
        st.warning("Si eliminas el reglamento deberás volver a registrarlo.")
        col_del1, col_del2 = st.columns([1, 2])
        with col_del1:
            confirmar_del = st.checkbox(
                "Confirmar eliminación del reglamento"
            )
        with col_del2:
            if st.button("Eliminar reglamento", type="secondary"):
                if confirmar_del:
                    execute(
                        "DELETE FROM reglamento WHERE Id_reglamento = %s",
                        (reglamento["Id_reglamento"],),
                    )
                    st.success("Reglamento eliminado correctamente.")
                    st.rerun()
                else:
                    st.warning(
                        "Marca la casilla de confirmación antes de eliminar."
                    )


# --------------------------------------------------------------------
# Panel principal de Directiva
# --------------------------------------------------------------------
@require_auth
@has_role("DIRECTIVA")
def directiva_panel():
    info_dir = _obtener_info_directiva()
    if not info_dir:
        st.error(
            "No se encontró información de directiva asociada a este usuario. "
            "Verifica que el DUI de la directiva exista en la tabla 'directiva'."
        )
        return

    st.title("Panel de Directiva")
    st.caption(
        f"Directiva: {info_dir['Nombre']} — DUI: {info_dir['DUI']} "
        f"— Grupo: {info_dir['Grupo']}"
    )

    pestañas = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Ahorros",
            "Multas",
            "Caja",
            "Cierre de ciclo",
            "Reportes",
        ]
    )

    with pestañas[0]:
        _seccion_reglamento(info_dir)

    # Las demás secciones se implementarán más adelante
    with pestañas[1]:
        st.info("Sección de miembros se implementará más adelante.")
    with pestañas[2]:
        st.info("Sección de ahorros se implementará más adelante.")
    with pestañas[3]:
        st.info("Sección de multas se implementará más adelante.")
    with pestañas[4]:
        st.info("Sección de caja se implementará más adelante.")
    with pestañas[5]:
        st.info("Sección de cierre de ciclo se implementará más adelante.")
    with pestañas[6]:
        st.info("Aquí irán los reportes para la directiva.")
