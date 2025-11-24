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
                    execute(
                        "DELETE FROM miembros WHERE Id_miembro = %s",
                        (mid,),
                    )
                st.success("Miembros eliminados correctamente.")
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

        st.success("Asistencia guardada correctamente (y multas de inasistencia generadas).")
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

    # Tasa mensual sugerida a partir del reglamento (Interes_por_10 / 10)
    tasa_default_mensual = 0.05
    if reglamento and reglamento.get("Interes_por_10") is not None:
        try:
            tasa_default_mensual = float(reglamento["Interes_por_10"]) / 10.0
        except Exception:
            tasa_default_mensual = 0.05

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
            "Tasa de interés mensual en **porcentaje**. "
            "Por ejemplo, si la tasa es 5% mensual, aquí escribes **5** (no 0.05)."
        )
        tasa_porcentaje = st.number_input(
            "Tasa de interés mensual (%)",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            value=round(tasa_default_mensual * 100, 2),
        )
        tasa_mensual = tasa_porcentaje / 100.0  # 5% -> 0.05

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
            st.error("Verifica que monto, plazo y tasa sean válidos.")
        else:
            # Cálculos básicos
            interes_total = monto * tasa_mensual * meses_plazo
            capital_total = monto
            total_pagar = capital_total + interes_total

            capital_cuota = capital_total / meses_plazo
            interes_cuota = interes_total / meses_plazo

            # Insertar préstamo
            sql_ins = """
            INSERT INTO prestamos_miembro (
                Id_grupo, Id_miembro, Fecha_prestamo, Fecha_primer_pago,
                Meses_plazo, Monto, Tasa_mensual,
                Capital_total, Interes_total, Total_pagar
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute(
                sql_ins,
                (
                    id_grupo,
                    id_miembro_sel,
                    fecha_prestamo,
                    fecha_primer_pago,
                    meses_plazo,
                    monto,
                    tasa_mensual,
                    capital_total,
                    interes_total,
                    total_pagar,
                ),
            )

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
            for n in range(1, meses_plazo + 1):
                fecha_cuota = _sumar_meses(fecha_primer_pago, n - 1)
                sql_pago = """
                INSERT INTO pagos_prestamo (
                    Id_prestamo, Numero_cuota, Fecha_programada,
                    Capital_programado, Interes_programado,
                    Capital_pagado, Interes_pagado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
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

    # Caja (pendiente)
    with tabs[6]:
        st.info("Aquí se implementará el manejo de caja.")

    # Cierre de ciclo (pendiente)
    with tabs[7]:
        st.info("Aquí se implementará el cierre de ciclo.")

    # Reportes (pendiente)
    with tabs[8]:
        st.info(
            "Aquí se implementarán los reportes con gráficos de ingresos, egresos "
            "y consolidado para el grupo."
        )
