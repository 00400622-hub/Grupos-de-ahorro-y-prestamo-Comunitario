# modulos/admin/panel.py
import streamlit as st
from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# ==========================
# CRUD DISTRITOS
# ==========================

def _crud_distritos():
    st.subheader("Distritos")

    # Listado de distritos
    distritos = fetch_all("""
        SELECT Id_distrito, Nombre
        FROM distritos
        ORDER BY Id_distrito ASC
    """)

    st.write("### Lista de distritos")
    if distritos:
        st.table(distritos)
    else:
        st.info("No hay distritos registrados.")

    st.write("---")
    st.write("### Crear nuevo distrito")
    nuevo_nombre = st.text_input("Nombre del distrito")

    if st.button("Crear distrito"):
        if not nuevo_nombre.strip():
            st.warning("Ingrese un nombre válido.")
        else:
            execute(
                "INSERT INTO distritos (Nombre) VALUES (%s)",
                (nuevo_nombre.strip(),),
            )
            st.success("Distrito creado correctamente.")
            st.rerun()

    st.write("---")
    st.write("### Eliminar distrito")

    if distritos:
        opciones = {
            f'{d["Id_distrito"]} - {d["Nombre"]}': d["Id_distrito"]
            for d in distritos
        }
        etiqueta = st.selectbox(
            "Seleccione el distrito a eliminar",
            list(opciones.keys())
        )
        id_sel = opciones[etiqueta]
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
        )

        if st.button("Eliminar distrito"):
            if confirmar:
                execute(
                    "DELETE FROM distritos WHERE Id_distrito = %s",
                    (id_sel,)
                )
                st.success("Distrito eliminado correctamente.")
                st.rerun()
            else:
                st.warning("Debe marcar la casilla de confirmación.")
    else:
        st.info("No hay distritos para eliminar.")


# ==========================
# CRUD USUARIOS
# ==========================

def _crud_usuarios():
    st.subheader("Usuarios")

    # Listado de usuarios
    usuarios = fetch_all("""
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               r.`Tipo de rol` AS Rol,
               u.Id_rol
        FROM Usuario u
        JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
    """)

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
    roles = fetch_all("""
        SELECT Id_rol, `Tipo de rol` AS RolNombre
        FROM rol
        ORDER BY Id_rol
    """)
    mapa_roles = {r["RolNombre"]: r["Id_rol"] for r in roles}
    rol_nombre = st.selectbox("Rol", list(mapa_roles.keys())) if roles else None

    if st.button("Crear usuario"):
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe existir al menos un rol en la tabla 'rol'.")
        else:
            id_rol = mapa_roles[rol_nombre]

            # Insertamos el usuario
            uid = execute(
                """
                INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre.strip(), dui.strip(), contr.strip(), id_rol),
                return_last_id=True,
            )

            # Si el rol es PROMOTORA, aseguramos fila en 'promotora'
            if rol_nombre.upper().strip() == "PROMOTORA":
                existe_prom = fetch_one(
                    "SELECT Id_promotora FROM promotora WHERE DUI = %s LIMIT 1",
                    (dui.strip(),),
                )
                if not existe_prom:
                    execute(
                        "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
                        (nombre.strip(), dui.strip()),
                    )

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
            "Seleccione el usuario a eliminar",
            list(opciones.keys())
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

@require_auth   # <--- sin paréntesis, ahora es seguro
@has_role("ADMINISTRADOR", "ADMINISTRADOR GENERAL")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    pestañas = st.tabs(["Distritos", "Usuarios"])

    with pestañas[0]:
        _crud_distritos()

    with pestañas[1]:
        _crud_usuarios()
