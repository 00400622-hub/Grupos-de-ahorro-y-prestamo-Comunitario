# modulos/admin/panel.py
import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, require_user_role


# ==========================
# CRUD DISTRITOS
# ==========================

def _crud_distritos():
    st.subheader("Distritos")

    # Listado
    distritos = fetch_all(
        """
        SELECT Id_distrito, Nombre, Estado, Creado_en
        FROM distritos
        ORDER BY Id_distrito ASC
        """
    )

    st.write("### Lista de distritos")
    if distritos:
        st.table(distritos)
    else:
        st.info("No hay distritos registrados.")

    st.write("---")
    st.write("### Crear nuevo distrito")

    nombre = st.text_input("Nombre del distrito")

    if st.button("Crear distrito"):
        if not nombre.strip():
            st.warning("Ingrese un nombre válido.")
        else:
            hoy = dt.date.today()
            execute(
                "INSERT INTO distritos (Nombre, Estado, Creado_en) VALUES (%s, %s, %s)",
                (nombre.strip(), "ACTIVO", hoy),
            )
            st.success("Distrito creado correctamente.")
            st.rerun()


# ==========================
# Sincronizar promotora con usuario
# ==========================

def _sync_promotora_from_usuario(uid: int) -> None:
    """
    Si el usuario tiene rol PROMOTORA, asegura que exista fila en 'promotora'.
    """
    usuario = fetch_one(
        """
        SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol` AS RolNombre
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
        return

    # ¿Ya existe esa promotora?
    existe = fetch_one(
        "SELECT Id_promotora FROM promotora WHERE DUI = %s LIMIT 1",
        (usuario["DUI"],),
    )
    if existe:
        return

    # Crear registro en tabla promotora
    execute(
        "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
        (usuario["Nombre"], usuario["DUI"]),
    )


# ==========================
# CRUD USUARIOS
# ==========================

def _crud_usuarios():
    st.subheader("Usuarios")

    usuarios = fetch_all(
        """
        SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol` AS Rol, u.Id_rol
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

    st.write("---")
    st.write("### Crear usuario")

    nombre = st.text_input("Nombre completo")
    dui = st.text_input("DUI")
    contr = st.text_input("Contraseña", type="password")

    # Cargar roles existentes
    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY Id_rol")
    mapa_roles = {r["Tipo de rol"]: r["Id_rol"] for r in roles}
    rol_nombre = st.selectbox("Rol", list(mapa_roles.keys())) if roles else None

    if st.button("Crear usuario"):
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe existir al menos un rol en la tabla 'rol'.")
        else:
            id_rol = mapa_roles[rol_nombre]
            uid = execute(
                """
                INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre.strip(), dui.strip(), contr.strip(), id_rol),
                return_last_id=True,
            )
            # Si es promotora, sincronizar en tabla promotora
            _sync_promotora_from_usuario(uid)
            st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
            st.rerun()

    st.write("---")
    st.write("### Eliminar usuario")

    if usuarios:
        opciones = {
            f'{u["Id_usuario"]} - {u["Nombre"]} ({u["DUI"]})': u["Id_usuario"]
            for u in usuarios
        }
        label_sel = st.selectbox(
            "Seleccione el usuario a eliminar", list(opciones.keys())
        )
        uid_sel = opciones[label_sel]

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
        )
        if st.button("Eliminar usuario"):
            if confirmar:
                execute("DELETE FROM Usuario WHERE Id_usuario = %s", (uid_sel,))
                st.success("Usuario eliminado.")
                st.rerun()
            else:
                st.warning("Debe marcar la casilla de confirmación.")
    else:
        st.info("No hay usuarios para eliminar.")


# ==========================
# PANEL ADMINISTRADOR
# ==========================

@require_auth
@require_user_role("ADMINISTRADOR")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    tabs = st.tabs(["Distritos", "Usuarios"])

    with tabs[0]:
        _crud_distritos()

    with tabs[1]:
        _crud_usuarios()
