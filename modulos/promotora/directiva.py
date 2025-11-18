import streamlit as st
from datetime import date
from modulos.config.conexion import fetch_all, fetch_one, execute


def _get_promotora_actual():
    """Devuelve el registro de la promotora asociado al usuario logueado."""
    user = st.session_state.get("usuario")
    if not user:
        return None

    dui = user.get("DUI")
    if not dui:
        return None

    prom = fetch_one(
        "SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s",
        (dui,),
    )
    return prom


def crear_directiva_panel():
    st.header("Crear usuario de Directiva")

    # 1. Obtener promotora actual
    promotora = _get_promotora_actual()
    if not promotora:
        st.error(
            "No se encontró una promotora asociada al usuario actual. "
            "Verifique que este usuario esté registrado en la tabla 'promotora'."
        )
        return

    id_promotora = promotora["Id_promotora"]
    dui_promotora = promotora["DUI"]

    st.info(f"Promotora actual: **{promotora['Nombre']}** (DUI: {dui_promotora})")

    # 2. Cargar grupos de esta promotora
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
        st.warning(
            "Todavía no tienes grupos registrados. "
            "Primero crea al menos un grupo para poder asignarlo a una directiva."
        )
        return

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_crear_directiva"):
        st.subheader("Datos de la directiva")

        nombre = st.text_input("Nombre completo de la directiva")
        dui_directiva = st.text_input("DUI de la directiva (sin guiones o como prefieras)")
        contrasenia = st.text_input("Contraseña para la directiva", type="password")

        st.subheader("Grupo asignado")
        etiqueta_grupo = st.selectbox(
            "Seleccione el grupo al que pertenece esta directiva",
            list(opciones_grupo.keys()),
        )
        id_grupo = opciones_grupo[etiqueta_grupo]

        crear_btn = st.form_submit_button("Crear usuario de Directiva")

    if not crear_btn:
        return

    # Validaciones básicas
    if not nombre.strip() or not dui_directiva.strip() or not contrasenia:
        st.error("Todos los campos son obligatorios.")
        return

    # 3. Verificar que el grupo aún no tenga directiva
    existe_dir = fetch_one(
        "SELECT Id_directiva FROM directiva WHERE Id_grupo = %s",
        (id_grupo,),
    )
    if existe_dir:
        st.error(
            "Este grupo ya tiene una directiva asignada. "
            "Si necesitas cambiarla, deberás editarla o eliminarla manualmente."
        )
        return

    # 4. Verificar que no exista ya un usuario con ese DUI
    usuario_existente = fetch_one(
        "SELECT Id_usuario, Nombre, DUI FROM Usuario WHERE DUI = %s",
        (dui_directiva.strip(),),
    )
    if usuario_existente:
        st.error(
            f"Ya existe un usuario con ese DUI ({usuario_existente['DUI']}). "
            "Usa otro DUI o edita el usuario existente."
        )
        return

    # 5. Obtener el Id_rol de DIRECTIVA
    rol_dir = fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA'"
    )
    if not rol_dir:
        st.error(
            "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
            "Crea ese rol primero."
        )
        return

    id_rol_directiva = rol_dir["Id_rol"]

    # 6. Crear el usuario en la tabla Usuario
    uid = execute(
        """
        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre.strip(), dui_directiva.strip(), contrasenia, id_rol_directiva),
    )

    # 7. Registrar en la tabla directiva
    execute(
        """
        INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre.strip(), dui_directiva.strip(), id_grupo, date.today()),
    )

    st.success(
        f"Usuario de directiva creado correctamente (Id_usuario={uid}) "
        f"y asignado al grupo {etiqueta_grupo}."
    )

    st.caption(
        "Recuerda: la directiva usará ese DUI y contraseña para iniciar sesión "
        "con el rol DIRECTIVA y solo verá la información del grupo asignado."
    )

    # 8. Mostrar directivas registradas para los grupos de esta promotora
    st.subheader("Directivas registradas en tus grupos")

    directivas = fetch_all(
        """
        SELECT dir.Id_directiva,
               dir.Nombre AS Directiva,
               dir.DUI,
               g.Id_grupo,
               g.Nombre AS Grupo,
               d.Nombre AS Distrito
        FROM directiva dir
        JOIN grupos g ON dir.Id_grupo = g.Id_grupo
        JOIN distritos d ON g.Id_distrito = d.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo ASC
        """,
        (id_promotora,),
    )

    if not directivas:
        st.info("Todavía no hay directivas registradas para tus grupos.")
        return

    st.table(directivas)
