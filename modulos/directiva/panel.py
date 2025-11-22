# modulos/directiva/panel.py

import streamlit as st
from datetime import date

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


# -------------------------------------------------------
# Helpers: obtener directiva y grupo asignado
# -------------------------------------------------------
def _obtener_directiva_actual():
    """
    Busca en la tabla 'directiva' usando el DUI del usuario en sesión.
    Devuelve dict con datos de la directiva y del grupo.
    """
    user = get_user()
    if not user:
        return None, None

    # Directiva identificada por DUI
    dir_row = fetch_one(
        """
        SELECT d.Id_directiva, d.Nombre, d.DUI, d.Id_grupo, d.Creado_en
        FROM directiva d
        WHERE d.DUI = %s
        LIMIT 1
        """,
        (user["DUI"],),
    )

    if not dir_row:
        return None, None

    grupo = fetch_one(
        """
        SELECT g.Id_grupo, g.Nombre, d.Nombre AS Distrito
        FROM grupos g
        LEFT JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE g.Id_grupo = %s
        LIMIT 1
        """,
        (dir_row["Id_grupo"],),
    )

    return dir_row, grupo


# -------------------------------------------------------
# TAB 1: Reglamento interno
# -------------------------------------------------------
def _tab_reglamento(dir_row: dict, grupo: dict):
    st.subheader("Reglamento interno del grupo")

    st.caption(
        f"Directiva: {dir_row['Nombre']} — DUI: {dir_row['DUI']}  |  "
        f"Grupo: {grupo['Nombre']} ({grupo.get('Distrito','')})"
    )

    id_grupo = grupo["Id_grupo"]

    # 1) Mostrar reglas existentes
    reglas = fetch_all(
        """
        SELECT Id_regla, Numero_regla, Texto, Creado_en
        FROM reglas_internas
        WHERE Id_grupo = %s
        ORDER BY Numero_regla ASC
        """,
        (id_grupo,),
    )

    if reglas:
        st.write("Reglas registradas para este grupo:")
        st.table(reglas)
    else:
        st.info("Aún no hay reglas registradas para este grupo.")

    st.markdown("---")

    # 2) Agregar nueva regla
    st.markdown("### Agregar nueva regla")

    with st.form("form_nueva_regla"):
        texto = st.text_area(
            "Texto de la regla",
            help="Describe claramente la regla tal como aparece en el formulario de reglas internas.",
        )
        enviar = st.form_submit_button("Guardar nueva regla")

    if enviar:
        if not texto.strip():
            st.warning("El texto de la regla no puede estar vacío.")
        else:
            # Calcular siguiente número de regla
            fila = fetch_one(
                """
                SELECT COALESCE(MAX(Numero_regla), 0) + 1 AS siguiente
                FROM reglas_internas
                WHERE Id_grupo = %s
                """,
                (id_grupo,),
            )
            sig_num = fila["siguiente"]

            execute(
                """
                INSERT INTO reglas_internas (Id_grupo, Numero_regla, Texto, Creado_en)
                VALUES (%s, %s, %s, %s)
                """,
                (id_grupo, sig_num, texto.strip(), date.today()),
            )
            st.success(f"Regla #{sig_num} agregada correctamente.")
            st.rerun()

    # 3) Eliminar regla existente
    st.markdown("---")
    st.markdown("### Eliminar una regla")

    if not reglas:
        st.info("No hay reglas para eliminar.")
        return

    opciones_reglas = {
        f"{r['Numero_regla']} - {r['Texto'][:60]}": r["Id_regla"] for r in reglas
    }

    etiqueta_sel = st.selectbox(
        "Selecciona la regla a eliminar",
        list(opciones_reglas.keys()),
        key="regla_a_eliminar",
    )
    id_regla_sel = opciones_reglas[etiqueta_sel]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar la regla seleccionada.",
        key="chk_eliminar_regla",
    )

    if st.button("Eliminar regla", type="secondary"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            execute(
                "DELETE FROM reglas_internas WHERE Id_regla = %s AND Id_grupo = %s",
                (id_regla_sel, id_grupo),
            )
            st.success("Regla eliminada correctamente.")
            st.rerun()


# -------------------------------------------------------
# Placeholders para las otras pestañas
# (las iremos llenando poco a poco)
# -------------------------------------------------------
def _tab_miembros(dir_row: dict, grupo: dict):
    st.subheader("Miembros del grupo")
    st.info("Aquí implementaremos el registro de miembros (Id_miembro, Nombre, DUI, Cargo).")


def _tab_asistencia(dir_row: dict, grupo: dict):
    st.subheader("Asistencia a reuniones")
    st.info("Aquí implementaremos el formulario de asistencia según tu PDF.")


def _tab_ahorros(dir_row: dict, grupo: dict):
    st.subheader("Ahorros")
    st.info("Aquí implementaremos el registro de ahorros (ahorro normal, ahorro final, etc.).")


def _tab_caja_prestamos(dir_row: dict, grupo: dict):
    st.subheader("Caja y préstamos")
    st.info("Aquí implementaremos movimientos de caja y control de préstamos.")


def _tab_multas(dir_row: dict, grupo: dict):
    st.subheader("Multas")
    st.info("Aquí implementaremos la asignación y pago de multas basadas en las reglas.")


def _tab_cierre_ciclo(dir_row: dict, grupo: dict):
    st.subheader("Cierre de ciclo")
    st.info("Aquí implementaremos los cálculos de cierre de ciclo y distribución de ahorros.")


# -------------------------------------------------------
# Panel principal de Directiva
# -------------------------------------------------------
@require_auth
@has_role("DIRECTIVA")
def directiva_panel():
    dir_row, grupo = _obtener_directiva_actual()

    if not dir_row or not grupo:
        st.error(
            "No se encontró un registro de directiva asociado a tu usuario. "
            "Verifica en la tabla 'directiva' que el DUI coincida con el usuario "
            "con el que estás iniciando sesión."
        )
        return

    st.title("Panel de Directiva")

    tabs = st.tabs(
        [
            "Reglamento",
            "Miembros",
            "Asistencia",
            "Ahorros",
            "Caja / Préstamos",
            "Multas",
            "Cierre de ciclo",
        ]
    )

    with tabs[0]:
        _tab_reglamento(dir_row, grupo)

    with tabs[1]:
        _tab_miembros(dir_row, grupo)

    with tabs[2]:
        _tab_asistencia(dir_row, grupo)

    with tabs[3]:
        _tab_ahorros(dir_row, grupo)

    with tabs[4]:
        _tab_caja_prestamos(dir_row, grupo)

    with tabs[5]:
        _tab_multas(dir_row, grupo)

    with tabs[6]:
        _tab_cierre_ciclo(dir_row, grupo)
