# modulos/directiva/panel.py (fragmento)

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, execute
from modulos.auth.rbac import has_role, get_user
# ... el resto de imports que ya tienes ...


def _cargar_reglamento_por_grupo(id_grupo: int):
    """
    Devuelve el reglamento del grupo (si existe) como diccionario.
    Usamos SELECT * para evitar problemas si se agregan más columnas.
    """
    return fetch_one(
        "SELECT * FROM reglamento WHERE Id_grupo = %s LIMIT 1",
        (id_grupo,),
    )


def _seccion_reglamento(info_dir: dict):
    """
    Sección de REGLAMENTO dentro del panel de Directiva.
    info_dir debe contener al menos Id_grupo y Nombre del grupo.
    """

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir.get("Grupo", f"Grupo {id_grupo}")

    st.subheader(f"Reglamento del grupo: {nombre_grupo}")

    regl = _cargar_reglamento_por_grupo(id_grupo)

    # -----------------------
    # Valores actuales / por defecto
    # -----------------------
    hoy = dt.date.today()

    nombre_comunidad = st.text_input(
        "1. Nombre de la comunidad",
        value=regl.get("Nombre_comunidad") if regl else "",
    )

    fecha_formacion = st.date_input(
        "2. Fecha en que se formó el grupo de ahorro",
        value=regl.get("Fecha_formacion") or hoy if regl else hoy,
    )

    st.markdown("### 3. Reuniones")

    reunion_dia = st.text_input(
        "Día de la reunión",
        value=regl.get("Reunion_dia") if regl else "",
    )

    reunion_hora = st.text_input(
        "Hora de la reunión",
        value=regl.get("Reunion_hora") if regl else "",
        help="Ejemplo: 3:00 p.m.",
    )

    reunion_lugar = st.text_input(
        "Lugar de la reunión",
        value=regl.get("Reunion_lugar") if regl else "",
    )

    reunion_frecuencia = st.text_input(
        "Frecuencia de la reunión",
        value=regl.get("Reunion_frecuencia") if regl else "",
        help="Ejemplo: Cada 15 días, una vez al mes, etc.",
    )

    st.markdown("### 4. Multa y ahorro mínimo")

    monto_multa = st.number_input(
        "Monto de la multa por inasistencia o atraso ($)",
        min_value=0.0,
        step=0.25,
        value=float(regl.get("Monto_multa") or 0.0) if regl else 0.0,
    )

    ahorro_minimo = st.number_input(
        "Cantidad mínima de ahorro por reunión ($)",
        min_value=0.0,
        step=0.25,
        value=float(regl.get("Ahorro_minimo") or 0.0) if regl else 0.0,
    )

    st.markdown("### 5. Préstamos")

    st.caption("Pagamos interés cuando se cumple el mes.")

    interes_por_10 = st.number_input(
        "Pagamos ___ de interés por cada $10.00 prestados.",
        min_value=0.0,
        step=0.1,
        value=float(regl.get("Interes_por_10") or 0.0) if regl else 0.0,
    )

    prestamo_maximo = st.number_input(
        "Solamente podemos tomar préstamos hasta la cantidad máxima de ($)",
        min_value=0.0,
        step=10.0,
        value=float(regl.get("Prestamo_maximo") or 0.0) if regl else 0.0,
    )

    plazo_maximo_meses = st.number_input(
        "Solamente podemos tomar préstamos por un plazo máximo de (meses)",
        min_value=1,
        step=1,
        value=int(regl.get("Plazo_maximo_meses") or 12) if regl else 12,
    )

    condiciones_prestamo = st.text_area(
        "Condiciones adicionales de préstamo",
        value=regl.get("Condiciones_prestamo") if regl else "",
        height=120,
    )

    st.markdown("### 6. Ciclo y meta social")

    fecha_inicio_ciclo = st.date_input(
        "Fecha de inicio de ciclo (fecha del primer depósito)",
        value=regl.get("Fecha_inicio_ciclo") or hoy if regl else hoy,
    )

    fecha_fin_ciclo = st.date_input(
        "Fecha de fin de ciclo (6 o 12 meses)",
        value=regl.get("Fecha_fin_ciclo") or hoy if regl else hoy,
    )

    meta_social = st.text_area(
        "Meta social",
        value=regl.get("Meta_social") if regl else "",
        height=100,
        help="Describe aquí la meta social del grupo.",
    )

    # -----------------------
    # Guardar / actualizar
    # -----------------------
    if st.button("Guardar reglamento", type="primary"):
        # Validaciones básicas mínimas
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        if regl:
            # UPDATE existente
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
                    Interes_por_10     = %s,
                    Prestamo_maximo    = %s,
                    Plazo_maximo_meses = %s,
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
                interes_por_10,
                prestamo_maximo,
                int(plazo_maximo_meses),
                condiciones_prestamo.strip(),
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
                regl["Id_reglamento"],
            )
            execute(sql, params)
            st.success("Reglamento actualizado correctamente.")
        else:
            # INSERT nuevo
            sql = """
                INSERT INTO reglamento
                (
                    Id_grupo,
                    Nombre_comunidad,
                    Fecha_formacion,
                    Reunion_dia,
                    Reunion_hora,
                    Reunion_lugar,
                    Reunion_frecuencia,
                    Monto_multa,
                    Ahorro_minimo,
                    Interes_por_10,
                    Prestamo_maximo,
                    Plazo_maximo_meses,
                    Condiciones_prestamo,
                    Fecha_inicio_ciclo,
                    Fecha_fin_ciclo,
                    Meta_social
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                interes_por_10,
                prestamo_maximo,
                int(plazo_maximo_meses),
                condiciones_prestamo.strip(),
                fecha_inicio_ciclo,
                fecha_fin_ciclo,
                meta_social.strip(),
            )
            execute(sql, params)
            st.success("Reglamento creado correctamente para este grupo.")

        st.rerun()

    # -----------------------
    # Eliminar reglamento
    # -----------------------
    if regl:
        st.markdown("---")
        st.warning(
            "Si eliminas el reglamento, todos los datos de reglas de este grupo "
            "se perderán y tendrás que volver a registrarlos."
        )
        if st.button("Eliminar reglamento de este grupo", type="secondary"):
            execute(
                "DELETE FROM reglamento WHERE Id_reglamento = %s",
                (regl["Id_reglamento"],),
            )
            st.success("Reglamento eliminado correctamente.")
            st.rerun()
