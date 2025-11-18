# modulos/admin/panel.py
import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# =====================================================
#  CRUD DISTRITOS
# =====================================================
def _crud_distritos():
    st.subheader("Distritos")

    # -------- Listado de distritos --------
    try:
        distritos = fetch_all(
            """
            SELECT Id_distrito, Nombre, Estado, Creado_en
            FROM distritos
            ORDER BY Id_distrito ASC
            """
        )
    except Exception as e:
        st.error(f"Error al cargar distritos: {e}")
        return

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
            try:
                execute(
                    """
                    INSERT INTO distritos (Nombre, Estado, Creado_en)
                    VALUES (%s, %s, %s)
                    """,
                    (nombre.strip(), "ACTIVO", hoy),
                )
                st.success("Distrito creado correctamente.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al crear distrito: {e}")


# =====================================================
#  Sincronizar tabla PROMOTORA a partir de Usuario
# =====================================================
def _sync_promotora_from_usuario(uid: int):
    """
    Si el usuario tiene rol PROMOTORA, asegura que exista una fila en 'promotora'.
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


# =====================================================
#  CRUD USUARIOS  (incluye creación de promotoras)
# =====================================================
def _crud_usuarios():
    st.subheader("Usuarios y promotoras")

    # -------- Listado de usuarios --------
    try:
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
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return

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
    if roles:
        mapa_roles = {r["Tipo de rol"]: r["Id_rol"] for r in roles}
        rol_nombre = st.selectbox("Rol", list(mapa_roles.keys()))
    else:
        mapa_roles = {}
        rol_nombre = None
        st.warning("No existen roles en la tabla 'rol'. Cree al menos uno en la BD.")

    if st.button("Crear usuario"):
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe seleccionar un rol.")
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
                # Si el rol es PROMOTORA, sincronizar en tabla promotora
                _sync_promotora_from_usuario(uid)

                st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al crear usuario: {e}")

    st.write("---")
    st.write("### Eliminar usuario")

    if usuarios:
        opciones = {
            f'{u["Id_usuario"]} - {u["Nombre"]} ({u["DUI"]})': u["Id_usuario"]
            for u in usuarios
        }
        label_sel = st.selectbox(
            "Seleccione el usuario a eliminar",
            list(opciones.keys()),
        )
        uid_sel = opciones[label_sel]

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
        )

        if st.button("Eliminar usuario"):
            if not confirmar:
                st.warning("Debe marcar la casilla de confirmación.")
            else:
                try:
                    execute(
                        "DELETE FROM Usuario WHERE Id_usuario = %s",
                        (uid_sel,),
                    )
                    st.success("Usuario eliminado.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al eliminar usuario: {e}")
    else:
        st.info("No hay usuarios para eliminar.")


# =====================================================
#  Reportes de todos los grupos
# =====================================================
def _reportes_grupos():
    st.subheader("Reportes de todos los grupos")

    try:
        grupos = fetch_all(
            """
            SELECT g.Id_grupo,
                   g.Nombre AS Grupo,
                   d.Nombre AS Distrito,
                   g.Estado,
                   g.Creado_en,
                   g.Id_promotora,
                   g.DUIs_promotoras
            FROM grupos g
            JOIN distritos d ON d.Id_distrito = g.Id_distrito
            ORDER BY d.Nombre, g.Nombre
            """
        )
    except Exception as e:
        st.error(f"Error al cargar grupos: {e}")
        return

    if not grupos:
        st.info("No hay grupos registrados.")
        return

    st.write("### Listado de grupos")
    st.dataframe(grupos, use_container_width=True)

    # Descarga CSV
    import pandas as pd
    import io

    df = pd.DataFrame(grupos)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Descargar reporte de grupos (CSV)",
        data=csv_buffer.getvalue(),
        file_name="reporte_grupos.csv",
        mime="text/csv",
    )


# =====================================================
#  PANEL ADMINISTRADOR
# =====================================================
@require_auth()
@has_role("ADMINISTRADOR")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    tab1, tab2, tab3 = st.tabs(
        ["Distritos", "Usuarios / Promotoras", "Reportes de grupos"]
    )

    with tab1:
        _crud_distritos()

    with tab2:
        _crud_usuarios()

    with tab3:
        _reportes_grupos()
# modulos/admin/panel.py
import datetime as dt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# =====================================================
#  CRUD DISTRITOS
# =====================================================
def _crud_distritos():
    st.subheader("Distritos")

    # -------- Listado de distritos --------
    try:
        distritos = fetch_all(
            """
            SELECT Id_distrito, Nombre, Estado, Creado_en
            FROM distritos
            ORDER BY Id_distrito ASC
            """
        )
    except Exception as e:
        st.error(f"Error al cargar distritos: {e}")
        return

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
            try:
                execute(
                    """
                    INSERT INTO distritos (Nombre, Estado, Creado_en)
                    VALUES (%s, %s, %s)
                    """,
                    (nombre.strip(), "ACTIVO", hoy),
                )
                st.success("Distrito creado correctamente.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al crear distrito: {e}")


# =====================================================
#  Sincronizar tabla PROMOTORA a partir de Usuario
# =====================================================
def _sync_promotora_from_usuario(uid: int):
    """
    Si el usuario tiene rol PROMOTORA, asegura que exista una fila en 'promotora'.
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


# =====================================================
#  CRUD USUARIOS  (incluye creación de promotoras)
# =====================================================
def _crud_usuarios():
    st.subheader("Usuarios y promotoras")

    # -------- Listado de usuarios --------
    try:
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
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return

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
    if roles:
        mapa_roles = {r["Tipo de rol"]: r["Id_rol"] for r in roles}
        rol_nombre = st.selectbox("Rol", list(mapa_roles.keys()))
    else:
        mapa_roles = {}
        rol_nombre = None
        st.warning("No existen roles en la tabla 'rol'. Cree al menos uno en la BD.")

    if st.button("Crear usuario"):
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe seleccionar un rol.")
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
                # Si el rol es PROMOTORA, sincronizar en tabla promotora
                _sync_promotora_from_usuario(uid)

                st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al crear usuario: {e}")

    st.write("---")
    st.write("### Eliminar usuario")

    if usuarios:
        opciones = {
            f'{u["Id_usuario"]} - {u["Nombre"]} ({u["DUI"]})': u["Id_usuario"]
            for u in usuarios
        }
        label_sel = st.selectbox(
            "Seleccione el usuario a eliminar",
            list(opciones.keys()),
        )
        uid_sel = opciones[label_sel]

        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
        )

        if st.button("Eliminar usuario"):
            if not confirmar:
                st.warning("Debe marcar la casilla de confirmación.")
            else:
                try:
                    execute(
                        "DELETE FROM Usuario WHERE Id_usuario = %s",
                        (uid_sel,),
                    )
                    st.success("Usuario eliminado.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al eliminar usuario: {e}")
    else:
        st.info("No hay usuarios para eliminar.")


# =====================================================
#  Reportes de todos los grupos
# =====================================================
def _reportes_grupos():
    st.subheader("Reportes de todos los grupos")

    try:
        grupos = fetch_all(
            """
            SELECT g.Id_grupo,
                   g.Nombre AS Grupo,
                   d.Nombre AS Distrito,
                   g.Estado,
                   g.Creado_en,
                   g.Id_promotora,
                   g.DUIs_promotoras
            FROM grupos g
            JOIN distritos d ON d.Id_distrito = g.Id_distrito
            ORDER BY d.Nombre, g.Nombre
            """
        )
    except Exception as e:
        st.error(f"Error al cargar grupos: {e}")
        return

    if not grupos:
        st.info("No hay grupos registrados.")
        return

    st.write("### Listado de grupos")
    st.dataframe(grupos, use_container_width=True)

    # Descarga CSV
    import pandas as pd
    import io

    df = pd.DataFrame(grupos)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Descargar reporte de grupos (CSV)",
        data=csv_buffer.getvalue(),
        file_name="reporte_grupos.csv",
        mime="text/csv",
    )


# =====================================================
#  PANEL ADMINISTRADOR
# =====================================================
@require_auth()
@has_role("ADMINISTRADOR")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    tab1, tab2, tab3 = st.tabs(
        ["Distritos", "Usuarios / Promotoras", "Reportes de grupos"]
    )

    with tab1:
        _crud_distritos()

    with tab2:
        _crud_usuarios()

    with tab3:
        _reportes_grupos()
