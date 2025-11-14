import streamlit as st
from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role

def _solo_admin():
    require_auth()
    if not has_role("ADMINISTRADOR"):
        st.error("Acceso restringido al Administrador.")
        st.stop()

def _titulo(txt):
    st.markdown(f"## {txt}")

# -------- Distritos (si sigues usando la tabla 'distritos') ----------
def _crud_distritos():
    _titulo("Distritos")
    st.caption("Crear y listar distritos.")

    with st.form("form_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Nombre requerido.")
            else:
                existe = fetch_one(
                    "SELECT id_distrito FROM distritos WHERE LOWER(Nombre)=LOWER(%s) LIMIT 1",
                    (nom,)
                )
                if existe:
                    st.error("Ya existe un distrito con ese nombre.")
                else:
                    sql = "INSERT INTO distritos (Nombre) VALUES (%s)"
                    _, last_id = execute(sql, (nom,))
                    st.success(f"Distrito creado (id={last_id}).")

    distritos = fetch_all("SELECT id_distrito, Nombre FROM distritos ORDER BY id_distrito DESC")
    st.dataframe(distritos, use_container_width=True)

# -------- Usuarios / Roles ----------
def _crud_usuarios():
    _titulo("Usuarios")
    st.caption("Crear usuarios seleccionando el rol desde la tabla 'rol'.")

    # Cargar roles desde tabla rol
    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY `Tipo de rol`")
    opciones = {r["Tipo de rol"]: r["Id_rol"] for r in roles}

    with st.form("form_usuario", clear_on_submit=True):
        nombre = st.text_input("Nombre del usuario")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña (sin cifrar por ahora)")
        rol_sel = st.selectbox("Tipo de rol", list(opciones.keys())) if opciones else None
        enviar = st.form_submit_button("Crear usuario")

        if enviar:
            if not (nombre and dui and contr and rol_sel):
                st.warning("Complete todos los campos.")
            else:
                id_rol = opciones[rol_sel]
                # evitar DUI duplicado
                existe = fetch_one("SELECT Id_usuario FROM Usuario WHERE DUI=%s LIMIT 1", (dui,))
                if existe:
                    st.error("Ya existe un usuario con ese DUI.")
                else:
                    sql = """
                        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                        VALUES (%s, %s, %s, %s)
                    """
                    _, uid = execute(sql, (nombre, dui, contr, id_rol))
                    st.success(f"Usuario creado con id={uid} y rol={rol_sel}.")

    # Listado de usuarios con su rol
    usuarios = fetch_all("""
        SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol` AS Rol
        FROM Usuario u
        LEFT JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario DESC
    """)
    st.dataframe(usuarios, use_container_width=True)

def _reportes_globales():
    _titulo("Reportes globales")
    st.info("Aquí más adelante puedes agregar reportes globales del sistema.")

def admin_panel():
    _solo_admin()
    tabs = st.tabs(["Distritos", "Usuarios", "Reportes globales"])
    with tabs[0]:
        _crud_distritos()
    with tabs[1]:
        _crud_usuarios()
    with tabs[2]:
        _reportes_globales()
