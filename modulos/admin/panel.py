import streamlit as st
from modulos.config.conexion import fetch_all, fetch_one, execute

def _crud_distritos():
    st.markdown("## Distritos")
    st.caption("Crear y listar distritos.")

    with st.form("form_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

        if enviar:
            nom = (nombre or "").strip()
            if not nom:
                st.warning("Nombre requerido.")
            else:
                # evita duplicados por nombre (insensible a mayúsculas)
                existe = fetch_one(
                    "SELECT id_distrito FROM distritos WHERE LOWER(Nombre)=LOWER(%s) LIMIT 1",
                    (nom,)
                )
                if existe:
                    st.error("Ya existe un distrito con ese nombre.")
                else:
                    # 👇 INSERT sin 'Creado_en'
                    sql = "INSERT INTO distritos (Nombre) VALUES (%s)"
                    _, last_id = execute(sql, (nom,))
                    st.success(f"Distrito creado (id={last_id}).")

    # 👇 SELECT sin 'Creado_en'
    distritos = fetch_all(
        "SELECT id_distrito, Nombre FROM distritos ORDER BY id_distrito DESC"
    )
    st.dataframe(distritos, use_container_width=True)
