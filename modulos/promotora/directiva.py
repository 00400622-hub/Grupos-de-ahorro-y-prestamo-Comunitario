import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute


# -------------------------------------------------
# Helpers para obtener usuario y promotora actual
# -------------------------------------------------

def _get_usuario_actual():
    """Devuelve el usuario logueado guardado en st.session_state."""
    return st.session_state.get("usuario")


def _get_promotora_actual():
    """
    Devuelve el registro de la promotora asociada al usuario logueado,
    usando el DUI que viene en st.session_state["usuario"].
    """
    user = _get_usuario_actual()
    if not user:
        return None

    dui = user.get("DUI")
    if not dui:
        return None

    return fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s",
        (dui,),
    )


# -------------------------------------------------
# Pestaña "Crear Directiva" (se llama desde grupos.py)
# -------------------------------------------------

def crear_directiva_panel():
    st.header("Crear Directiva")

    # 1. Validar promotora
    promotora = _get_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada a este usuario.\n\n"
            "Verifica que el DUI del usuario exista en la tabla 'promotora'."
        )
        return

    id_promotora = promotora["Id_promotora"]
    st.info(
        f"Sesión de promotora: **{promotora['Nombre']}** "
        f"(Id_promotora={id_promotora}, DUI: {promotora['DUI']})"
    )

    # 2. Cargar SOLO los grupos de esta promotora
    grupos = fetch_all(
        """
        SELECT Id_grupo, Nombre
        FROM grupos
        WHERE Id_promotora = %s
          AND Estado = 'ACTIVO'
        ORDER BY Id_grupo ASC
        """,
        (id_promotora,),
    )

    if not grupos:
        st.warning(
            "Todavía no tienes grupos activos registrados. "
            "Primero crea un grupo en la pestaña 'Crear grupo'."
        )
        return

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"]
        for g in grupos
    }

    # 3. Formulario para crear el usuario de directiva
    with st.form("form_crear_directiva"):
        nombre = st.text_input(
            "Nombre de la directiva (Presidente/Secretaria)",
            max_chars=120,
        )
        dui_dir = st.text_input(
            "DUI de la directiva (con o sin guion)",
            max_chars=20,
        )
        contrasena = st.text_input(
            "Contraseña para que la directiva inicie sesión",
            type="password",
            max_chars=255,
        )
        grupo_label = st.selectbox(
            "Grupo al que se asignará esta directiva",
            list(opciones_grupo.keys()),
        )

        crear_btn = st.form_submit_button("Crear usuario de directiva")

    if not crear_btn:
        return

    # 4. Validaciones básicas
    if not nombre.strip() or not dui_dir.strip() or not contrasena:
        st.error("Todos los campos (nombre, DUI y contraseña) son obligatorios.")
        return

    dui_digits = "".join(ch for ch in dui_dir if ch.isdigit())
    if len(dui_digits) != 9:
        st.error("El DUI debe tener exactamente 9 dígitos (con o sin guion).")
        return

    id_grupo = opciones_grupo[grupo_label]

    # 5. Insertar en tabla 'directiva'
    try:
        execute(
            """
            INSERT INTO directiva
                (Nombre, DUI, Contrasena, Id_grupo, Activo, Creado_en)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nombre.strip(),
                dui_digits,              # guardamos solo dígitos
                contrasena,              # si luego quieres, aquí puedes encriptar
                id_grupo,
                1,                       # Activo = 1
                date.today(),
            ),
        )
    except IntegrityError:
        st.error(
            "Ya existe una directiva registrada con ese DUI.\n\n"
            "Si quieres cambiarla de grupo, edítala o elimínala "
            "desde phpMyAdmin o implementa un formulario de edición."
        )
        return

    st.success(
        f"Directiva creada correctamente y asignada al grupo: **{grupo_label}**."
    )
    st.info(
        "Recuerda que para que la directiva pueda iniciar sesión en el sistema, "
        "debes tener también un usuario en la tabla 'Usuario' con este mismo DUI "
        "y rol DIRECTIVA (esto se puede automatizar más adelante)."
    )
