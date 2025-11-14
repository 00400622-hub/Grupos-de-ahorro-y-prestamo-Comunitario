import streamlit as st
import mysql.connector
from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role

# ... aquí van _solo_admin(), _titulo(), etc. que ya tienes ...

def _crud_distritos():
    _titulo("Distritos")
    st.caption("Crear, listar y eliminar distritos.")

    # ---------- FORMULARIO PARA CREAR ----------
    with st.form("form_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Nombre requerido.")
            else:
                # evita duplicados por nombre
                existe = fetch_one(
                    "SELECT Id_distrito FROM distritos WHERE LOWER(Nombre)=LOWER(%s) LIMIT 1",
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

    # ---------- LISTADO DE DISTRITOS ----------
    distritos = fetch_all(
        "SELECT Id_distrito, Nombre FROM distritos ORDER BY Id_distrito ASC"
    )
    st.subheader("Lista de distritos")
    st.dataframe(distritos, use_container_width=True)

    # ---------- FORMULARIO PARA ELIMINAR ----------
    st.markdown("### Eliminar distrito")
    if not distritos:
        st.info("No hay distritos para eliminar.")
        return

    # opciones para seleccionar
    opciones = {
        f"{d['Id_distrito']} - {d['Nombre']}": d["Id_distrito"]
        for d in distritos
    }

    with st.form("form_eliminar_distrito"):
        sel = st.selectbox("Seleccione el distrito a eliminar", list(opciones.keys()))
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar distrito", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Marca la casilla de confirmación para eliminar.")
            else:
                id_sel = opciones[sel]
                try:
                    # intenta borrar
                    sql = "DELETE FROM distritos WHERE Id_distrito = %s"
                    filas, _ = execute(sql, (id_sel,))
                    if filas > 0:
                        st.success(f"Distrito {sel} eliminado correctamente.")
                        st.experimental_rerun()
                    else:
                        st.warning("No se encontró el distrito a eliminar.")
                except mysql.connector.IntegrityError as e:
                    # Esto pasa si hay grupos/usuarios que aún usan ese distrito
                    st.error(
                        "No se puede eliminar el distrito porque está siendo usado "
                        "por otros registros (grupos, usuarios, etc.). "
                        f"Detalle MySQL [{e.errno}]: {e.msg}"
                    )
                except Exception as e:
                    st.exception(e)
