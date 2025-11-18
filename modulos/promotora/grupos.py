import streamlit as st
from datetime import date
import bcrypt

from modulos.config.conexion import db_conn


# -----------------------------
# Helpers básicos de BD
# -----------------------------
def _fetch_all(sql, params=None):
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()


def _fetch_one(sql, params=None):
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchone()


def _execute(sql, params=None, return_last_id=False):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(sql, params or ())
        con.commit()
        if return_last_id:
            return cur.lastrowid
        return None


# -----------------------------
# Helpers de sesión / usuario (versión simple)
# -----------------------------
def _obtener_usuario_de_sesion():
    """
    Versión simple: usamos exactamente la misma lógica que te funcionaba antes.
    Si no existe st.session_state["usuario"], cortamos.
    """
    if "usuario" not in st.session_state:
        st.error("No hay una sesión activa. Inicia sesión nuevamente.")
        st.stop()

    return st.session_state["usuario"]


def _validar_promotora(usuario):
    rol = str(
        usuario.get("Rol")
        or usuario.get("rol")
        or usuario.get("Tipo de rol")
        or usuario.get("tipo de rol")
        or ""
    ).upper()

    if rol != "PROMOTORA":
        st.error("Acceso restringido: esta sección es solo para Promotoras.")
        st.stop()


def _obtener_promotora_desde_usuario(usuario):
    """
    A partir de los datos del usuario logueado en la tabla Usuario,
    se asegura que exista un registro en la tabla 'promotora' con el mismo DUI.
    Devuelve el registro de la tabla promotora.
    """
    dui = usuario.get("DUI") or usuario.get("dui")
    nombre = usuario.get("Nombre") or usuario.get("nombre")

    if not dui:
        st.error("No se encontró el DUI en la sesión del usuario.")
        st.stop()

    fila = _fetch_one("SELECT * FROM promotora WHERE DUI = %s", (dui,))
    if fila:
        return fila

    # Si no existe, lo creamos
    nuevo_id = _execute(
        "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
        (nombre, dui),
        return_last_id=True,
    )

    return {
        "Id_promotora": nuevo_id,
        "Nombre": nombre,
        "DUI": dui,
    }


# -----------------------------
# Helpers de datos
# -----------------------------
def _listar_distritos():
    return _fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre ASC"
    )


def _listar_grupos_de_promotora(id_promotora):
    sql = """
        SELECT g.Id_grupo,
               g.Nombre,
               d.Nombre AS Distrito,
               g.Estado,
               g.Creado_en
        FROM grupos g
        JOIN distritos d ON d.Id_distrito = g.Id_distrito
        WHERE g.Id_promotora = %s
        ORDER BY g.Id_grupo ASC
    """
    return _fetch_all(sql, (id_promotora,))


# -----------------------------
# Vista: Crear grupo
# -----------------------------
def _vista_crear_grupo(promotora, usuario):
    st.subheader("Registrar un nuevo grupo de ahorro")

    distritos = _listar_distritos()
    if not distritos:
        st.info("Todavía no hay distritos creados por el Administrador.")
        return

    opciones = {f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"] for d in distritos}

    with st.form("form_crear_grupo"):
        nombre = st.text_input("Nombre del grupo")
        etiqueta_distrito = st.selectbox(
            "Distrito al que pertenece el grupo", list(opciones.keys())
        )
        enviar = st.form_submit_button("Crear grupo")

        if enviar:
            if not nombre.strip():
                st.warning("Debes escribir un nombre de grupo.")
                return

            id_distrito = opciones[etiqueta_distrito]
            hoy = date.today()

            id_usuario = (
                usuario.get("Id_usuario")
                or usuario.get("id_usuario")
                or usuario.get("ID_usuario")
            )

            dui_prom = promotora["DUI"]
            duis_promotoras = dui_prom  # en el futuro puedes concatenar más DUIs

            sql = """
                INSERT INTO grupos
                    (Nombre, Id_distrito, Estado, Creado_por, Creado_en,
                     Id_promotora, DUIs_promotoras)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                nombre.strip(),
                id_distrito,
                "ACTIVO",
                id_usuario,
                hoy,
                promotora["Id_promotora"],
                duis_promotoras,
            )

            try:
                new_id = _execute(sql, params, return_last_id=True)
                st.success(f"Grupo creado correctamente (Id_grupo={new_id}).")
            except Exception:
                st.error(
                    "No se pudo crear el grupo. "
                    "Verifica que no exista otro grupo con el mismo nombre y distrito."
                )


# -----------------------------
# Vista: Mis grupos
# -----------------------------
def _vista_mis_grupos(promotora):
    st.subheader("Mis grupos")

    grupos = _listar_grupos_de_promotora(promotora["Id_promotora"])
    if not grupos:
        st.info("Todavía no has creado grupos.")
        return

    st.write("**Listado de grupos**")
    st.dataframe(grupos, use_container_width=True, hide_index=True)

    st.markdown("### Eliminar grupo")

    mapa = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_eliminar_grupo"):
        if not mapa:
            st.info("No hay grupos para eliminar.")
            return

        etiqueta = st.selectbox("Seleccione el grupo a eliminar", list(mapa.keys()))
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este grupo (no se puede deshacer)."
        )
        enviar = st.form_submit_button("Eliminar grupo")

        if enviar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
                return

            id_grupo = mapa[etiqueta]
            try:
                _execute(
                    "DELETE FROM grupos WHERE Id_grupo = %s AND Id_promotora = %s",
                    (id_grupo, promotora["Id_promotora"]),
                )
                st.success("Grupo eliminado correctamente.")
            except Exception:
                st.error(
                    "No se pudo eliminar el grupo. "
                    "Verifica que no tenga información relacionada en otras tablas."
                )


# -----------------------------
# Helpers para Directiva
# -----------------------------
def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _obtener_id_rol_directiva():
    fila = _fetch_one(
        "SELECT Id_rol FROM rol WHERE `Tipo de rol` = %s", ("DIRECTIVA",)
    )
    if not fila:
        return None
    return fila["Id_rol"]


# -----------------------------
# Vista: Crear Directiva
# -----------------------------
def _vista_crear_directiva(promotora):
    st.subheader("Crear usuario de Directiva para un grupo")

    grupos = _listar_grupos_de_promotora(promotora["Id_promotora"])
    if not grupos:
        st.info("Primero debes crear al menos un grupo.")
        return

    opciones = {
        f"{g['Id_grupo']} - {g['Nombre']} ({g['Distrito']})": g["Id_grupo"]
        for g in grupos
    }

    with st.form("form_crear_directiva"):
        nombre = st.text_input("Nombre de la Directiva")
        dui = st.text_input("DUI de la Directiva (sin guiones)")
        contrasenia = st.text_input("Contraseña", type="password")
        etiqueta_grupo = st.selectbox(
            "Grupo al que se asignará la Directiva", list(opciones.keys())
        )

        enviar = st.form_submit_button("Crear usuario de Directiva")

        if enviar:
            if not (nombre.strip() and dui.strip() and contrasenia):
                st.warning("Todos los campos son obligatorios.")
                return

            # Validar DUI único en Usuario
            existente = _fetch_one(
                "SELECT Id_usuario FROM Usuario WHERE DUI = %s", (dui.strip(),)
            )
            if existente:
                st.error("Ya existe un usuario con ese DUI en el sistema.")
                return

            id_rol_dir = _obtener_id_rol_directiva()
            if not id_rol_dir:
                st.error(
                    "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                    "Primero crea ese rol."
                )
                return

            id_grupo = opciones[etiqueta_grupo]
            hoy = date.today()
            hash_pass = _hash_password(contrasenia)

            try:
                # 1) Crear usuario para login
                id_usuario = _execute(
                    """
                    INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre.strip(), dui.strip(), hash_pass, id_rol_dir),
                    return_last_id=True,
                )

                # 2) Registrar en tabla directiva
                _execute(
                    """
                    INSERT INTO directiva
                        (Nombre, DUI, Contraseña, Id_grupo, Activo, Creado_en)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (nombre.strip(), dui.strip(), hash_pass, id_grupo, "1", hoy),
                )

                st.success(
                    f"Usuario de Directiva creado correctamente (Id_usuario={id_usuario})."
                )
            except Exception:
                st.error("Ocurrió un error al crear la Directiva. Revisa los datos.")


# -----------------------------
# Panel principal de Promotora
# -----------------------------
def promotora_panel():
    # 1) Obtener usuario desde la sesión EXACTAMENTE como antes
    usuario = _obtener_usuario_de_sesion()

    # 2) Validar que el rol sea PROMOTORA
    _validar_promotora(usuario)

    # 3) Obtener/crear registro en tabla promotora
    promotora = _obtener_promotora_desde_usuario(usuario)

    # Sidebar de sesión
    st.sidebar.markdown("### Sesión")
    st.sidebar.write(f"Usuario: {usuario.get('Nombre')}")
    st.sidebar.write("Rol: PROMOTORA")

    st.title("Panel de Promotora")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"]
    )

    with tab1:
        _vista_crear_grupo(promotora, usuario)

    with tab2:
        _vista_mis_grupos(promotora)

    with tab3:
        _vista_crear_directiva(promotora)

    with tab4:
        st.info("Aquí más adelante puedes agregar reportes específicos para Promotora.")
