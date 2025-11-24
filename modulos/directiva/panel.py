# modulos/directiva/panel.py

import datetime as dt
import calendar
import streamlit as st

from modulos.config.conexion import fetch_one, fetch_all, execute
from modulos.auth.rbac import has_role, get_user


# -------------------------------------------------------
# Helpers generales
# -------------------------------------------------------
def _obtener_info_directiva_actual() -> dict | None:
    """
    Devuelve la fila de la directiva asociada al usuario en sesión
    (se busca por el DUI del usuario) junto con info del grupo.
    """
    user = get_user()
    if not user:
        return None

    dui = (user.get("DUI") or "").strip()
    if not dui:
        return None

    sql = """
    SELECT 
        d.Id_directiva,
        d.Nombre,
        d.DUI,
        d.Id_grupo,
        g.Nombre AS Nombre_grupo
    FROM directiva d
    JOIN grupos g ON g.Id_grupo = d.Id_grupo
    WHERE d.DUI = %s
    LIMIT 1
    """
    return fetch_one(sql, (dui,))


def _obtener_reglamento_por_grupo(id_grupo: int) -> dict | None:
    sql = """
    SELECT *
    FROM reglamento_grupo
    WHERE Id_grupo = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _obtener_miembros_grupo(id_grupo: int):
    sql = """
    SELECT 
        Id_miembro,
        Nombre,
        DUI,
        Cargo,
        Sexo
    FROM miembros
    WHERE Id_grupo = %s
    ORDER BY Cargo, Nombre
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_reuniones_de_grupo(id_grupo: int):
    sql = """
    SELECT
        Id_reunion,
        Fecha,
        Numero_reunion,
        Tema
    FROM reuniones_grupo
    WHERE Id_grupo = %s
    ORDER BY Fecha, Numero_reunion
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_reunion_por_id(id_reunion: int) -> dict | None:
    sql = """
    SELECT Id_reunion, Id_grupo, Fecha, Numero_reunion, Tema
    FROM reuniones_grupo
    WHERE Id_reunion = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_reunion,))


def _sumar_meses(fecha: dt.date, meses: int) -> dt.date:
    """Suma 'meses' meses a una fecha sin usar librerías externas."""
    year = fecha.year + (fecha.month - 1 + meses) // 12
    month = (fecha.month - 1 + meses) % 12 + 1
    day = min(fecha.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def _sumar_float(sql: str, params=()) -> float:
    """Ejecuta un SUM(...) AS suma y devuelve 0.0 si es NULL."""
    fila = fetch_one(sql, params)
    if not fila or fila.get("suma") is None:
        return 0.0
    try:
        return float(fila["suma"])
    except Exception:
        return 0.0


# -------------------------------------------------------
# Helpers de Caja
# -------------------------------------------------------
def _obtener_caja_por_reunion(id_grupo: int, id_reunion: int) -> dict | None:
    sql = """
    SELECT *
    FROM caja_reunion
    WHERE Id_grupo = %s AND Id_reunion = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo, id_reunion))


def _obtener_saldo_cierre_anterior(id_grupo: int, fecha_reunion: dt.date) -> float:
    """
    Devuelve el saldo de cierre de la caja de la reunión inmediatamente anterior
    (por fecha) para el grupo. Si no hay, devuelve 0.
    """
    sql = """
    SELECT cr.Saldo_cierre AS saldo
    FROM caja_reunion cr
    JOIN reuniones_grupo rg ON rg.Id_reunion = cr.Id_reunion
    WHERE cr.Id_grupo = %s
      AND rg.Fecha < %s
    ORDER BY rg.Fecha DESC, rg.Numero_reunion DESC
    LIMIT 1
    """
    fila = fetch_one(sql, (id_grupo, fecha_reunion))
    if fila and fila.get("saldo") is not None:
        try:
            return float(fila["saldo"])
        except Exception:
            return 0.0
    return 0.0


def _obtener_saldo_caja_actual(id_grupo: int) -> float:
    """
    Devuelve el último saldo de cierre registrado en caja_reunion para el grupo.
    Se usa como disponibilidad de caja para nuevos préstamos.
    """
    sql = """
    SELECT Saldo_cierre AS saldo
    FROM caja_reunion
    WHERE Id_grupo = %s
    ORDER BY Id_caja DESC
    LIMIT 1
    """
    fila = fetch_one(sql, (id_grupo,))
    if fila and fila.get("saldo") is not None:
        try:
            return float(fila["saldo"])
        except Exception:
            return 0.0
    return 0.0


# -------------------------------------------------------
# Helpers de Cierre de ciclo
# -------------------------------------------------------
def _tiene_prestamos_pendientes(id_grupo: int) -> bool:
    """
    True si existe al menos un préstamo del grupo con saldo pendiente.
    """
    sql = """
    SELECT 
        p.Id_prestamo,
        p.Total_pagar,
        COALESCE(SUM(pp.Capital_pagado + pp.Interes_pagado), 0) AS Pagado
    FROM prestamos_miembro p
    LEFT JOIN pagos_prestamo pp ON pp.Id_prestamo = p.Id_prestamo
    WHERE p.Id_grupo = %s
    GROUP BY p.Id_prestamo, p.Total_pagar
    HAVING Pagado < p.Total_pagar - 0.01
    """
    filas = fetch_all(sql, (id_grupo,))
    return bool(filas)


def _tiene_multas_pendientes(id_grupo: int) -> bool:
    """
    True si hay multas NO pagadas en el grupo.
    """
    sql = """
    SELECT COUNT(*) AS c
    FROM multas_miembro
    WHERE Id_grupo = %s AND Pagada = 0
    """
    fila = fetch_one(sql, (id_grupo,))
    return bool(fila and fila.get("c", 0) > 0)


def _obtener_cierres_ciclo_grupo(id_grupo: int):
    """
    Devuelve todos los cierres de ciclo del grupo (historial).
    """
    sql = """
    SELECT 
        Id_cierre,
        Id_grupo,
        Fecha_cierre,
        Fecha_inicio_ciclo,
        Fecha_fin_ciclo,
        Total_ahorro_grupo,
        Porcion_fondo_grupo
    FROM cierres_ciclo
    WHERE Id_grupo = %s
    ORDER BY Fecha_cierre DESC, Id_cierre DESC
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_detalle_cierre(id_cierre: int):
    """
    Devuelve el detalle por miembro de un cierre de ciclo.
    """
    sql = """
    SELECT 
        ccm.Id_cierre_miembro,
        ccm.Id_miembro,
        m.Nombre,
        m.Cargo,
        ccm.Total_ahorrado_ciclo,
        ccm.Total_correspondiente,
        ccm.Retiro_cierre,
        ccm.Saldo_siguiente_ciclo
    FROM cierres_ciclo_miembros ccm
    JOIN miembros m ON m.Id_miembro = ccm.Id_miembro
    WHERE ccm.Id_cierre = %s
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_cierre,))


def _obtener_totales_ahorro_ciclo(
    id_grupo: int,
    fecha_inicio: dt.date,
    fecha_fin: dt.date,
):
    """
    Calcula, para cada miembro, el total ahorrado durante el ciclo
    [fecha_inicio, fecha_fin].
    """
    sql = """
    SELECT 
        m.Id_miembro,
        m.Nombre,
        m.Cargo,
        COALESCE(SUM(
            COALESCE(a.Ahorro, 0)
          + COALESCE(a.Otras_actividades, 0)
          - COALESCE(a.Retiros, 0)
        ), 0) AS Total_ahorrado
    FROM miembros m
    LEFT JOIN ahorros_miembros a
        ON a.Id_miembro = m.Id_miembro
       AND a.Id_grupo = m.Id_grupo
    LEFT JOIN reuniones_grupo rg
        ON rg.Id_reunion = a.Id_reunion
    WHERE m.Id_grupo = %s
      AND (rg.Fecha IS NULL OR (rg.Fecha BETWEEN %s AND %s))
    GROUP BY m.Id_miembro, m.Nombre, m.Cargo
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_grupo, fecha_inicio, fecha_fin))


def _actualizar_saldo_final_ultimo_ahorro(
    id_grupo: int, id_miembro: int, nuevo_saldo: float
):
    """
    Actualiza el Saldo_final del último registro de ahorros_miembros
    del miembro (para que sea saldo inicial del siguiente ciclo).
    """
    sql_sel = """
    SELECT Id_ahorro
    FROM ahorros_miembros
    WHERE Id_grupo = %s AND Id_miembro = %s
    ORDER BY Id_reunion DESC, Id_ahorro DESC
    LIMIT 1
    """
    fila = fetch_one(sql_sel, (id_grupo, id_miembro))
    if not fila:
        return

    sql_up = """
    UPDATE ahorros_miembros
    SET Saldo_final = %s
    WHERE Id_ahorro = %s
    """
    execute(sql_up, (nuevo_saldo, fila["Id_ahorro"]))


# -------------------------------------------------------
# Sección: Reglamento de grupo
# -------------------------------------------------------
def _seccion_reglamento(info_dir: dict):
    st.subheader("Reglamento del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]

    st.caption(f"Grupo: **{nombre_grupo}** — Id_grupo: {id_grupo}")

    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    # -------- Formulario --------
    with st.form("form_reglamento_grupo"):
        # Datos básicos
        nombre_comunidad = st.text_input(
            "Nombre de la comunidad",
            value=(reglamento.get("Nombre_comunidad") if reglamento else ""),
        )

        # Fecha de formación del grupo
        if reglamento and reglamento.get("Fecha_formacion"):
            fecha_formacion = st.date_input(
                "Fecha en que se formó el grupo de ahorro",
                value=reglamento["Fecha_formacion"],
            )
        else:
            fecha_formacion = st.date_input(
                "Fecha en que se formó el grupo de ahorro",
                value=dt.date.today(),
            )

        st.markdown("### Reuniones")
        reunion_dia = st.text_input(
            "Día de la reunión",
            value=(reglamento.get("Reunion_dia") if reglamento else ""),
        )
        reunion_hora = st.text_input(
            "Hora de la reunión",
            value=(reglamento.get("Reunion_hora") if reglamento else ""),
            help="Ejemplo: 3:00 p.m.",
        )
        reunion_lugar = st.text_input(
            "Lugar de la reunión",
            value=(reglamento.get("Reunion_lugar") if reglamento else ""),
        )
        reunion_frecuencia = st.text_input(
            "Frecuencia de la reunión",
            value=(reglamento.get("Reunion_frecuencia") if reglamento else ""),
            help="Ejemplo: semanal, quincenal, mensual…",
        )

        st.markdown("### Multas y ahorro mínimo")
        monto_multa = st.number_input(
            "Monto de la multa por inasistencia o llegadas tarde ($)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=float(reglamento["Monto_multa"])
            if reglamento and reglamento.get("Monto_multa") is not None
            else 0.0,
        )

        ahorro_minimo = st.number_input(
            "Cantidad mínima de ahorro por reunión ($)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=float(reglamento["Ahorro_minimo"])
            if reglamento and reglamento.get("Ahorro_minimo") is not None
            else 0.0,
        )

        st.markdown("### Préstamos")
        interes_por_10 = st.number_input(
            "Pagamos ____ de interés por cada $10.00 prestados (por período)",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            value=float(reglamento["Interes_por_10"])
            if reglamento and reglamento.get("Interes_por_10") is not None
            else 0.0,
        )

        prestamo_maximo = st.number_input(
            "Solamente podemos tomar préstamos hasta la cantidad máxima de ($)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
            value=float(reglamento["Prestamo_maximo"])
            if reglamento and reglamento.get("Prestamo_maximo") is not None
            else 0.0,
        )

        plazo_maximo_meses = st.number_input(
            "Solamente podemos tomar préstamos por un plazo máximo de (meses)",
            min_value=1,
            step=1,
            value=int(reglamento["Plazo_maximo_meses"])
            if reglamento and reglamento.get("Plazo_maximo_meses") is not None
            else 6,
        )

        condiciones_prestamo = st.text_area(
            "Condiciones adicionales de préstamo",
            value=(reglamento.get("Condiciones_prestamo") if reglamento else ""),
            placeholder=(
                "Ejemplo: solo podemos tener un préstamo a la vez, "
                "requisitos especiales, garantías, etc."
            ),
        )

        st.markdown("### Ciclo y meta social")
        if reglamento and reglamento.get("Fecha_inicio_ciclo"):
            fecha_inicio_ciclo = st.date_input(
                "Fecha de inicio del ciclo (primer depósito)",
                value=reglamento["Fecha_inicio_ciclo"],
            )
        else:
            fecha_inicio_ciclo = st.date_input(
                "Fecha de inicio del ciclo (primer depósito)",
                value=dt.date.today(),
            )

        if reglamento and reglamento.get("Fecha_fin_ciclo"):
            fecha_fin_ciclo = st.date_input(
                "Fecha estimada de cierre del ciclo",
                value=reglamento["Fecha_fin_ciclo"],
            )
        else:
            fecha_fin_ciclo = st.date_input(
                "Fecha estimada de cierre del ciclo",
                value=dt.date.today().replace(year=dt.date.today().year + 1),
            )

        meta_social = st.text_area(
            "Meta social del grupo",
            value=(reglamento.get("Meta_social") if reglamento else ""),
            placeholder="Ejemplo: actividades comunitarias, apoyo a la escuela, etc.",
        )

        if reglamento:
            col1, col2 = st.columns(2)
            with col1:
                guardar = st.form_submit_button("Actualizar reglamento")
            with col2:
                eliminar = st.form_submit_button(
                    "Eliminar reglamento", type="secondary"
                )
        else:
            guardar = st.form_submit_button("Guardar reglamento")
            eliminar = False

    # -------- Lógica de guardado / borrado --------
    if guardar:
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        if reglamento is None:
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
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    plazo_maximo_meses,
                ),
            )
            st.success("Reglamento creado correctamente.")
        else:
            sql = """
            UPDATE reglamento_grupo
            SET
                Nombre_comunidad = %s,
                Fecha_formacion = %s,
                Reunion_dia = %s,
                Reunion_hora = %s,
                Reunion_lugar = %s,
                Reunion_frecuencia = %s,
                Monto_multa = %s,
                Ahorro_minimo = %s,
                Condiciones_prestamo = %s,
                Fecha_inicio_ciclo = %s,
                Fecha_fin_ciclo = %s,
                Meta_social = %s,
                Interes_por_10 = %s,
                Prestamo_maximo = %s,
                Plazo_maximo_meses = %s
            WHERE Id_reglamento = %s
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
                    plazo_maximo_meses,
                    reglamento["Id_reglamento"],
                ),
            )
            st.success("Reglamento actualizado correctamente.")

        st.rerun()

    if eliminar and reglamento:
        execute(
            "DELETE FROM reglamento_grupo WHERE Id_reglamento = %s",
            (reglamento["Id_reglamento"],),
        )
        st.success("Reglamento eliminado correctamente.")
        st.rerun()


# -------------------------------------------------------
# Sección: Miembros del grupo
# -------------------------------------------------------
def _seccion_miembros(info_dir: dict):
    st.subheader("Miembros del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]

    st.caption(f"Grupo: **{nombre_grupo}** — Id_grupo: {id_grupo}")
    st.write(
        "En esta sección se registran todas las personas que forman parte del grupo "
        "(directiva y asociados). Más adelante se usarán para asistencia, multas, "
        "ahorros, préstamos, etc."
    )

    miembros = _obtener_miembros_grupo(id_grupo)

    # -------- Formulario para agregar miembro --------
    st.markdown("### Agregar nuevo miembro")

    cargos_posibles = [
        "Presidenta",
        "Secretaria",
        "Tesorera",
        "Vocal",
        "Comité de crédito",
        "Comité de educación",
        "Asociado",
    ]

    with st.form("form_nuevo_miembro"):
        nombre_m = st.text_input("Nombre completo del miembro")
        dui_m = st.text_input("DUI del miembro (con o sin guiones)")
        cargo_m = st.selectbox("Cargo dentro del grupo", cargos_posibles)
        sexo_m = st.selectbox("Sexo", ["Femenino", "Masculino", "Otro"])

        btn_agregar = st.form_submit_button("Guardar miembro")

    if btn_agregar:
        if not nombre_m.strip() or not dui_m.strip():
            st.warning("Debes completar el nombre y el DUI del miembro.")
        else:
            execute(
                """
                INSERT INTO miembros (Id_grupo, Nombre, DUI, Cargo, Sexo)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_grupo, nombre_m.strip(), dui_m.strip(), cargo_m, sexo_m),
            )
            st.success("Miembro registrado correctamente.")
            st.rerun()

    # -------- Listado y eliminación --------
    st.markdown("---")
    st.markdown("### Miembros registrados en el grupo")

    if miembros:
        st.table(miembros)

        etiquetas = {
            f"{m['Id_miembro']} - {m['Nombre']} ({m['Cargo']})": m["Id_miembro"]
            for m in miembros
        }

        seleccion_eliminar = st.multiselect(
            "Selecciona miembros a eliminar",
            list(etiquetas.keys()),
        )

        if st.button("Eliminar miembros seleccionados", type="secondary"):
            if not seleccion_eliminar:
                st.warning("No has seleccionado ningún miembro para eliminar.")
            else:
                ids_a_borrar = [etiquetas[e] for e in seleccion_eliminar]

                for mid in ids_a_borrar:
                    # 1) Borrar pagos de préstamos del miembro
                    prestamos_m = fetch_all(
                        "SELECT Id_prestamo FROM prestamos_miembro WHERE Id_miembro = %s",
                        (mid,),
                    )
                    for p in prestamos_m:
                        execute(
                            "DELETE FROM pagos_prestamo WHERE Id_prestamo = %s",
                            (p["Id_prestamo"],),
                        )

                    # 2) Borrar préstamos del miembro
                    execute(
                        "DELETE FROM prestamos_miembro WHERE Id_miembro = %s",
                        (mid,),
                    )

                    # 3) Borrar ahorros del miembro
                    execute(
                        "DELETE FROM ahorros_miembros WHERE Id_miembro = %s",
                        (mid,),
                    )

                    # 4) Borrar multas del miembro
                    execute(
                        "DELETE FROM multas_miembro WHERE Id_miembro = %s",
                        (mid,),
                    )

                    # 5) Borrar asistencias del miembro
                    execute(
                        "DELETE FROM asistencia_miembro WHERE Id_miembro = %s",
                        (mid,),
                    )

                    # 6) Finalmente borrar el miembro
                    execute(
                        "DELETE FROM miembros WHERE Id_miembro = %s",
                        (mid,),
                    )

                st.success(
                    "Miembros y sus registros asociados fueron eliminados correctamente."
                )
                st.rerun()
    else:
        st.info("Aún no se han registrado miembros para este grupo.")


# -------------------------------------------------------
# Sección: Asistencia (con multas automáticas)
# -------------------------------------------------------
def _obtener_asistencia_de_reunion(id_reunion: int):
    sql = """
    SELECT 
        a.Id_asistencia,
        a.Id_miembro,
        m.Nombre,
        m.Cargo,
        m.Sexo,
        a.Presente
    FROM asistencia_miembro a
    JOIN miembros m ON m.Id_miembro = a.Id_miembro
    WHERE a.Id_reunion = %s
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_reunion,))


def _crear_multa_inasistencia(
    id_grupo: int,
    id_miembro: int,
    fecha_multa: dt.date,
    monto_multa: float,
):
    """
    Crea una multa por inasistencia si no existe ya una multa
    para ese miembro, grupo y fecha.
    """
    if monto_multa <= 0:
        return

    sql_busca = """
    SELECT Id_multa
    FROM multas_miembro
    WHERE Id_grupo = %s AND Id_miembro = %s AND Fecha_multa = %s
    LIMIT 1
    """
    existe = fetch_one(sql_busca, (id_grupo, id_miembro, fecha_multa))
    if existe:
        return

    sql_ins = """
    INSERT INTO multas_miembro
        (Id_grupo, Id_miembro, Fecha_multa, Monto, Pagada, Fecha_pago)
    VALUES (%s, %s, %s, %s, 0, NULL)
    """
    execute(sql_ins, (id_grupo, id_miembro, fecha_multa, monto_multa))


def _seccion_asistencia(info_dir: dict):
    st.subheader("Asistencia")

    id_grupo = info_dir["Id_grupo"]
    reuniones = _obtener_reuniones_de_grupo(id_grupo)
    miembros = _obtener_miembros_grupo(id_grupo)
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    if not miembros:
        st.info("Primero debes registrar miembros.")
        return

    st.markdown("#### 1. Seleccionar o crear reunión")

    # ---- Select de reuniones existentes ----
    id_reunion_sel = None
    opciones_reu = {}
    if reuniones:
        opciones_reu = {
            f"{r['Fecha']} - Reunión {r['Numero_reunion']} ({r['Tema']})": r[
                "Id_reunion"
            ]
            for r in reuniones
        }
        id_reunion_sel = st.selectbox(
            "Reuniones creadas",
            list(opciones_reu.values()),
            format_func=lambda rid: next(
                k for k, v in opciones_reu.items() if v == rid
            ),
            key="reunion_existente",
        )

    st.markdown("##### Crear nueva reunión")

    with st.form("form_reunion"):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input(
                "Fecha de la reunión", value=dt.date.today(), key="fecha_reu_nueva"
            )
        with col2:
            numero = st.number_input(
                "Número de reunión", min_value=1, step=1, value=1, key="num_reu_nueva"
            )
        tema = st.text_input("Tema / Comentarios de la reunión", "", key="tema_reu")
        btn_crear_reunion = st.form_submit_button("Crear reunión")

    if btn_crear_reunion:
        sql_busca = """
        SELECT Id_reunion
        FROM reuniones_grupo
        WHERE Id_grupo = %s AND Fecha = %s AND Numero_reunion = %s
        LIMIT 1
        """
        existente = fetch_one(sql_busca, (id_grupo, fecha, numero))
        if existente:
            id_reunion_sel = existente["Id_reunion"]
        else:
            sql_ins = """
            INSERT INTO reuniones_grupo (Fecha, Numero_reunion, Tema, Id_grupo)
            VALUES (%s, %s, %s, %s)
            """
            execute(sql_ins, (fecha, numero, tema.strip(), id_grupo))
            existente = fetch_one(sql_busca, (id_grupo, fecha, numero))
            id_reunion_sel = existente["Id_reunion"]

        st.session_state["reunion_abierta"] = id_reunion_sel
        st.success(f"Reunión creada (Id_reunion = {id_reunion_sel}).")
        st.rerun()

    # Si hay en session_state, tiene prioridad
    id_reunion_sel = st.session_state.get("reunion_abierta") or id_reunion_sel

    if not id_reunion_sel:
        st.info("Selecciona una reunión existente o crea una nueva.")
        return

    info_reu = _obtener_reunion_por_id(id_reunion_sel)
    st.markdown(
        f"**Reunión actual:** Id_reunion = {id_reunion_sel} — Fecha: {info_reu['Fecha']} — "
        f"N° {info_reu['Numero_reunion']} — {info_reu['Tema']}"
    )

    # ---- Formulario de asistencia ----
    st.markdown("#### 2. Marcar asistencia de miembros")

    registros = _obtener_asistencia_de_reunion(id_reunion_sel)
    presentes_dict = {r["Id_miembro"]: bool(r["Presente"]) for r in registros}

    with st.form("form_asistencia_miembros"):
        nuevos_presentes: dict[int, bool] = {}

        for m in miembros:
            mid = m["Id_miembro"]
            etiqueta = f"{m['Nombre']} ({m['Cargo']} - {m['Sexo']})"
            valor_default = presentes_dict.get(mid, False)
            nuevos_presentes[mid] = st.checkbox(etiqueta, value=valor_default)

        guardar_asistencia = st.form_submit_button("Guardar asistencia")

    if guardar_asistencia:
        monto_multa = 0.0
        if reglamento and reglamento.get("Monto_multa") is not None:
            try:
                monto_multa = float(reglamento["Monto_multa"])
            except Exception:
                monto_multa = 0.0

        for mid, presente in nuevos_presentes.items():
            sql_sel = """
            SELECT Id_asistencia
            FROM asistencia_miembro
            WHERE Id_reunion = %s AND Id_miembro = %s
            LIMIT 1
            """
            existente = fetch_one(sql_sel, (id_reunion_sel, mid))
            if existente:
                sql_up = """
                UPDATE asistencia_miembro
                SET Presente = %s
                WHERE Id_asistencia = %s
                """
                execute(sql_up, (1 if presente else 0, existente["Id_asistencia"]))
            else:
                sql_ins = """
                INSERT INTO asistencia_miembro (Id_reunion, Id_miembro, Presente)
                VALUES (%s, %s, %s)
                """
                execute(sql_ins, (id_reunion_sel, mid, 1 if presente else 0))

            # Multa automática por inasistencia
            if not presente and monto_multa > 0 and info_reu:
                _crear_multa_inasistencia(
                    id_grupo=id_grupo,
                    id_miembro=mid,
                    fecha_multa=info_reu["Fecha"],
                    monto_multa=monto_multa,
                )

        st.success(
            "Asistencia guardada correctamente (y multas de inasistencia generadas)."
        )
        st.rerun()

    # ---- Resumen de la reunión ----
    st.markdown("#### 3. Resumen de asistencia")

    registros = _obtener_asistencia_de_reunion(id_reunion_sel)
    if registros:
        st.table(registros)
        total = len(registros)
        presentes = sum(1 for r in registros if r["Presente"])
        st.write(f"Fecha de la reunión: **{info_reu['Fecha']}**")
        st.write(f"Total de miembros registrados: **{total}**")
        st.write(f"Asistieron: **{presentes}** — No asistieron: **{total - presentes}**")
    else:
        st.info("Todavía no se ha registrado asistencia para esta reunión.")


# -------------------------------------------------------
# Sección: Multas
# -------------------------------------------------------
def _obtener_multas_de_grupo(id_grupo: int):
    sql = """
    SELECT 
        mm.Id_multa,
        mm.Id_miembro,
        m.Nombre,
        m.Cargo,
        mm.Fecha_multa,
        mm.Monto,
        mm.Pagada,
        mm.Fecha_pago
    FROM multas_miembro mm
    JOIN miembros m ON m.Id_miembro = mm.Id_miembro
    WHERE mm.Id_grupo = %s
    ORDER BY mm.Fecha_multa DESC, mm.Id_multa DESC
    """
    return fetch_all(sql, (id_grupo,))


def _seccion_multas(info_dir: dict):
    st.subheader("Multas")

    id_grupo = info_dir["Id_grupo"]
    miembros = _obtener_miembros_grupo(id_grupo)
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    monto_default = 0.0
    if reglamento and reglamento.get("Monto_multa") is not None:
        try:
            monto_default = float(reglamento["Monto_multa"])
        except Exception:
            monto_default = 0.0

    if not miembros:
        st.info("Primero debes registrar miembros para poder asignar multas.")
        return

    st.markdown(
        "Las multas por inasistencia se generan automáticamente al guardar la "
        "asistencia (cuando un miembro aparece como NO presente). "
        "Aquí puedes registrar multas especiales y gestionarlas."
    )

    # -------- Registrar multa manual --------
    st.markdown("### Registrar nueva multa manual")

    opciones_miembro = {
        f"{m['Nombre']} ({m['Cargo']})": m["Id_miembro"] for m in miembros
    }

    with st.form("form_multas"):
        miembro_label = st.selectbox(
            "Miembro",
            list(opciones_miembro.keys()),
        )
        id_miembro_sel = opciones_miembro[miembro_label]

        fecha_multa = st.date_input("Fecha de la multa", value=dt.date.today())

        monto = st.number_input(
            "Monto de la multa ($)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=monto_default,
        )

        pagada = st.checkbox("¿Multa pagada?")
        fecha_pago = None
        if pagada:
            fecha_pago = st.date_input(
                "Fecha de pago de la multa", value=dt.date.today()
            )

        guardar_multa = st.form_submit_button("Guardar multa")

    if guardar_multa:
        sql = """
        INSERT INTO multas_miembro
            (Id_grupo, Id_miembro, Fecha_multa, Monto, Pagada, Fecha_pago)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute(
            sql,
            (
                id_grupo,
                id_miembro_sel,
                fecha_multa,
                monto,
                1 if pagada else 0,
                fecha_pago,
            ),
        )
        st.success("Multa registrada correctamente.")
        st.rerun()

    # -------- Listado y gestión de multas --------
    st.markdown("---")
    st.markdown("### Multas registradas")

    multas = _obtener_multas_de_grupo(id_grupo)
    if not multas:
        st.info("Todavía no hay multas registradas para este grupo.")
        return

    st.table(multas)

    # Marcar una multa como pagada
    pendientes = [m for m in multas if not m["Pagada"]]
    if pendientes:
        opciones_pend = {
            f"#{m['Id_multa']} - {m['Nombre']} - ${m['Monto']} ({m['Fecha_multa']})": m[
                "Id_multa"
            ]
            for m in pendientes
        }

        st.markdown("#### Marcar multa como pagada")
        with st.form("form_marcar_pagada"):
            label_sel = st.selectbox("Multa pendiente", list(opciones_pend.keys()))
            id_multa_sel = opciones_pend[label_sel]
            fecha_pago2 = st.date_input(
                "Fecha de pago", value=dt.date.today(), key="fecha_pago_multa"
            )
            btn_pagar = st.form_submit_button("Marcar como pagada")

        if btn_pagar:
            sql_up = """
            UPDATE multas_miembro
            SET Pagada = 1, Fecha_pago = %s
            WHERE Id_multa = %s
            """
            execute(sql_up, (fecha_pago2, id_multa_sel))
            st.success("Multa actualizada como pagada.")
            st.rerun()
    else:
        st.info("Todas las multas están pagadas actualmente.")


# -------------------------------------------------------
# Sección: Ahorro final
# Tabla: ahorros_miembros
# -------------------------------------------------------
def _obtener_ahorros_de_reunion(id_grupo: int, id_reunion: int):
    sql = """
    SELECT 
        a.Id_ahorro,
        a.Id_miembro,
        m.Nombre,
        m.Cargo,
        a.Saldo_inicial,
        a.Ahorro,
        a.Otras_actividades,
        a.Retiros,
        a.Saldo_final
    FROM ahorros_miembros a
    JOIN miembros m ON m.Id_miembro = a.Id_miembro
    WHERE a.Id_grupo = %s
      AND a.Id_reunion = %s
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_grupo, id_reunion))


def _obtener_ultimo_saldo_miembro(id_grupo: int, id_miembro: int):
    sql = """
    SELECT Saldo_final
    FROM ahorros_miembros
    WHERE Id_grupo = %s AND Id_miembro = %s
    ORDER BY Id_reunion DESC, Id_ahorro DESC
    LIMIT 1
    """
    fila = fetch_one(sql, (id_grupo, id_miembro))
    if fila and fila.get("Saldo_final") is not None:
        try:
            return float(fila["Saldo_final"])
        except Exception:
            return 0.0
    return 0.0


def _seccion_ahorro_final(info_dir: dict):
    st.subheader("Ahorro final")

    id_grupo = info_dir["Id_grupo"]
    reuniones = _obtener_reuniones_de_grupo(id_grupo)
    miembros = _obtener_miembros_grupo(id_grupo)
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    if not miembros:
        st.info("Primero debes registrar miembros.")
        return

    if not reuniones:
        st.info("Todavía no hay reuniones registradas. Crea al menos una en Asistencia.")
        return

    ahorro_minimo = 0.0
    if reglamento and reglamento.get("Ahorro_minimo") is not None:
        try:
            ahorro_minimo = float(reglamento["Ahorro_minimo"])
        except Exception:
            ahorro_minimo = 0.0

    opciones_reu = {
        f"{r['Fecha']} - Reunión {r['Numero_reunion']} ({r['Tema']})": r["Id_reunion"]
        for r in reuniones
    }

    st.markdown("### Seleccionar reunión para registrar ahorros")

    id_reunion_sel = st.selectbox(
        "Reunión",
        list(opciones_reu.values()),
        format_func=lambda rid: next(
            k for k, v in opciones_reu.items() if v == rid
        ),
        key="reunion_ahorro",
    )

    info_reu = _obtener_reunion_por_id(id_reunion_sel)
    st.markdown(
        f"Reunión seleccionada: **Id_reunion = {id_reunion_sel}**, "
        f"Fecha: **{info_reu['Fecha']}**, Tema: **{info_reu['Tema']}**"
    )

    registros = _obtener_ahorros_de_reunion(id_grupo, id_reunion_sel)
    registros_dict = {r["Id_miembro"]: r for r in registros}

    st.markdown("### Registro de ahorros por miembro")

    with st.form("form_ahorro_final"):
        datos_form = {}

        for m in miembros:
            mid = m["Id_miembro"]
            st.markdown(f"**{m['Nombre']} ({m['Cargo']})**")

            registro_existente = registros_dict.get(mid)

            # Saldo inicial:
            if registro_existente:
                saldo_inicial = float(registro_existente["Saldo_inicial"])
            else:
                saldo_prev = _obtener_ultimo_saldo_miembro(id_grupo, mid)
                if saldo_prev > 0:
                    saldo_inicial = saldo_prev
                else:
                    saldo_inicial = ahorro_minimo

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.write(f"Saldo inicial: **${saldo_inicial:.2f}**")

            with col2:
                ahorro = st.number_input(
                    "Ahorro",
                    key=f"ah_{mid}",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                    value=float(registro_existente["Ahorro"])
                    if registro_existente
                    else 0.0,
                )

            with col3:
                otras = st.number_input(
                    "Otras actividades",
                    key=f"ot_{mid}",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                    value=float(registro_existente["Otras_actividades"])
                    if registro_existente
                    else 0.0,
                )

            with col4:
                retiros = st.number_input(
                    "Retiros",
                    key=f"re_{mid}",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                    value=float(registro_existente["Retiros"])
                    if registro_existente
                    else 0.0,
                )

            saldo_final = saldo_inicial + ahorro + otras - retiros

            with col5:
                st.write(f"Saldo final: **${saldo_final:.2f}**")

            datos_form[mid] = {
                "saldo_inicial": saldo_inicial,
                "ahorro": ahorro,
                "otras": otras,
                "retiros": retiros,
                "saldo_final": saldo_final,
                "existente": registro_existente["Id_ahorro"] if registro_existente else None,
            }

            st.markdown("---")

        guardar_ahorros = st.form_submit_button("Guardar ahorros de la reunión")

    if guardar_ahorros:
        for mid, info_m in datos_form.items():
            if info_m["existente"]:
                sql_up = """
                UPDATE ahorros_miembros
                SET Saldo_inicial = %s,
                    Ahorro = %s,
                    Otras_actividades = %s,
                    Retiros = %s,
                    Saldo_final = %s
                WHERE Id_ahorro = %s
                """
                execute(
                    sql_up,
                    (
                        info_m["saldo_inicial"],
                        info_m["ahorro"],
                        info_m["otras"],
                        info_m["retiros"],
                        info_m["saldo_final"],
                        info_m["existente"],
                    ),
                )
            else:
                sql_ins = """
                INSERT INTO ahorros_miembros
                    (Id_grupo, Id_reunion, Id_miembro,
                     Saldo_inicial, Ahorro, Otras_actividades, Retiros, Saldo_final)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                execute(
                    sql_ins,
                    (
                        id_grupo,
                        id_reunion_sel,
                        mid,
                        info_m["saldo_inicial"],
                        info_m["ahorro"],
                        info_m["otras"],
                        info_m["retiros"],
                        info_m["saldo_final"],
                    ),
                )

        st.success("Ahorros guardados correctamente.")
        st.rerun()

    # ---- Resumen por reunión ----
    st.markdown("### Resumen de ahorros de la reunión")

    registros = _obtener_ahorros_de_reunion(id_grupo, id_reunion_sel)
    if registros:
        st.table(registros)

        total_ahorro = sum(float(r["Ahorro"]) for r in registros)
        total_otras = sum(float(r["Otras_actividades"]) for r in registros)
        total_retiros = sum(float(r["Retiros"]) for r in registros)
        total_saldo_final = sum(float(r["Saldo_final"]) for r in registros)

        st.write(f"**Totales del grupo en la reunión {id_reunion_sel}:**")
        st.write(f"- Total ahorro: **${total_ahorro:.2f}**")
        st.write(f"- Total otras actividades: **${total_otras:.2f}**")
        st.write(f"- Total retiros: **${total_retiros:.2f}**")
        st.write(f"- Total saldo final del grupo: **${total_saldo_final:.2f}**")
    else:
        st.info("Todavía no hay ahorros registrados para esta reunión.")


# -------------------------------------------------------
# Sección: Caja
# Tabla: caja_reunion
# -------------------------------------------------------
def _seccion_caja(info_dir: dict):
    st.subheader("Caja")

    id_grupo = info_dir["Id_grupo"]
    reuniones = _obtener_reuniones_de_grupo(id_grupo)

    if not reuniones:
        st.info("Todavía no hay reuniones registradas. Crea al menos una en Asistencia.")
        return

    opciones_reu = {
        f"{r['Fecha']} - Reunión {r['Numero_reunion']} ({r['Tema']})": r["Id_reunion"]
        for r in reuniones
    }

    st.markdown("### Seleccionar reunión para ver la caja")

    id_reunion_sel = st.selectbox(
        "Reunión",
        list(opciones_reu.values()),
        format_func=lambda rid: next(
            k for k, v in opciones_reu.items() if v == rid
        ),
        key="reunion_caja",
    )

    info_reu = _obtener_reunion_por_id(id_reunion_sel)
    fecha_reu = info_reu["Fecha"]

    st.markdown(
        f"Reunión seleccionada: **{fecha_reu}** — N° {info_reu['Numero_reunion']} — {info_reu['Tema']}"
    )

    # Caja existente (si ya se guardó antes)
    caja = _obtener_caja_por_reunion(id_grupo, id_reunion_sel)

    # Saldo de apertura: si ya hay caja guardada, usamos ese; si no, lo calculamos
    if caja:
        saldo_apertura = float(caja["Saldo_apertura"])
        otros_ingresos_default = float(caja["Otros_ingresos"])
        otros_gastos_default = float(caja["Otros_gastos"])
    else:
        saldo_apertura = _obtener_saldo_cierre_anterior(id_grupo, fecha_reu)
        otros_ingresos_default = 0.0
        otros_gastos_default = 0.0

    # ---- DINERO QUE ENTRA (automático) ----
    multas_pagadas = _sumar_float(
        """
        SELECT SUM(Monto) AS suma
        FROM multas_miembro
        WHERE Id_grupo = %s AND Pagada = 1 AND Fecha_pago = %s
        """,
        (id_grupo, fecha_reu),
    )

    ahorros = _sumar_float(
        """
        SELECT SUM(Ahorro) AS suma
        FROM ahorros_miembros
        WHERE Id_grupo = %s AND Id_reunion = %s
        """,
        (id_grupo, id_reunion_sel),
    )

    otras_act = _sumar_float(
        """
        SELECT SUM(Otras_actividades) AS suma
        FROM ahorros_miembros
        WHERE Id_grupo = %s AND Id_reunion = %s
        """,
        (id_grupo, id_reunion_sel),
    )

    pagos_prestamos = _sumar_float(
        """
        SELECT SUM(pp.Capital_pagado + pp.Interes_pagado) AS suma
        FROM pagos_prestamo pp
        JOIN prestamos_miembro p ON p.Id_prestamo = pp.Id_prestamo
        WHERE p.Id_grupo = %s AND pp.Fecha_programada = %s
        """,
        (id_grupo, fecha_reu),
    )

    # ---- DINERO QUE SALE (automático) ----
    retiros_ahorros = _sumar_float(
        """
        SELECT SUM(Retiros) AS suma
        FROM ahorros_miembros
        WHERE Id_grupo = %s AND Id_reunion = %s
        """,
        (id_grupo, id_reunion_sel),
    )

    desembolsos_prestamos = _sumar_float(
        """
        SELECT SUM(Monto) AS suma
        FROM prestamos_miembro
        WHERE Id_grupo = %s AND Fecha_prestamo = %s
        """,
        (id_grupo, fecha_reu),
    )

    # ---- Formulario para otros ingresos/gastos y guardar ----
    with st.form("form_caja"):
        st.markdown("### Dinero que entra")
        st.write(f"- Multas pagadas: **${multas_pagadas:.2f}**")
        st.write(f"- Ahorros: **${ahorros:.2f}**")
        st.write(f"- Otras actividades: **${otras_act:.2f}**")
        st.write(
            f"- Pago de préstamos (capital e interés): **${pagos_prestamos:.2f}**"
        )

        otros_ingresos = st.number_input(
            "Otros ingresos del grupo",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=otros_ingresos_default,
        )

        total_entradas = (
            multas_pagadas + ahorros + otras_act + pagos_prestamos + otros_ingresos
        )

        st.write(f"**Total dinero que entra:** ${total_entradas:.2f}**")

        st.markdown("### Dinero que sale")
        st.write(f"- Retiro de ahorros: **${retiros_ahorros:.2f}**")
        st.write(f"- Desembolso de préstamos: **${desembolsos_prestamos:.2f}**")

        otros_gastos = st.number_input(
            "Otros gastos del grupo",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=otros_gastos_default,
        )

        total_salidas = retiros_ahorros + desembolsos_prestamos + otros_gastos

        st.write(f"**Total dinero que sale:** ${total_salidas:.2f}**")

        saldo_despues_entradas = saldo_apertura + total_entradas
        saldo_cierre = saldo_despues_entradas - total_salidas

        st.markdown("### Resumen de caja")
        st.write(f"Saldo de apertura: **${saldo_apertura:.2f}**")
        st.write(f"Saldo después de que entra dinero: **${saldo_despues_entradas:.2f}**")
        st.write(f"Saldo de cierre: **${saldo_cierre:.2f}**")

        btn_guardar_caja = st.form_submit_button("Guardar caja de la reunión")

    if btn_guardar_caja:
        if caja:
            sql_up = """
            UPDATE caja_reunion
            SET Saldo_apertura = %s,
                Multas = %s,
                Ahorros = %s,
                Otras_actividades = %s,
                Pagos_prestamos = %s,
                Otros_ingresos = %s,
                Total_entradas = %s,
                Retiros_ahorros = %s,
                Desembolsos_prestamos = %s,
                Otros_gastos = %s,
                Total_salidas = %s,
                Saldo_cierre = %s
            WHERE Id_caja = %s
            """
            execute(
                sql_up,
                (
                    saldo_apertura,
                    multas_pagadas,
                    ahorros,
                    otras_act,
                    pagos_prestamos,
                    otros_ingresos,
                    total_entradas,
                    retiros_ahorros,
                    desembolsos_prestamos,
                    otros_gastos,
                    total_salidas,
                    saldo_cierre,
                    caja["Id_caja"],
                ),
            )
        else:
            sql_ins = """
            INSERT INTO caja_reunion (
                Id_grupo, Id_reunion,
                Saldo_apertura,
                Multas, Ahorros, Otras_actividades, Pagos_prestamos,
                Otros_ingresos, Total_entradas,
                Retiros_ahorros, Desembolsos_prestamos, Otros_gastos,
                Total_salidas, Saldo_cierre
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute(
                sql_ins,
                (
                    id_grupo,
                    id_reunion_sel,
                    saldo_apertura,
                    multas_pagadas,
                    ahorros,
                    otras_act,
                    pagos_prestamos,
                    otros_ingresos,
                    total_entradas,
                    retiros_ahorros,
                    desembolsos_prestamos,
                    otros_gastos,
                    total_salidas,
                    saldo_cierre,
                ),
            )

        st.success("Caja de la reunión guardada correctamente.")
        st.rerun()


# -------------------------------------------------------
# Sección: Préstamos
# Tablas: prestamos_miembro y pagos_prestamo
# -------------------------------------------------------
def _obtener_prestamos_de_grupo(id_grupo: int):
    sql = """
    SELECT 
        p.Id_prestamo,
        p.Id_miembro,
        m.Nombre,
        m.Cargo,
        p.Fecha_prestamo,
        p.Fecha_primer_pago,
        p.Meses_plazo,
        p.Monto,
        p.Tasa_mensual,
        p.Capital_total,
        p.Interes_total,
        p.Total_pagar
    FROM prestamos_miembro p
    JOIN miembros m ON m.Id_miembro = p.Id_miembro
    WHERE p.Id_grupo = %s
    ORDER BY p.Fecha_prestamo DESC, p.Id_prestamo DESC
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_pagos_prestamo(id_prestamo: int):
    sql = """
    SELECT 
        Id_pago,
        Id_prestamo,
        Numero_cuota,
        Fecha_programada,
        Capital_programado,
        Interes_programado,
        Capital_pagado,
        Interes_pagado
    FROM pagos_prestamo
    WHERE Id_prestamo = %s
    ORDER BY Numero_cuota
    """
    return fetch_all(sql, (id_prestamo,))


def _seccion_prestamos(info_dir: dict):
    st.subheader("Préstamos")

    id_grupo = info_dir["Id_grupo"]
    miembros = _obtener_miembros_grupo(id_grupo)
    reglamento = _obtener_reglamento_por_grupo(id_grupo)

    if not miembros:
        st.info("Primero debes registrar miembros para poder otorgar préstamos.")
        return

    # Tasa mensual tomada automáticamente del reglamento (Interes_por_10 / 10)
    tasa_mensual = 0.05
    if reglamento and reglamento.get("Interes_por_10") is not None:
        try:
            tasa_mensual = float(reglamento["Interes_por_10"]) / 10.0
        except Exception:
            tasa_mensual = 0.05

    saldo_caja_actual = _obtener_saldo_caja_actual(id_grupo)
    st.info(
        f"Saldo disponible en caja: **${saldo_caja_actual:.2f}**\n\n"
        f"Tasa de interés mensual aplicada (desde reglamento): "
        f"**{tasa_mensual*100:.2f}%**"
    )

    st.markdown("### Registrar nuevo préstamo")

    opciones_miembro = {
        f"{m['Nombre']} ({m['Cargo']})": m["Id_miembro"] for m in miembros
    }

    with st.form("form_nuevo_prestamo"):
        miembro_label = st.selectbox(
            "Socia / socio (miembro que toma el préstamo)",
            list(opciones_miembro.keys()),
        )
        id_miembro_sel = opciones_miembro[miembro_label]

        fecha_prestamo = st.date_input("Fecha del préstamo", value=dt.date.today())
        meses_plazo = st.number_input(
            "Plazo en meses",
            min_value=1,
            step=1,
            value=3,
        )
        monto = st.number_input(
            "Monto del préstamo ($)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
        )

        st.write(
            "La tasa mensual se toma automáticamente del reglamento del grupo.\n"
            "Si en el reglamento dice, por ejemplo, 0.5 por cada $10, aquí se usa 5% mensual."
        )
        st.write(f"**Tasa mensual aplicada:** {tasa_mensual*100:.2f}%")

        fecha_primer_pago = st.date_input(
            "Fecha del primer pago",
            value=_sumar_meses(fecha_prestamo, 1),
        )

        proposito = st.text_area(
            "Propósito del préstamo",
            placeholder="Ejemplo: capital de trabajo, emergencia médica, etc.",
        )

        btn_calcular = st.form_submit_button("Calcular y guardar préstamo")

    if btn_calcular:
        if monto <= 0 or meses_plazo <= 0 or tasa_mensual < 0:
            st.error("Verifica que monto y plazo sean válidos.")
            return

        if monto > saldo_caja_actual:
            st.error(
                "El monto del préstamo supera el saldo de caja disponible. "
                "No se puede otorgar este préstamo."
            )
            return

        # --- Cálculos redondeados para evitar problemas con DECIMAL ---
        interes_total = round(monto * tasa_mensual * meses_plazo, 2)
        capital_total = round(monto, 2)
        total_pagar = round(capital_total + interes_total, 2)

        capital_cuota = round(capital_total / meses_plazo, 2)
        interes_cuota = round(interes_total / meses_plazo, 2)

        # --- Insert de préstamo con manejo de errores para ver el mensaje real ---
        sql_ins = """
        INSERT INTO prestamos_miembro (
            Id_grupo, Id_miembro, Fecha_prestamo, Fecha_primer_pago,
            Meses_plazo, Monto, Tasa_mensual,
            Capital_total, Interes_total, Total_pagar
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            execute(
                sql_ins,
                (
                    id_grupo,
                    id_miembro_sel,
                    fecha_prestamo,
                    fecha_primer_pago,
                    int(meses_plazo),
                    capital_total,
                    tasa_mensual,
                    capital_total,
                    interes_total,
                    total_pagar,
                ),
            )
        except Exception as e:
            st.error(f"Error al guardar el préstamo en la tabla prestamos_miembro: {e}")
            return

        # Recuperar Id_prestamo recién creado
        sql_last = """
        SELECT Id_prestamo
        FROM prestamos_miembro
        WHERE Id_grupo = %s AND Id_miembro = %s AND Fecha_prestamo = %s
        ORDER BY Id_prestamo DESC
        LIMIT 1
        """
        prestamo = fetch_one(sql_last, (id_grupo, id_miembro_sel, fecha_prestamo))
        if not prestamo:
            st.error("No se pudo recuperar el préstamo recién creado.")
            return
        id_prestamo = prestamo["Id_prestamo"]

        # Crear calendario de pagos (cuotas mensuales)
        for n in range(1, int(meses_plazo) + 1):
            fecha_cuota = _sumar_meses(fecha_primer_pago, n - 1)
            sql_pago = """
            INSERT INTO pagos_prestamo (
                Id_prestamo, Numero_cuota, Fecha_programada,
                Capital_programado, Interes_programado,
                Capital_pagado, Interes_pagado
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            try:
                execute(
                    sql_pago,
                    (
                        id_prestamo,
                        n,
                        fecha_cuota,
                        capital_cuota,
                        interes_cuota,
                        0.0,
                        0.0,
                    ),
                )
            except Exception as e:
                st.error(
                    f"Error al crear la cuota {n} en la tabla pagos_prestamo: {e}"
                )
                return

        st.success(
            f"Préstamo guardado correctamente. Capital total: ${capital_total:.2f}, "
            f"intereses totales: ${interes_total:.2f}, total a pagar: ${total_pagar:.2f}."
        )
        st.rerun()

    # -------- Gestión de préstamos existentes --------
    st.markdown("---")
    st.markdown("### Préstamos registrados")

    prestamos = _obtener_prestamos_de_grupo(id_grupo)
    if not prestamos:
        st.info("Aún no hay préstamos registrados para este grupo.")
        return

    etiquetas_prestamo = {
        f"#{p['Id_prestamo']} - {p['Nombre']} - ${p['Monto']:.2f} "
        f"({p['Fecha_prestamo']}, {p['Meses_plazo']} meses)": p["Id_prestamo"]
        for p in prestamos
    }

    id_prestamo_sel = st.selectbox(
        "Selecciona un préstamo para ver / registrar pagos",
        list(etiquetas_prestamo.values()),
        format_func=lambda pid: next(
            k for k, v in etiquetas_prestamo.items() if v == pid
        ),
    )

    prestamo_sel = next(p for p in prestamos if p["Id_prestamo"] == id_prestamo_sel)
    pagos = _obtener_pagos_prestamo(id_prestamo_sel)

    st.write(
        f"**Socia:** {prestamo_sel['Nombre']} ({prestamo_sel['Cargo']}) — "
        f"Fecha préstamo: {prestamo_sel['Fecha_prestamo']} — "
        f"Monto: ${prestamo_sel['Monto']:.2f} — "
        f"Tasa mensual: {prestamo_sel['Tasa_mensual']*100:.2f}% — "
        f"Total a pagar: ${prestamo_sel['Total_pagar']:.2f}"
    )

    if not pagos:
        st.info("No se encontraron cuotas para este préstamo.")
        return

    st.markdown("#### Calendario de pagos (a pagar vs pagado)")

    total_cap_prog = 0.0
    total_int_prog = 0.0
    total_cap_pag = 0.0
    total_int_pag = 0.0

    with st.form("form_pagos_prestamo"):
        nuevos_pagos = []

        for pago in pagos:
            st.markdown(f"**Cuota {pago['Numero_cuota']}**")
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                fecha_prog = st.date_input(
                    "Fecha",
                    value=pago["Fecha_programada"],
                    key=f"fp_{pago['Id_pago']}",
                )
            with col2:
                cap_prog = float(pago["Capital_programado"])
                st.write(f"Capital a pagar: **${cap_prog:.2f}**")
            with col3:
                int_prog = float(pago["Interes_programado"])
                st.write(f"Interés a pagar: **${int_prog:.2f}**")
            with col4:
                cap_pag = st.number_input(
                    "Capital pagado",
                    key=f"cp_{pago['Id_pago']}",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    value=float(pago["Capital_pagado"]),
                )
            with col5:
                int_pag = st.number_input(
                    "Interés pagado",
                    key=f"ip_{pago['Id_pago']}",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    value=float(pago["Interes_pagado"]),
                )

            total_pagado_cuota = cap_pag + int_pag
            st.write(f"Total pagado en esta fecha: **${total_pagado_cuota:.2f}**")
            st.markdown("---")

            total_cap_prog += cap_prog
            total_int_prog += int_prog
            total_cap_pag += cap_pag
            total_int_pag += int_pag

            nuevos_pagos.append(
                {
                    "Id_pago": pago["Id_pago"],
                    "Fecha_programada": fecha_prog,
                    "Capital_pagado": cap_pag,
                    "Interes_pagado": int_pag,
                }
            )

        btn_guardar_pagos = st.form_submit_button("Guardar pagos")

    if btn_guardar_pagos:
        for np in nuevos_pagos:
            sql_up = """
            UPDATE pagos_prestamo
            SET Fecha_programada = %s,
                Capital_pagado = %s,
                Interes_pagado = %s
            WHERE Id_pago = %s
            """
            execute(
                sql_up,
                (
                    np["Fecha_programada"],
                    np["Capital_pagado"],
                    np["Interes_pagado"],
                    np["Id_pago"],
                ),
            )

        st.success("Pagos actualizados correctamente.")
        st.rerun()

    # Resumen y saldo pendiente
    total_pagado = total_cap_pag + total_int_pag
    saldo_pendiente = float(prestamo_sel["Total_pagar"]) - total_pagado

    st.markdown("#### Resumen del préstamo")
    st.write(f"- Capital total programado: **${total_cap_prog:.2f}**")
    st.write(f"- Interés total programado: **${total_int_prog:.2f}**")
    st.write(f"- Capital pagado: **${total_cap_pag:.2f}**")
    st.write(f"- Interés pagado: **${total_int_pag:.2f}**")
    st.write(f"- Total pagado: **${total_pagado:.2f}**")
    st.write(f"- Saldo pendiente: **${saldo_pendiente:.2f}**")


# -------------------------------------------------------
# Sección: Cierre de ciclo
# -------------------------------------------------------
def _seccion_cierre_ciclo(info_dir: dict):
    st.subheader("Cierre de ciclo")
    id_grupo = info_dir["Id_grupo"]

    reglamento = _obtener_reglamento_por_grupo(id_grupo)
    if not reglamento:
        st.info("Primero debes definir el reglamento del grupo (ciclo y fechas).")
        return

    fecha_inicio_ciclo = reglamento.get("Fecha_inicio_ciclo")
    fecha_fin_ciclo = reglamento.get("Fecha_fin_ciclo")

    if not fecha_inicio_ciclo or not fecha_fin_ciclo:
        st.warning(
            "El reglamento no tiene definidas la fecha de inicio y fin del ciclo. "
            "Complétalas en la pestaña de Reglamento."
        )
        return

    st.markdown("### Información del ciclo actual (según reglamento)")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Fecha de inicio del ciclo: **{fecha_inicio_ciclo}**")
    with col2:
        st.write(f"Fecha estimada de cierre del ciclo: **{fecha_fin_ciclo}**")

    # --------------------------- Historial -----------------------------
    st.markdown("---")
    st.markdown("### Historial de cierres de ciclo del grupo")

    cierres = _obtener_cierres_ciclo_grupo(id_grupo)
    if cierres:
        opciones_cierres = {
            f"{c['Fecha_cierre']} — del {c['Fecha_inicio_ciclo']} al {c['Fecha_fin_ciclo']} "
            f"(Total ahorro grupo: ${c['Total_ahorro_grupo']:.2f})": c["Id_cierre"]
            for c in cierres
        }
        id_cierre_sel = st.selectbox(
            "Selecciona un cierre para consultar su detalle",
            list(opciones_cierres.values()),
            format_func=lambda cid: next(
                k for k, v in opciones_cierres.items() if v == cid
            ),
        )

        if id_cierre_sel:
            st.markdown("#### Detalle de miembros en el cierre seleccionado")
            detalle = _obtener_detalle_cierre(id_cierre_sel)
            if detalle:
                st.table(detalle)
            else:
                st.info("No se encontraron detalles de miembros para este cierre.")
    else:
        st.info("Aún no se ha registrado ningún cierre de ciclo para este grupo.")

    # ------------------------ Nuevo cierre -----------------------------
    st.markdown("---")
    st.markdown("### Registrar nuevo cierre de ciclo")

    # Regla: solo si NO hay préstamos ni multas pendientes
    hay_prestamos_pend = _tiene_prestamos_pendientes(id_grupo)
    hay_multas_pend = _tiene_multas_pendientes(id_grupo)

    if hay_prestamos_pend or hay_multas_pend:
        if hay_prestamos_pend:
            st.error(
                "No se puede cerrar el ciclo: todavía hay préstamos con saldo pendiente."
            )
        if hay_multas_pend:
            st.error(
                "No se puede cerrar el ciclo: todavía hay multas NO pagadas."
            )
        st.info(
            "Cuando todos los préstamos estén liquidados y todas las multas pagadas, "
            "podrás habilitar el cierre de ciclo."
        )
        return

    # Evitar duplicar un cierre para el mismo rango de fechas
    for c in cierres:
        if (
            c["Fecha_inicio_ciclo"] == fecha_inicio_ciclo
            and c["Fecha_fin_ciclo"] == fecha_fin_ciclo
        ):
            st.warning(
                "Ya existe un cierre de ciclo registrado para este periodo "
                "(misma fecha de inicio y fin)."
            )
            return

    # Totales de ahorro del ciclo por miembro
    miembros_totales = _obtener_totales_ahorro_ciclo(
        id_grupo, fecha_inicio_ciclo, fecha_fin_ciclo
    )
    if not miembros_totales:
        st.info(
            "No se encontraron registros de ahorros para este ciclo. "
            "Verifica la pestaña de Ahorro final."
        )
        return

    num_miembros = len(miembros_totales)
    total_ahorro_grupo = sum(
        float(m["Total_ahorrado"] or 0.0) for m in miembros_totales
    )
    porcion_fondo = (
        round(total_ahorro_grupo / num_miembros, 2) if num_miembros > 0 else 0.0
    )

    st.write(f"**Total ahorro del grupo en el ciclo:** ${total_ahorro_grupo:.2f}")
    st.write(f"**Número de miembros:** {num_miembros}")
    st.write(
        f"**Porción de fondo del grupo por persona (equitativa):** "
        f"${porcion_fondo:.2f}"
    )

    # Formulario de cierre
    with st.form("form_cierre_ciclo"):
        fecha_cierre = st.date_input(
            "Fecha de cierre del ciclo",
            value=fecha_fin_ciclo,
            help="Debe coincidir con la fecha de cierre definida en el reglamento.",
        )

        st.markdown("#### Detalle por miembro")
        datos_cierre = {}

        for m in miembros_totales:
            mid = m["Id_miembro"]
            nombre = m["Nombre"]
            cargo = m["Cargo"]
            total_ahorrado = float(m["Total_ahorrado"] or 0.0)
            total_correspondiente = round(total_ahorrado + porcion_fondo, 2)

            st.markdown(f"**{nombre} ({cargo})**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"Total ahorrado en el ciclo: **${total_ahorrado:.2f}**")
            with col2:
                st.write(f"Porción del fondo del grupo: **${porcion_fondo:.2f}**")
            with col3:
                st.write(
                    f"Total correspondiente: **${total_correspondiente:.2f}**"
                )
            with col4:
                retiro = st.number_input(
                    "Retiro en cierre",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"retiro_cierre_{mid}",
                )

            datos_cierre[mid] = {
                "total_ahorrado": total_ahorrado,
                "total_correspondiente": total_correspondiente,
                "retiro": retiro,
            }

        st.markdown(
            "El saldo que NO se retire quedará como **saldo inicial del siguiente ciclo**."
        )

        btn_guardar_cierre = st.form_submit_button("Guardar cierre de ciclo")

    if not btn_guardar_cierre:
        return

    # Validar que la fecha de cierre coincida con la del reglamento
    if fecha_cierre != fecha_fin_ciclo:
        st.error(
            "La fecha de cierre que seleccionaste no coincide con la fecha de cierre "
            "establecida en el reglamento. Modifica la fecha o actualiza el reglamento."
        )
        return

    # Validación de retiros
    for mid, info_m in datos_cierre.items():
        if info_m["retiro"] > info_m["total_correspondiente"] + 0.01:
            st.error(
                "El retiro de alguna socia excede el total correspondiente. "
                "Revisa los valores antes de guardar."
            )
            return

    # Insertar en cierres_ciclo
    sql_ins_cierre = """
    INSERT INTO cierres_ciclo (
        Id_grupo,
        Fecha_cierre,
        Fecha_inicio_ciclo,
        Fecha_fin_ciclo,
        Total_ahorro_grupo,
        Porcion_fondo_grupo
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute(
        sql_ins_cierre,
        (
            id_grupo,
            fecha_cierre,
            fecha_inicio_ciclo,
            fecha_fin_ciclo,
            total_ahorro_grupo,
            porcion_fondo,
        ),
    )

    # Recuperar Id_cierre
    sql_sel_cierre = """
    SELECT Id_cierre
    FROM cierres_ciclo
    WHERE Id_grupo = %s AND Fecha_cierre = %s
    ORDER BY Id_cierre DESC
    LIMIT 1
    """
    cierre = fetch_one(sql_sel_cierre, (id_grupo, fecha_cierre))
    if not cierre:
        st.error("No se pudo recuperar el cierre de ciclo recién creado.")
        return

    id_cierre = cierre["Id_cierre"]

    # Detalle por miembro + actualizar saldo final
    for mid, info_m in datos_cierre.items():
        total_ahorrado = info_m["total_ahorrado"]
        total_corr = info_m["total_correspondiente"]
        retiro = info_m["retiro"]
        saldo_siguiente = round(total_corr - retiro, 2)

        sql_ins_det = """
        INSERT INTO cierres_ciclo_miembros (
            Id_cierre,
            Id_miembro,
            Total_ahorrado_ciclo,
            Total_correspondiente,
            Retiro_cierre,
            Saldo_siguiente_ciclo
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute(
            sql_ins_det,
            (
                id_cierre,
                mid,
                total_ahorrado,
                total_corr,
                retiro,
                saldo_siguiente,
            ),
        )

        _actualizar_saldo_final_ultimo_ahorro(id_grupo, mid, saldo_siguiente)

    st.success("Cierre de ciclo registrado correctamente.")
    st.info(
        "Los saldos que dejaron las socias se usarán como saldo inicial en el "
        "siguiente ciclo, cuando actualicen el reglamento."
    )
    st.rerun()


# -------------------------------------------------------
# Panel principal de Directiva
# -------------------------------------------------------
@has_role("DIRECTIVA")
def directiva_panel():
    """
    Panel principal que ve la directiva cuando inicia sesión.
    """
    info_dir = _obtener_info_directiva_actual()
    if not info_dir:
        st.error(
            "No se encontró información de directiva asociada a este usuario. "
            "Verifica que el DUI del usuario esté registrado en la tabla 'directiva'."
        )
        return

    st.title("Panel de Directiva")
    st.caption(
        f"Directiva: {info_dir['Nombre']} — Grupo: {info_dir['Nombre_grupo']} "
        f"(Id_grupo {info_dir['Id_grupo']})"
    )

    # Orden que acordamos:
    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            "Multas",
            "Ahorro final",
            "Préstamos",
            "Caja",
            "Cierre de ciclo",
            "Reportes",
        ]
    )

    # Reglamento
    with tabs[0]:
        _seccion_reglamento(info_dir)

    # Miembros
    with tabs[1]:
        _seccion_miembros(info_dir)

    # Asistencia
    with tabs[2]:
        _seccion_asistencia(info_dir)

    # Multas
    with tabs[3]:
        _seccion_multas(info_dir)

    # Ahorro final
    with tabs[4]:
        _seccion_ahorro_final(info_dir)

    # Préstamos
    with tabs[5]:
        _seccion_prestamos(info_dir)

    # Caja
    with tabs[6]:
        _seccion_caja(info_dir)

    # Cierre de ciclo
    with tabs[7]:
        _seccion_cierre_ciclo(info_dir)

    # Reportes (pendiente)
    with tabs[8]:
        st.info(
            "Aquí se implementarán los reportes con gráficos de ingresos, egresos "
            "y consolidado para el grupo."
        )
