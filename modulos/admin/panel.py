import streamlit as st
import mysql.connector

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# ----------------- helpers básicos ----------------- #

def _solo_admin():
    """Solo permite acceder a usuarios con rol ADMINISTRADOR."""
    require_auth()
    if not has_role("ADMINISTRADOR"):
        st.error("Acceso restringido al Administrador.")
        st.stop()


def _titulo(txt: str):
    st.markdown(f"## {txt}")


# ----------------- CRUD de Distritos ----------------- #

def _crud_distritos():
    _titulo("Distritos")
    st.caption("Crear, listar y eliminar distritos.")

    # -------- formulario para crear -------- #
    with st.form("form_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Nombre requerido.")
            else:
                # evitar nombres duplicados
                existe = fetch_one(
                    "SELECT Id_distrito FROM distritos "
                    "WHERE LOWER(Nombre) = LOWER(%s) LIMIT 1",
                    (nom,)
                )
                if existe:
                    st.error("Ya existe un distrito con ese nombre.")
                else:
                    try:
                        sql = "INSERT INTO distritos (Nombre) VALUES (%s)"
                        _, last_id = execute(sql, (nom,))
                        st.success(f"Distrito creado (Id_distrito={last_id}).")
                    except mysql.connector.IntegrityError as e:
                        st.error(f"Error de integridad MySQL [{e.errno}]: {e.msg}")
                    except Exception as e:
                        st.exception(e)

    st.markdown("---")

    # -------- listado de distritos -------- #
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Id_distrito ASC"
    )
    st.subheader("Lista de distritos")
    if distritos:
        st.dataframe(distritos, use_container_width=True)
    else:
        st.info("No hay distritos registrados aún.")

    st.markdown("### Eliminar distrito")

    if not distritos:
        st.info("No hay distritos para eliminar.")
        return

    # mapear opciones para el select
    opciones = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }

    with st.form("form_eliminar_distrito"):
        sel = st.selectbox(
            "Seleccione el distrito a eliminar",
            list(opciones.keys())
        )
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar distrito", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                id_sel = opciones[sel]
                try:
                    sql = "DELETE FROM distritos WHERE Id_distrito = %s"
                    filas, _ = execute(sql, (id_sel,))
                    if filas > 0:
                        st.success(f"Distrito {sel} eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("No se encontró el distrito seleccionado.")
                except mysql.connector.IntegrityError as e:
                    st.error(
                        "No se puede eliminar el distrito porque está siendo "
                        "utilizado por otros registros (por ejemplo, grupos o usuarios). "
                        f"Detalle MySQL [{e.errno}]: {e.msg}"
                    )
                except Exception as e:
                    st.exception(e)


# ----------------- CRUD Usuarios / Roles ----------------- #

def _crud_usuarios():
    _titulo("Usuarios")
    st.caption("Crear usuarios seleccionando el rol desde la tabla 'rol'.")

    # cargar roles desde tabla rol
    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY `Tipo de rol`")
    opciones = {r["Tipo de rol"]: r["Id_rol"] for r in roles}

    with st.form("form_usuario", clear_on_submit=True):
        nombre = st.text_input("Nombre del usuario")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña (por ahora sin cifrar)")
        rol_sel = st.selectbox(
            "Tipo de rol",
            list(opciones.keys())
        ) if opciones else None
        enviar = st.form_submit_button("Crear usuario")

        if enviar:
            if not (nombre and dui and contr and rol_sel):
                st.warning("Complete todos los campos.")
            else:
                id_rol = opciones[rol_sel]
                # evitar DUI duplicado
                existe = fetch_one(
                    "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
                    (dui,)
                )
                if existe:
                    st.error("Ya existe un usuario con ese DUI.")
                else:
                    sql = """
                        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                        VALUES (%s, %s, %s, %s)
                    """
                    _, uid = execute(sql, (nombre, dui, contr, id_rol))
                    st.success(f"Usuario creado con Id_usuario={uid} y rol={rol_sel}.")

    # listado de usuarios
    usuarios = fetch_all("""
        SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol` AS Rol
        FROM Usuario u
        LEFT JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
    """)
    st.subheader("Lista de usuarios")
    st.dataframe(usuarios, use_container_width=True)


# ----------------- Reportes globales (placeholder) ----------------- #

def _reportes_globales():
    _titulo("Reportes globales")
    st.info("Aquí más adelante podrás agregar reportes globales del sistema.")


# ----------------- Punto de entrada del panel ADMIN ----------------- #

def admin_panel():
    """Función principal del panel de administrador."""
    _solo_admin()
    tab1, tab2, tab3 = st.tabs(["Distritos", "Usuarios", "Reportes globales"])
    with tab1:
        _crud_distritos()
    with tab2:
        _crud_usuarios()
    with tab3:
        _reportes_globales()
