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
            Sexo,
            Cargo
        FROM miembros
        WHERE Id_grupo = %s
        ORDER BY Cargo, Nombre
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
            hoy = dt.date.today()
            fecha_fin_ciclo = st.date_input(
                "Fecha estimada de cierre del ciclo",
                value=hoy.replace(year=hoy.year + 1),
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
        sexo_m = st.selectbox("Sexo", ["F", "M", "Otro"], index=0)
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
# Tablas: reuniones_grupo, asistencia_miembro
# -------------------------------------------------------
def _obtener_reuniones_de_grupo(id_grupo: int):
    sql = """
        SELECT Id_reunion, Fecha, Numero_reunion, Tema
        FROM reuniones_grupo
        WHERE Id_grupo = %s
        ORDER BY Fecha DESC, Id_reunion DESC
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_asistencia_reunion(id_reunion: int):
    sql = """
        SELECT Id_miembro, Presente
        FROM asistencia_miembro
        WHERE Id_reunion = %s
    """
    filas = fetch_all(sql, (id_reunion,))
    return {f["Id_miembro"]: bool(f["Presente"]) for f in filas}


def _seccion_asistencia(info_dir: dict):
    st.subheader("Asistencia a reuniones")

    id_grupo = info_dir["Id_grupo"]

    # --------------------------------------------------
    # Crear / abrir reunión
    # --------------------------------------------------
    st.markdown("### Crear o abrir reunión")

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
                "Ya existía una reunión en esa fecha, "
                "se abrió para editar asistencia."
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

    # --------------------------------------------------
    # Listar reuniones del grupo
    # --------------------------------------------------
    reuniones = _obtener_reuniones_de_grupo(id_grupo)

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

    # --------------------------------------------------
    # Asistencia de miembros
    # --------------------------------------------------
    st.markdown("### Lista de miembros y asistencia")

    miembros = _obtener_miembros_grupo(id_grupo)
    if not miembros:
        st.warning("No hay miembros registrados para este grupo.")
        return

    asist_map = _obtener_asistencia_reunion(id_reunion_sel)

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

    # --------------------------------------------------
    # Resumen y opciones avanzadas
    # --------------------------------------------------
    total_presentes = sum(1 for v in estados.values() if v)
    st.metric("Total presentes en esta reunión", total_presentes)

    with st.expander("Opciones avanzadas"):
        if st.button(
            "Eliminar esta reunión (incluye asistencia)",
            type="secondary",
            key="btn_eliminar_reunion",
        ):
            execute(
                "DELETE FROM reuniones_grupo WHERE Id_reunion = %s",
                (id_reunion_sel,),
            )
            st.success("Reunión eliminada.")
            if "reunion_abierta" in st.session_state:
                del st.session_state["reunion_abierta"]
            st.rerun()

    # Mostrar tabla de asistencia resumida
    st.markdown("#### Resumen de asistencia de esta reunión")
    resumen = []
    for m in miembros:
        presente = estados.get(m["Id_miembro"], False)
        resumen.append(
            {
                "Miembro": m["Nombre"],
                "Sexo": m["Sexo"],
                "Cargo": m["Cargo"],
                "Presente": "Sí" if presente else "No",
            }
        )
    st.table(resumen)


# -------------------------------------------------------
# Sección: Multas
# Tabla: multas_miembro
# -------------------------------------------------------
def _obtener_multas_de_grupo(id_grupo: int):
    sql = """
        SELECT 
            mm.Id_multa,
            mm.Id_miembro,
            mb.Nombre AS Nombre_miembro,
            mb.Cargo,
            mm.Fecha_multa,
            mm.Monto,
            mm.Pagada,
            mm.Fecha_pago
        FROM multas_miembro mm
        JOIN miembros mb ON mb.Id_miembro = mm.Id_miembro
        WHERE mm.Id_grupo = %s
        ORDER BY mm.Fecha_multa DESC, mm.Id_multa DESC
    """
    return fetch_all(sql, (id_grupo,))


def _seccion_multas(info_dir: dict):
    st.subheader("Multas del grupo")

    id_grupo = info_dir["Id_grupo"]
    nombre_grupo = info_dir["Nombre_grupo"]

    st.caption(f"Grupo: **{nombre_grupo}** — Id_grupo: {id_grupo}")

    miembros = _obtener_miembros_grupo(id_grupo)
    if not miembros:
        st.info("Primero registra miembros para poder asignar multas.")
        return

    # --------------------------------------------------
    # Registrar nueva multa
    # --------------------------------------------------
    st.markdown("### Registrar nueva multa")

    opciones_miembros = {
        f"{m['Nombre']} ({m['Cargo']})": m["Id_miembro"] for m in miembros
    }
    nombres_miembros = list(opciones_miembros.keys())

    with st.form("form_nueva_multa"):
        miembro_sel = st.selectbox(
            "Miembro",
            nombres_miembros,
            key="multa_miembro",
        )
        fecha_multa = st.date_input(
            "Fecha de la multa",
            value=dt.date.today(),
            key="fecha_multa",
        )
        monto = st.number_input(
            "Monto de la multa ($)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            key="monto_multa",
        )
        pagada_inicial = st.checkbox(
            "¿Marcar como pagada desde ya?",
            value=False,
            key="pagada_inicial",
        )

        if pagada_inicial:
            fecha_pago = st.date_input(
                "Fecha de pago",
                value=dt.date.today(),
                key="fecha_pago_inicial",
            )
        else:
            fecha_pago = None

        btn_guardar_multa = st.form_submit_button("Guardar multa")

    if btn_guardar_multa:
        id_miembro = opciones_miembros[miembro_sel]

        execute(
            """
            INSERT INTO multas_miembro 
                (Id_grupo, Id_miembro, Fecha_multa, Monto, Pagada, Fecha_pago)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                id_grupo,
                id_miembro,
                fecha_multa,
                monto,
                1 if pagada_inicial else 0,
                fecha_pago,
            ),
        )
        st.success("Multa registrada correctamente.")
        st.rerun()

    st.markdown("---")

    # --------------------------------------------------
    # Listado de multas
    # --------------------------------------------------
    st.markdown("### Multas registradas")

    multas = _obtener_multas_de_grupo(id_grupo)

    if not multas:
        st.info("Todavía no hay multas registradas para este grupo.")
        return

    # Tabla resumen
    tabla = []
    for m in multas:
        tabla.append(
            {
                "ID": m["Id_multa"],
                "Miembro": m["Nombre_miembro"],
                "Cargo": m["Cargo"],
                "Fecha multa": m["Fecha_multa"],
                "Monto": float(m["Monto"]),
                "Pagada": "Sí" if m["Pagada"] else "No",
                "Fecha pago": m["Fecha_pago"] or "",
            }
        )

    st.table(tabla)

    # --------------------------------------------------
    # Marcar multas como pagadas
    # --------------------------------------------------
    st.markdown("### Marcar multa como pagada")

    multas_pendientes = [m for m in multas if not m["Pagada"]]

    if not multas_pendientes:
        st.info("Todas las multas están pagadas.")
        return

    opciones_pendientes = {
        f"{m['Id_multa']} - {m['Nombre_miembro']} "
        f"({m['Fecha_multa']} - ${m['Monto']})": m["Id_multa"]
        for m in multas_pendientes
    }

    with st.form("form_pagar_multa"):
        etiqueta = st.selectbox(
            "Selecciona la multa a marcar como pagada",
            list(opciones_pendientes.keys()),
            key="multa_pagar",
        )
        fecha_pago = st.date_input(
            "Fecha de pago",
            value=dt.date.today(),
            key="fecha_pago_marcar",
        )
        btn_pagar = st.form_submit_button("Marcar como pagada")

    if btn_pagar:
        id_multa_sel = opciones_pendientes[etiqueta]
        execute(
            """
            UPDATE multas_miembro
            SET Pagada = 1, Fecha_pago = %s
            WHERE Id_multa = %s AND Id_grupo = %s
            """,
            (fecha_pago, id_multa_sel, id_grupo),
        )
        st.success("Multa actualizada como pagada.")
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

    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            "Multas",
            "Caja",
            "Ahorro final",
            "Cierre de ciclo",
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

    # Las demás secciones se irán implementando paso a paso
    with tabs[4]:
        st.info("Aquí se implementará el manejo de caja.")
    with tabs[5]:
        st.info("Aquí se implementará el formulario de ahorro final.")
    with tabs[6]:
        st.info("Aquí se implementará el cierre de ciclo.")
