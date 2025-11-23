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


def _obtener_reuniones_grupo(id_grupo: int):
    """
    Devuelve las reuniones ya registradas para un grupo.
    """
    sql = """
        SELECT Id_reunion, Fecha, Numero_reunion, Tema
        FROM reuniones_grupo
        WHERE Id_grupo = %s
        ORDER BY Fecha DESC, Id_reunion DESC
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_asistencia_reunion(id_reunion: int) -> dict:
    """
    Devuelve un diccionario {Id_miembro: True/False} con la asistencia
    registrada para una reunión dada.
    """
    sql = """
        SELECT Id_miembro, Presente
        FROM asistencia_miembro
        WHERE Id_reunion = %s
    """
    filas = fetch_all(sql, (id_reunion,))
    return {f["Id_miembro"]: bool(f["Presente"]) for f in filas}


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
        sexo_m = st.selectbox("Sexo", ["Femenino", "Masculino", "Otro"])
        cargo_m = st.selectbox("Cargo dentro del grupo", cargos_posibles)

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


def _seccion_asistencia(info_dir: dict):
    st.subheader("Asistencia a reuniones")

    id_grupo = info_dir["Id_grupo"]

    # ---------- Crear / usar reunión ----------
    st.markdown("### Crear o abrir reunión")

    with st.form("form_crear_reunion"):
        fecha = st.date_input("Fecha de la reunión", value=dt.date.today())
        numero = st.number_input(
            "Número de reunión en el ciclo",
            min_value=1,
            step=1,
            value=1,
        )
        tema = st.text_input(
            "Tema u observaciones (opcional)",
            value="",
        )

        btn_crear = st.form_submit_button("Crear / usar esta reunión")

    if btn_crear:
        # ¿Existe ya una reunión con esa fecha?
        existente = fetch_one(
            """
            SELECT Id_reunion
            FROM reuniones_grupo
            WHERE Id_grupo = %s AND Fecha = %s
            LIMIT 1
            """,
            (id_grupo, fecha),
        )

        if existente:
            id_reunion = existente["Id_reunion"]
            st.info(
                "Ya existía una reunión en esa fecha. "
                "Se abrió para editar la asistencia."
            )
        else:
            id_reunion = execute(
                """
                INSERT INTO reuniones_grupo (Id_grupo, Fecha, Numero_reunion, Tema)
                VALUES (%s, %s, %s, %s)
                """,
                (id_grupo, fecha, numero, tema),
                return_last_id=True,
            )
            st.success("Reunión creada correctamente.")

        st.session_state["reunion_abierta"] = id_reunion
        st.rerun()

    # ---------- Listado de reuniones ----------
    reuniones = _obtener_reuniones_grupo(id_grupo)

    if not reuniones:
        st.info("Todavía no hay reuniones registradas para este grupo.")
        return

    reunion_abierta = st.session_state.get("reunion_abierta")

    opciones = {
        f"{r['Fecha']}  (#{r['Numero_reunion']} — {r['Tema'] or 'sin tema'})": r[
            "Id_reunion"
        ]
        for r in reuniones
    }
    etiquetas = list(opciones.keys())
    valores = list(opciones.values())

    if reunion_abierta in valores:
        idx_default = valores.index(reunion_abierta)
    else:
        idx_default = 0

    etiqueta_sel = st.selectbox(
        "Reunión a trabajar",
        etiquetas,
        index=idx_default,
        key="sel_reunion_asistencia",
    )
    id_reunion_sel = opciones[etiqueta_sel]

    st.markdown("---")
    st.markdown("### Lista de miembros y asistencia")

    miembros = _obtener_miembros_grupo(id_grupo)
    if not miembros:
        st.warning("No hay miembros registrados en este grupo.")
        return

    asistencia_actual = _obtener_asistencia_reunion(id_reunion_sel)

    with st.form(f"form_asistencia_{id_reunion_sel}"):
        estados: dict[int, bool] = {}
        for m in miembros:
            label = f"{m['Nombre']} — {m['Sexo']} — {m['Cargo']}"
            estados[m["Id_miembro"]] = st.checkbox(
                label,
                value=asistencia_actual.get(m["Id_miembro"], False),
                key=f"asis_{id_reunion_sel}_{m['Id_miembro']}",
            )

        btn_guardar = st.form_submit_button("Guardar asistencia")

    if btn_guardar:
        # borrar registros anteriores de esa reunión
        execute(
            "DELETE FROM asistencia_miembro WHERE Id_reunion = %s",
            (id_reunion_sel,),
        )

        # insertar la asistencia actual
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
            "Verifica que el DUI del usuario esté registrado en la tabla "
            "'directiva'."
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

    # Las demás secciones se irán implementando paso a paso
    with tabs[3]:
        st.info("Aquí se implementará el manejo de multas.")
    with tabs[4]:
        st.info("Aquí se implementará el manejo de caja.")
    with tabs[5]:
        st.info("Aquí se implementará el formulario de ahorro final.")
    with tabs[6]:
        st.info("Aquí se implementará el cierre de ciclo.")
