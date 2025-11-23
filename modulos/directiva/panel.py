# modulos/directiva/panel.py

import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_one, fetch_all, execute
from modulos.auth.rbac import has_role, get_user


# -------------------------------------------------------------------
# Helpers generales
# -------------------------------------------------------------------
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
            Sexo,
            Cargo
        FROM miembros
        WHERE Id_grupo = %s
        ORDER BY Cargo, Nombre
    """
    return fetch_all(sql, (id_grupo,))


# -------------------------------------------------------------------
# Sección: Reglamento de grupo
# -------------------------------------------------------------------
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
            value=int(reglamento["Plazo_max_meses"])
            if reglamento and reglamento.get("Plazo_max_meses") is not None
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
                    Plazo_max_meses
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
                    Plazo_max_meses = %s
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


# -------------------------------------------------------------------
# Sección: Miembros del grupo
# -------------------------------------------------------------------
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
        sexo_m = st.selectbox("Sexo", ["F", "M", "Otro"])
        cargo_m = st.selectbox("Cargo dentro del grupo", cargos_posibles)

        btn_agregar = st.form_submit_button("Guardar miembro")

    if btn_agregar:
        if not nombre_m.strip() or not dui_m.strip():
            st.warning("Debes completar el nombre y el DUI del miembro.")
        else:
            execute(
                """
                INSERT INTO miembros (Id_grupo, Nombre, DUI, Sexo, Cargo)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_grupo, nombre_m.strip(), dui_m.strip(), sexo_m, cargo_m),
            )
            st.success("Miembro registrado correctamente.")
            st.rerun()

    # -------- Listado y eliminación --------
    st.markdown("---")
    st.markdown("### Miembros registrados en el grupo")

    miembros = _obtener_miembros_grupo(id_grupo)
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


# -------------------------------------------------------------------
# Sección: Asistencia
# Tablas: reuniones_grupo, asistencia_miembro
# -------------------------------------------------------------------
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
            value=dt.date.today(),
        )
        num_reu = st.number_input(
            "Número de reunión en el ciclo",
            min_value=1,
            step=1,
            value=1,
        )
        tema_reu = st.text_input(
            "Tema u observaciones (opcional)",
            "",
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
            st.info(
                "Ya existía una reunión en esa fecha, se abrió para editar asistencia."
            )
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

    miembros = _obtener_miembros_grupo(id_grupo)
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

    # Resumen rápido
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


# -------------------------------------------------------------------
# Sección: Multas
# Tabla: multas_miembro
# -------------------------------------------------------------------
def _obtener_multas_de_grupo(id_grupo: int):
    sql = """
        SELECT 
            mta.Id_multa,
            mta.Id_miembro,
            mi.Nombre AS Nombre_miembro,
            mi.Cargo,
            mta.Fecha_multa,
            mta.Monto,
            mta.Pagada,
            mta.Fecha_pago
        FROM multas_miembro mta
        JOIN miembros mi ON mi.Id_miembro = mta.Id_miembro
        WHERE mta.Id_grupo = %s
        ORDER BY mta.Fecha_multa DESC, mta.Id_multa DESC
    """
    return fetch_all(sql, (id_grupo,))


def _seccion_multas(info_dir: dict):
    st.subheader("Multas")

    id_grupo = info_dir["Id_grupo"]
    miembros = _obtener_miembros_grupo(id_grupo)

    if not miembros:
        st.info("Primero registra miembros para poder asignar multas.")
        return

    # -------- Registrar nueva multa --------
    st.markdown("### Registrar nueva multa")

    # Mapa para el select
    opciones = {
        f"{m['Nombre']} ({m['Cargo']})": m["Id_miembro"]
        for m in miembros
    }

    with st.form("form_nueva_multa"):
        miembro_label = st.selectbox(
            "Miembro",
            list(opciones.keys()),
        )
        id_miembro_sel = opciones[miembro_label]

        fecha_multa = st.date_input(
            "Fecha de la multa",
            value=dt.date.today(),
        )

        monto = st.number_input(
            "Monto de la multa ($)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
        )

        pagada = st.checkbox("¿Multa pagada?")
        fecha_pago = None
        if pagada:
            fecha_pago = st.date_input(
                "Fecha de pago",
                value=dt.date.today(),
            )

        btn_guardar_multa = st.form_submit_button("Guardar multa")

    if btn_guardar_multa:
        if monto <= 0:
            st.warning("El monto de la multa debe ser mayor que 0.")
        else:
            execute(
                """
                INSERT INTO multas_miembro (
                    Id_grupo, Id_miembro, Fecha_multa, Monto, Pagada, Fecha_pago
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
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

    # -------- Listado de multas --------
    st.markdown("---")
    st.markdown("### Multas registradas")

    multas = _obtener_multas_de_grupo(id_grupo)
    if not multas:
        st.info("Aún no se han registrado multas para este grupo.")
        return

    # Mostrar en tabla simple
    st.table(multas)

    # -------- Marcar como pagada / eliminar --------
    st.markdown("### Actualizar / eliminar multa")

    opciones_multas = {
        f"{m['Id_multa']} - {m['Nombre_miembro']} - {m['Fecha_multa']} - ${m['Monto']}":
            m["Id_multa"]
        for m in multas
    }

    label_multa = st.selectbox(
        "Selecciona la multa a actualizar",
        list(opciones_multas.keys()),
        key="sel_multa",
    )
    id_multa_sel = opciones_multas[label_multa]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Marcar como pagada", type="primary"):
            hoy = dt.date.today()
            execute(
                """
                UPDATE multas_miembro
                SET Pagada = 1, Fecha_pago = %s
                WHERE Id_multa = %s
                """,
                (hoy, id_multa_sel),
            )
            st.success("Multa marcada como pagada.")
            st.rerun()
    with col2:
        if st.button("Eliminar multa", type="secondary"):
            execute(
                "DELETE FROM multas_miembro WHERE Id_multa = %s",
                (id_multa_sel,),
            )
            st.success("Multa eliminada.")
            st.rerun()


# -------------------------------------------------------------------
# Sección: Ahorro final
# Tabla: ahorro_miembro
# -------------------------------------------------------------------
def _obtener_ahorros_de_reunion(id_grupo: int, id_reunion: int):
    """
    Devuelve, para una reunión, todos los miembros del grupo con su registro
    de ahorro (si existe) para esa reunión.
    """
    sql = """
        SELECT
            a.Id_ahorro,
            m.Id_miembro,
            m.Nombre,
            m.Cargo,
            a.Saldo_inicial,
            a.Ahorro,
            a.Otras_actividades,
            a.Retiros,
            a.Saldo_final
        FROM miembros m
        LEFT JOIN ahorro_miembro a
          ON a.Id_miembro = m.Id_miembro
         AND a.Id_grupo   = %s
         AND a.Id_reunion = %s
        WHERE m.Id_grupo = %s
        ORDER BY m.Nombre
    """
    return fetch_all(sql, (id_grupo, id_reunion, id_grupo))


def _calcular_saldo_inicial_miembro(
    id_grupo: int,
    id_miembro: int,
    id_reunion: int,
    ahorro_minimo_default: float,
) -> float:
    """
    Si ya tiene reuniones anteriores, toma el Saldo_final de la más reciente
    antes de la reunión actual. Si no, usa el ahorro mínimo del reglamento.
    """
    fila_reu = fetch_one(
        "SELECT Fecha FROM reuniones_grupo WHERE Id_reunion = %s",
        (id_reunion,),
    )
    if not fila_reu:
        return ahorro_minimo_default

    fecha_actual = fila_reu["Fecha"]

    fila_prev = fetch_one(
        """
        SELECT a.Saldo_final
        FROM ahorro_miembro a
        JOIN reuniones_grupo r ON r.Id_reunion = a.Id_reunion
        WHERE a.Id_grupo = %s
          AND a.Id_miembro = %s
          AND r.Fecha < %s
        ORDER BY r.Fecha DESC, a.Id_ahorro DESC
        LIMIT 1
        """,
        (id_grupo, id_miembro, fecha_actual),
    )

    if fila_prev and fila_prev["Saldo_final"] is not None:
        return float(fila_prev["Saldo_final"])

    return ahorro_minimo_default


def _seccion_ahorro_final(info_dir: dict):
    st.subheader("Ahorro final")

    id_grupo = info_dir["Id_grupo"]

    # Necesitamos reuniones existentes
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
        st.info("Todavía no hay reuniones registradas. Primero registra asistencia.")
        return

    # Select de reunión a trabajar
    mapa_reu = {
        f"{r['Fecha']}  (Reunión #{r['Numero_reunion'] or ''} - {r['Tema'] or 'sin tema'})":
            r["Id_reunion"]
        for r in reuniones
    }

    claves = list(mapa_reu.keys())
    valores = list(mapa_reu.values())
    id_reunion_default = st.session_state.get("reunion_ahorro")

    if id_reunion_default and id_reunion_default in valores:
        idx_default = valores.index(id_reunion_default)
    else:
        idx_default = 0

    etiqueta_reu = st.selectbox(
        "Reunión a trabajar para ahorro",
        claves,
        index=idx_default,
        key="sel_reunion_ahorro",
    )
    id_reunion_sel = mapa_reu[etiqueta_reu]
    st.session_state["reunion_ahorro"] = id_reunion_sel

    regl = _obtener_reglamento_por_grupo(id_grupo)
    ahorro_minimo = float(regl["Ahorro_minimo"]) if regl and regl.get("Ahorro_minimo") is not None else 0.0

    registros = _obtener_ahorros_de_reunion(id_grupo, id_reunion_sel)
    if not registros:
        st.info("No hay miembros registrados para este grupo.")
        return

    st.markdown("---")
    st.markdown("### Registro de ahorro por miembro")
    st.caption(
        "El saldo inicial se calcula a partir del saldo final de la reunión anterior. "
        "Si es la primera reunión, se usa el ahorro mínimo del reglamento."
    )

    filas_guardado: list[tuple] = []

    with st.form(f"form_ahorro_{id_reunion_sel}"):
        # Encabezados
        cols_header = st.columns([3, 1.3, 1.3, 1.3, 1.3, 1.3])
        cols_header[0].markdown("**Miembro**")
        cols_header[1].markdown("**Saldo inicial**")
        cols_header[2].markdown("**Ahorro**")
        cols_header[3].markdown("**Otras actividades**")
        cols_header[4].markdown("**Retiros**")
        cols_header[5].markdown("**Saldo final**")

        for reg in registros:
            id_ahorro = reg["Id_ahorro"]
            id_m = reg["Id_miembro"]
            nombre = reg["Nombre"]
            cargo = reg["Cargo"]

            saldo_inicial_exist = reg["Saldo_inicial"]
            ahorro_exist = reg["Ahorro"]
            otras_exist = reg["Otras_actividades"]
            retiros_exist = reg["Retiros"]
            saldo_final_exist = reg["Saldo_final"]

            if saldo_inicial_exist is not None:
                saldo_inicial_val = float(saldo_inicial_exist)
            else:
                saldo_inicial_val = _calcular_saldo_inicial_miembro(
                    id_grupo=id_grupo,
                    id_miembro=id_m,
                    id_reunion=id_reunion_sel,
                    ahorro_minimo_default=ahorro_minimo,
                )

            ahorro_val = float(ahorro_exist) if ahorro_exist is not None else ahorro_minimo
            otras_val = float(otras_exist) if otras_exist is not None else 0.0
            retiros_val = float(retiros_exist) if retiros_exist is not None else 0.0

            cols = st.columns([3, 1.3, 1.3, 1.3, 1.3, 1.3])
            cols[0].markdown(
                f"**{nombre}**<br/><span style='font-size: 12px;'>{cargo}</span>",
                unsafe_allow_html=True,
            )

            saldo_in = cols[1].number_input(
                "",
                key=f"salini_{id_reunion_sel}_{id_m}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=saldo_inicial_val,
            )
            ahorro = cols[2].number_input(
                "",
                key=f"ahorro_{id_reunion_sel}_{id_m}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=ahorro_val,
            )
            otras = cols[3].number_input(
                "",
                key=f"otras_{id_reunion_sel}_{id_m}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=otras_val,
            )
            retiros = cols[4].number_input(
                "",
                key=f"retiros_{id_reunion_sel}_{id_m}",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=retiros_val,
            )

            saldo_final_calc = saldo_in + ahorro + otras - retiros

            # Mostrar saldo final calculado (solo lectura)
            cols[5].markdown(f"**${saldo_final_calc:,.2f}**")

            filas_guardado.append(
                (
                    id_ahorro,
                    id_m,
                    saldo_in,
                    ahorro,
                    otras,
                    retiros,
                    saldo_final_calc,
                )
            )

        btn_guardar = st.form_submit_button("Guardar ahorro de esta reunión")

    if btn_guardar:
        for (
            id_ahorro,
            id_m,
            saldo_in,
            ahorro,
            otras,
            retiros,
            saldo_final_calc,
        ) in filas_guardado:
            if id_ahorro:
                # UPDATE
                execute(
                    """
                    UPDATE ahorro_miembro
                    SET Saldo_inicial = %s,
                        Ahorro = %s,
                        Otras_actividades = %s,
                        Retiros = %s,
                        Saldo_final = %s
                    WHERE Id_ahorro = %s
                    """,
                    (
                        saldo_in,
                        ahorro,
                        otras,
                        retiros,
                        saldo_final_calc,
                        id_ahorro,
                    ),
                )
            else:
                # INSERT
                execute(
                    """
                    INSERT INTO ahorro_miembro (
                        Id_grupo,
                        Id_reunion,
                        Id_miembro,
                        Saldo_inicial,
                        Ahorro,
                        Otras_actividades,
                        Retiros,
                        Saldo_final
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        id_grupo,
                        id_reunion_sel,
                        id_m,
                        saldo_in,
                        ahorro,
                        otras,
                        retiros,
                        saldo_final_calc,
                    ),
                )

        st.success("Ahorro de la reunión guardado correctamente.")
        st.rerun()

    # -------- Resumen de la reunión --------
    st.markdown("---")
    st.markdown("### Resumen de ahorro de la reunión")

    resumen = fetch_all(
        """
        SELECT
            m.Nombre,
            m.Cargo,
            a.Saldo_inicial,
            a.Ahorro,
            a.Otras_actividades,
            a.Retiros,
            a.Saldo_final
        FROM ahorro_miembro a
        JOIN miembros m ON m.Id_miembro = a.Id_miembro
        WHERE a.Id_grupo = %s
          AND a.Id_reunion = %s
        ORDER BY m.Nombre
        """,
        (id_grupo, id_reunion_sel),
    )

    if resumen:
        st.table(resumen)
    else:
        st.info("Todavía no hay registros de ahorro guardados para esta reunión.")


# -------------------------------------------------------------------
# Panel principal de Directiva
# -------------------------------------------------------------------
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

    # Préstamos (pendiente)
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
        st.info("Aquí se implementarán los reportes con gráficos de ingresos, egresos y consolidado.")
