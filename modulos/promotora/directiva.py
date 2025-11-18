import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute


def _get_usuario_actual():
    """Devuelve el dict de usuario que se guardó en sesión al hacer login."""
    usuario = st.session_state.get("usuario")
    if not usuario:
        st.error("No hay una sesión activa.")
        st.stop()
    return usuario


def _get_promotora_actual():
    """Busca en la tabla promotora usando el DUI del usuario logueado."""
    usuario = _get_usuario_actual()
    dui = usuario["DUI"]

    promotora = fetch_one(
        "SELECT Id_promotora, Nombre FROM promotora WHERE DUI = %s",
        (dui,),
    )
    if not promotora:
        st.error(
            f"No se encontró una promotora registrada para el DUI {dui}. "
            "Pida al administrador que revise la tabla 'promotora'."
        )
        st.stop()

    return promotora


def crear_directiva_panel():
    """
    Pestaña 'Crear Directiva' para la PROMOTORA.
    Crea:
      - registro en tabla 'usuario' con rol DIRECTIVA
      - registro en tabla 'directiva' vinculado a un grupo
    """

    st.header("Crear usuario para Directiva del grupo")

    promotora = _get_promotora_actual()
    id_promotora = promotora["Id_promotora"]

    # 1. Obtener los grupos de ESTA promotora
    grupos = fetch_all(
        """
        SELECT g.Id_grupo, g.Nombre, d.Nombre AS Distrito
        FROM grupos g
        JOIN distritos d ON g.Id_distrito = d.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Nombre ASC
        """,
        (id_promotora,),
    )

    if not grupos:
        st.info(
            "Todavía no tiene grupos registrados. "
            "Primero cree un grupo en la pestaña **Crear grupo**."
        )
        return

    # Opciones para el selectbox
    opciones_grupo = [
        (g["Id_grupo"], f"{g['Nombre']} ({g['Distrito']})") for g in grupos
    ]

    # 2. Necesitamos el Id_rol para el rol DIRECTIVA
    rol_directiva = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA'"
    )
    if not rol_directiva:
        st.error(
            "No existe el rol 'DIRECTIVA' en la tabla 'rol'. "
            "Regístrelo primero en phpMyAdmin."
        )
        return

    id_rol_directiva = rol_directiva["Id_rol"]

    st.write(
        "Este formulario crea un usuario que será compartido por "
        "Presidenta y Secretaria del grupo (misma cuenta)."
    )

    with st.form("form_crear_directiva"):
        nombre = st.text_input("Nombre completo de la Directiva")
        dui = st.text_input("DUI de la Directiva (solo números o con guión)")
        contrasenia = st.text_input("Contraseña para el usuario", type="password")

        id_grupo_sel = st.selectbox(
            "Grupo al que se asignará la Directiva",
            options=[g[0] for g in opciones_grupo],
            format_func=lambda gid: next(
                etiqueta for (idg, etiqueta) in opciones_grupo if idg == gid
            ),
        )

        crear = st.form_submit_button("Crear usuario de Directiva")

    if not crear:
        return

    # Validaciones básicas
    if not nombre.strip() or not dui.strip() or not contrasenia:
        st.warning("Todos los campos son obligatorios.")
        return

    # 3. Verificar que el grupo no tenga ya una directiva asignada
    ya_existe = fetch_one(
        "SELECT Id_directiva FROM directiva WHERE Id_grupo = %s",
        (id_grupo_sel,),
    )
    if ya_existe:
        st.error(
            "Este grupo ya tiene un usuario de Directiva asignado. "
            "Si necesita cambiarlo, el administrador debe modificarlo desde la base de datos."
        )
        return

    try:
        # 4. Crear el usuario en tabla 'usuario'
        execute(
            """
            INSERT INTO usuario (Nombre, DUI, Contraseña, Id_rol)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre.strip(), dui.strip(), contrasenia, id_rol_directiva),
        )

        # 5. Crear el registro en tabla 'directiva'
        execute(
            """
            INSERT INTO directiva (Nombre, DUI, Contraseña, Id_grupo, Creado_en)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nombre.strip(), dui.strip(), contrasenia, id_grupo_sel, date.today()),
        )

        st.success(
            "Usuario de Directiva creado correctamente y asignado al grupo seleccionado."
        )

    except IntegrityError as e:
        st.error(
            "Error de integridad al crear la Directiva. "
            "Revise si ya existe un usuario con ese DUI o una directiva para ese grupo."
        )
        st.exception(e)
    except Exception as e:
        st.error("Ocurrió un error inesperado al crear la Directiva.")
        st.exception(e)
