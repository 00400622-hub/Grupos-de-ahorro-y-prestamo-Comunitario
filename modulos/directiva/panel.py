# modulos/directiva/panel.py

import datetime as dt
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
    """
    Recupera el reglamento registrado para un grupo (si existe).
    """
    sql = """
    SELECT *
    FROM reglamento_grupo
    WHERE Id_grupo = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _obtener_miembros_grupo(id_grupo: int):
    """
    Devuelve los miembros registrados para un grupo.
    """
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
    """
    Reuniones registradas del grupo (para asistencia y ahorro final).
    """
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
            "Pagamos ____ de interés por cada $10.00 prestados",
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
            # Por defecto un año después
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
        # Validaciones simples
        if not nombre_comunidad.strip():
            st.warning("Debes escribir el nombre de la comunidad.")
            return

        if reglamento is None:
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
            # UPDATE
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
        "ahorros, etc."
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
# Sección: Asistencia
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


def _seccion_asistencia(info_dir: dict):
    st.subheader("Asistencia")

    id_grupo = info_dir["Id_grupo"]
    reuniones = _obtener_reuniones_de_grupo(id_grupo)
    miembros = _obtener_miembros_grupo(id_grupo)

    # ---- Crear o seleccionar reunión ----
    st.markdown("#### 1. Reunión")

    with st.form("form_reunion"):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha de la reunión", value=dt.date.today())
        with col2:
            numero = st.number_input("Número de reunión", min_value=1, step=1, value=1)
        tema = st.text_input("Tema / Comentarios de la reunión", "")

        btn_crear_reunion = st.form_submit_button("Crear / usar esta reunión")

    if btn_crear_reunion:
        # Buscar si ya existe reunión con ese grupo, fecha y número
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
            # Recuperar id
            existente = fetch_one(sql_busca, (id_grupo, fecha, numero))
            id_reunion_sel = existente["Id_reunion"]

        st.session_state["reunion_abierta"] = id_reunion_sel
        st.success(f"Reunión lista (Id_reunion = {id_reunion_sel}).")
        st.rerun()

    id_reunion_sel = st.session_state.get("reunion_abierta")
    if not id_reunion_sel:
        st.info("Primero crea o selecciona una reunión para tomar asistencia.")
        return

    # Buscar info de la reunión actual (para mostrar fecha y número)
    reunion_actual = next(
        (r for r in reuniones if r["Id_reunion"] == id_reunion_sel), None
    )

    if reunion_actual:
        st.markdown(
            f"**Reunión actual:** Id_reunion = {id_reunion_sel} — "
            f"Fecha: **{reunion_actual['Fecha']}**, "
            f"Número: **{reunion_actual['Numero_reunion']}**"
        )
    else:
        st.markdown(f"**Reunión actual:** Id_reunion = {id_reunion_sel}")

    # ---- Formulario de asistencia ----
    st.markdown("#### 2. Marcar asistencia de miembros")

    # Traemos asistencias ya registradas
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
        # Guardamos uno por uno (insert / update)
        for mid, presente in nuevos_presentes.items():
            # ¿Existe registro?
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

        st.success("Asistencia guardada correctamente.")
        st.rerun()

    # ---- Resumen de la reunión ----
    st.markdown("#### 3. Resumen de asistencia")

    registros = _obtener_asistencia_de_reunion(id_reunion_sel)
    if registros:
        if reunion_actual:
            st.write(f"Fecha de la reunión: **{reunion_actual['Fecha']}**")
        st.table(registros)
        total = len(registros)
        presentes = sum(1 for r in registros if r["Presente"])
        st.write(f"Total de miembros registrados: **{total}**")
        st.write(f"Asistieron: **{presentes}** — No asistieron: **{total - presentes}**")
    else:
        st.info("Todavía no se ha registrado asistencia para esta reunión.")


# -------------------------------------------------------
# Sección: Multas
# Tabla: multas_miembro
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

    # -------- Registrar multa --------
    st.markdown("### Registrar nueva multa")

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
    """
    Registros de ahorro para un grupo y una reunión específica.
    Incluye también la fecha de la reunión.
    """
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
        a.Saldo_final,
        r.Fecha AS Fecha_reunion
    FROM ahorros_miembros a
    JOIN miembros m ON m.Id_miembro = a.Id_miembro
    JOIN reuniones_grupo r ON r.Id_reunion = a.Id_reunion
    WHERE a.Id_grupo = %s
      AND a.Id_reunion = %s
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_grupo, id_reunion))


def _obtener_ultimo_saldo_miembro(id_grupo: int, id_miembro: int):
    """
    Último saldo_final registrado para un miembro del grupo.
    """
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

    # Info de la reunión seleccionada
    reunion_actual = next(
        (r for r in reuniones if r["Id_reunion"] == id_reunion_sel), None
    )

    if reunion_actual:
        st.markdown(
            f"Reunión seleccionada: **Id_reunion = {id_reunion_sel}** — "
            f"Fecha: **{reunion_actual['Fecha']}**, "
            f"Número: **{reunion_actual['Numero_reunion']}**"
        )
    else:
        st.markdown(f"Reunión seleccionada: **Id_reunion = {id_reunion_sel}**")

    # Traemos registros existentes de esa reunión
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
                # Si no hay registro previo para este miembro, usamos:
                # - último saldo_final registrado
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
                # UPDATE
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
                # INSERT
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

    # ---- Resumen de ahorros de la reunión ----
    st.markdown("### Resumen de ahorros de la reunión")

    registros_resumen = _obtener_ahorros_de_reunion(id_grupo, id_reunion_sel)
    if registros_resumen:
        # Todos los registros tienen la misma fecha de reunión
        fecha_reu = registros_resumen[0].get("Fecha_reunion")
        if fecha_reu:
            st.write(f"Fecha de la reunión: **{fecha_reu}**")
        st.table(registros_resumen)
    else:
        st.info("Todavía no hay ahorros registrados para esta reunión.")


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

    # Préstamos (pendiente de implementar)
    with tabs[5]:
        st.info("Aquí se implementará el formulario de préstamos.")

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
