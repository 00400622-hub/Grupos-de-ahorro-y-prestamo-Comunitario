import streamlit as st
from datetime import date

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_admin


# ---------- helpers generales ---------- #

def _titulo(txt: str):
    st.markdown(f"## {txt}")


def _sync_promotora_from_usuario(id_usuario: int):
    """
    Sincroniza la tabla 'promotora' a partir de un registro de 'Usuario'.

    - Si el usuario tiene rol PROMOTORA y tiene DUI:
        -> Inserta o actualiza en 'promotora' (Nombre, DUI).
    - Si NO es rol PROMOTORA:
        -> Borra cualquier promotora con ese DUI (si existe).
    """
    usuario = fetch_one(
        "SELECT Id_usuario, Nombre, DUI, Id_rol FROM Usuario WHERE Id_usuario = %s",
        (id_usuario,),
    )
    if not usuario:
        return

    dui = (usuario.get("DUI") or "").strip()
    if not dui:
        # Sin DUI, no hay nada que sincronizar
        return

    # Ver el tipo de rol
    rol = fetch_one(
        "SELECT `Tipo de rol` FROM rol WHERE Id_rol = %s",
        (usuario["Id_rol"],),
    )
    tipo = (rol["Tipo de rol"] or "").upper().strip() if rol else ""

    if tipo != "PROMOTORA":
        # Si ya no es promotora, borramos cualquier registro que use ese DUI
        execute("DELETE FROM promotora WHERE DUI = %s", (dui,))
        return

    # Es PROMOTORA: insertamos o actualizamos en 'promotora'
    existente = fetch_one(
        "SELECT Id_promotora FROM promotora WHERE DUI = %s",
        (dui,),
    )

    if existente:
        execute(
            "UPDATE promotora SET Nombre = %s WHERE Id_promotora = %s",
            (usuario["Nombre"], existente["Id_promotora"]),
        )
    else:
        execute(
            "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
            (usuario["Nombre"], dui),
        )


# ---------- CRUD de distritos ---------- #

def _crud_distritos():
    _titulo("Distritos")

    st.subheader("Crear nuevo distrito")

    with st.form("form_crear_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        crear = st.form_submit_button("Crear distrito")

        if crear:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Debes ingresar el nombre del distrito.")
                return

            # evitar duplicados
            existe = fetch_one(
                "SELECT Id_distrito FROM distritos WHERE LOWER(Nombre) = LOWER(%s)",
                (nom,),
            )
            if existe:
                st.error("Ya existe un distrito con ese nombre.")
                return

            # Para evitar problemas con columnas opcionales, solo insertamos Nombre
            sql = "INSERT INTO distritos (Nombre) VALUES (%s)"
            _, did = execute(sql, (nom,))
            st.success(f"Distrito creado correctamente (Id_distrito={did}).")

    st.subheader("Distritos existentes")

    # AQUÍ quitamos Creado_en del SELECT para evitar el ProgrammingError
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Id_distrito ASC"
    )

    if distritos:
        st.dataframe(distritos, use_container_width=True)
    else:
        st.info("Todavía no hay distritos registrados.")

    st.markdown("### Eliminar distrito")

    if not distritos:
        st.caption("No hay distritos para eliminar.")
        return

    opciones = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"] for d in distritos
    }

    with st.form("form_eliminar_distrito"):
        sel = st.selectbox("Distrito a eliminar", list(opciones.keys()))
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar distrito", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
                return

            id_sel = opciones[sel]
            try:
                filas, _ = execute(
                    "DELETE FROM distritos WHERE Id_distrito = %s", (id_sel,)
                )
                if filas > 0:
                    st.success("Distrito eliminado correctamente.")
                    st.rerun()
                else:
                    st.warning("No se encontró el distrito seleccionado.")
            except Exception as e:
                st.error(
                    "No se puede eliminar el distrito porque está "
                    "siendo usado por otros registros."
                )
                st.exception(e)


# ---------- CRUD de usuarios (Admin, Promotora, Directiva, etc.) ---------- #

def _crud_usuarios():
    _titulo("Usuarios (incluye promotoras)")

    # --- cargar roles ---
    roles = fetch_all(
        "SELECT Id_rol, `Tipo de rol` AS Tipo FROM rol ORDER BY Id_rol ASC"
    )
    if not roles:
        st.error(
            "No hay roles definidos en la tabla 'rol'. "
            "Debes crear al menos ADMINISTRADOR, PROMOTORA, DIRECTIVA."
        )
        return

    rol_opciones = {
        f"{r['Id_rol']} - {r['Tipo']}": r["Id_rol"] for r in roles
    }

    # --- listar usuarios ---
    st.subheader("Usuarios registrados")

    usuarios = fetch_all(
        """
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               u.Contraseña,
               u.Id_rol,
               r.`Tipo de rol` AS Rol
        FROM Usuario u
        LEFT JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
        """
    )

    if usuarios:
        st.dataframe(usuarios, use_container_width=True)
    else:
        st.info("Todavía no hay usuarios registrados.")

    # ---------- crear usuario ---------- #

    st.markdown("---")
    st.subheader("Crear nuevo usuario")

    with st.form("form_crear_usuario", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        dui = st.text_input("DUI (con o sin guion)")
        contr = st.text_input("Contraseña", type="password")
        sel_rol = st.selectbox(
            "Rol",
            list(rol_opciones.keys()),
        )
        crear = st.form_submit_button("Crear usuario")

        if crear:
            nom = (nombre or "").strip()
            d = (dui or "").strip()
            pwd = (contr or "").strip()
            id_rol = rol_opciones[sel_rol]

            if not nom or not d or not pwd:
                st.warning("Nombre, DUI y Contraseña son obligatorios.")
                return

            # evitar duplicado por DUI
            existe = fetch_one(
                "SELECT Id_usuario FROM Usuario WHERE DUI = %s",
                (d,),
            )
            if existe:
                st.error("Ya existe un usuario con ese DUI.")
                return

            sql = """
                INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                VALUES (%s, %s, %s, %s)
            """
            _, uid = execute(sql, (nom, d, pwd, id_rol))

            # Sincronizar tabla promotora si el rol es PROMOTORA
            _sync_promotora_from_usuario(uid)

            st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
            st.rerun()

    # ---------- eliminar usuario ---------- #

    st.markdown("---")
    st.subheader("Eliminar usuario")

    if not usuarios:
        st.caption("No hay usuarios para eliminar.")
        return

    opciones_usr = {
        f"{u['Id_usuario']} - {u['Nombre']} ({u['DUI']})": u for u in usuarios
    }

    with st.form("form_eliminar_usuario"):
        sel_usr = st.selectbox(
            "Seleccione el usuario a eliminar",
            list(opciones_usr.keys())
        )
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar usuario", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
                return

            u_sel = opciones_usr[sel_usr]
            id_u = u_sel["Id_usuario"]
            dui_u = (u_sel["DUI"] or "").strip()

            try:
                # Borramos primero en Usuario
                filas, _ = execute(
                    "DELETE FROM Usuario WHERE Id_usuario = %s",
                    (id_u,),
                )

                # Y si tenía promotora, la borramos también
                if dui_u:
                    execute(
                        "DELETE FROM promotora WHERE DUI = %s",
                        (dui_u,),
                    )

                if filas > 0:
                    st.success("Usuario eliminado correctamente.")
                    st.rerun()
                else:
                    st.warning("No se encontró el usuario seleccionado.")
            except Exception as e:
                st.error(
                    "No se puede eliminar el usuario porque está asociado "
                    "a otros registros."
                )
                st.exception(e)


# ---------- panel principal de ADMIN ---------- #

def admin_panel():
    require_auth()
    if not has_role("ADMINISTRADOR"):
        st.error("Acceso restringido al rol ADMINISTRADOR.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(
        ["Distritos", "Usuarios / Promotoras", "Reportes globales"]
    )

    with tab1:
        _crud_distritos()
    with tab2:
        _crud_usuarios()
    with tab3:
        _titulo("Reportes globales")
        st.info("Aquí luego puedes agregar reportes consolidados para el administrador.")
