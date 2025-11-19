# modulos/admin/panel.py

import streamlit as st
from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# ==========================
#  CRUD DISTRITOS
# ==========================

def _crud_distritos():
    st.subheader("Distritos")

    # ------- Listado -------
    try:
        distritos = fetch_all(
            """
            SELECT Id_distrito, Nombre
            FROM distritos
            ORDER BY Id_distrito ASC
            """
        )
    except Exception as e:
        st.error(
            "Error al consultar la tabla 'distritos'. "
            "Revisa nombres de tabla/columnas en phpMyAdmin."
        )
        st.code(str(e))
        return

    st.write("### Lista de distritos")
    if distritos:
        st.table(distritos)
    else:
        st.info("No hay distritos registrados.")

    # ------- Crear distrito -------
    st.write("---")
    st.write("### Crear nuevo distrito")

    with st.form("form_crear_distrito"):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

    if enviar:
        if not nombre.strip():
            st.warning("Ingrese un nombre válido.")
        else:
            try:
                execute(
                    "INSERT INTO distritos (Nombre) VALUES (%s)",
                    (nombre.strip(),),
                )
                st.success("Distrito creado correctamente.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo crear el distrito.")
                st.code(str(e))

    # ------- Eliminar distrito -------
    st.write("---")
    st.write("### Eliminar distrito")

    if not distritos:
        st.info("No hay distritos para eliminar.")
        return

    opciones = {
        f'{d["Id_distrito"]} - {d["Nombre"]}': d["Id_distrito"]
        for d in distritos
    }

    etiqueta = st.selectbox(
        "Seleccione el distrito a eliminar", list(opciones.keys())
    )
    id_sel = opciones[etiqueta]
    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
    )

    if st.button("Eliminar distrito"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            try:
                execute("DELETE FROM distritos WHERE Id_distrito = %s", (id_sel,))
                st.success("Distrito eliminado correctamente.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo eliminar el distrito.")
                st.code(str(e))


# ==========================
#  Sincronizar promotora con usuario
# ==========================

def _sync_promotora_from_usuario(uid: int):
    """
    Si el usuario tiene rol PROMOTORA, asegura que exista la fila
    correspondiente en la tabla 'promotora'.
    """
    usuario = fetch_one(
        """
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               r.`Tipo de rol` AS RolNombre
        FROM Usuario u
        JOIN rol r ON r.Id_rol = u.Id_rol
        WHERE u.Id_usuario = %s
        """,
        (uid,),
    )

    if not usuario:
        return

    rol = (usuario["RolNombre"] or "").upper().strip()
    if rol != "PROMOTORA":
        # Solo sincronizamos si el rol es PROMOTORA
        return

    # ¿Ya existe en promotora?
    existe = fetch_one(
        "SELECT Id_promotora FROM promotora WHERE DUI = %s LIMIT 1",
        (usuario["DUI"],),
    )
    if existe:
        return

    # Crear registro en promotora
    execute(
        "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
        (usuario["Nombre"], usuario["DUI"]),
    )


# ==========================
#  CRUD USUARIOS
# ==========================

def _crud_usuarios():
    st.subheader("Usuarios")

    # ------- Listado -------
    usuarios = fetch_all(
        """
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               r.`Tipo de rol` AS Rol,
               u.Id_rol
        FROM Usuario u
        JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
        """
    )

    st.write("### Lista de usuarios")
    if usuarios:
        st.table(usuarios)
    else:
        st.info("No hay usuarios registrados.")

    # ------- Crear usuario -------
    st.write("---")
    st.write("### Crear usuario")

    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY Id_rol")
    mapa_roles = {r["`Tipo de rol`"] if "`Tipo de rol`" in r else r["Tipo de rol"]: r["Id_rol"] for r in roles} if roles else {}

    # Normalizamos claves del diccionario para evitar problema del nombre del campo
    if roles:
        mapa_roles = {}
        for r in roles:
            # el alias puede venir como 'Tipo de rol' o '`Tipo de rol`' según fetch_all
            tipo = r.get("Tipo de rol", r.get("`Tipo de rol`"))
            mapa_roles[tipo] = r["Id_rol"]

    with st.form("form_crear_usuario"):
        nombre = st.text_input("Nombre completo")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña", type="password")
        rol_nombre = (
            st.selectbox("Rol", list(mapa_roles.keys()))
            if mapa_roles
            else None
        )
        enviar = st.form_submit_button("Crear usuario")

    if enviar:
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe existir al menos un rol en la tabla 'rol'.")
        else:
            id_rol = mapa_roles[rol_nombre]
            try:
                uid = execute(
                    """
                    INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre.strip(), dui.strip(), contr.strip(), id_rol),
                    return_last_id=True,
                )

                # Si el usuario es PROMOTORA, lo sincronizamos en la tabla promotora
                _sync_promotora_from_usuario(uid)

                st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
                st.rerun()
            except Exception as e:
                st.error("No se pudo crear el usuario.")
                st.code(str(e))

    # ------- Eliminar usuario -------
    st.write("---")
    st.write("### Eliminar usuario")

    if not usuarios:
        st.info("No hay usuarios para eliminar.")
        return

    opciones = {
        f'{u["Id_usuario"]} - {u["Nombre"]} ({u["DUI"]})': u["Id_usuario"]
        for u in usuarios
    }
    etiqueta = st.selectbox(
        "Seleccione el usuario a eliminar", list(opciones.keys())
    )
    uid_sel = opciones[etiqueta]
    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
    )

    if st.button("Eliminar usuario"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            try:
                execute("DELETE FROM Usuario WHERE Id_usuario = %s", (uid_sel,))
                st.success("Usuario eliminado.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo eliminar el usuario.")
                st.code(str(e))


# ==========================
#  PANEL ADMINISTRADOR
# ==========================

@require_auth()
@has_role("ADMINISTRADOR")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    pestañas = st.tabs(["Distritos", "Usuarios"])

    with pestañas[0]:
        _crud_distritos()

    with pestañas[1]:
        _crud_usuarios()
