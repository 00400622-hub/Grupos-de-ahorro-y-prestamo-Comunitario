import streamlit as st
from datetime import date
from modulos.auth.rbac import require_auth, has_role, current_user
from modulos.config.conexion import fetch_all, fetch_one, execute

def _validar_rol_promotora():
    require_auth()
    if not has_role("PROMOTORA"):
        st.error("Acceso restringido a Promotora.")
        st.stop()

def _crear_grupo(id_distrito):
    st.subheader("Crear grupo en mi distrito")
    with st.form("form_grupo", clear_on_submit=True):
        nombre = st.text_input("Nombre del grupo")
        estado = st.selectbox("Estado", ["ACTIVO", "INACTIVO"], index=0)
        enviar = st.form_submit_button("Crear grupo")
        if enviar:
            if not nombre.strip():
                st.warning("Nombre requerido.")
            else:
                sql = """
                    INSERT INTO grupos (Nombre, id_distrito, Estado, Creado_por, Creado_en)
                    VALUES (%s, %s, %s, %s, %s)
                """
                _, gid = execute(sql, (nombre.strip(), id_distrito, estado, current_user()["id_usuarios"], date.today()))
                st.success(f"Grupo creado (id={gid}).")

def _listado_grupos(id_distrito):
    st.subheader("Mis grupos por distrito")
    grupos = fetch_all("""
        SELECT g.id_grupo, g.Nombre, g.Estado, g.Creado_en,
               (SELECT COUNT(1) FROM usuarios u WHERE u.Rol='DIRECTIVA' AND u.id_grupo=g.id_grupo) AS TieneDirectiva
        FROM grupos g
        WHERE g.id_distrito=%s
        ORDER BY g.id_grupo DESC
    """, (id_distrito,))
    st.dataframe(grupos, use_container_width=True)
    return grupos

def _crear_directiva_para_grupo():
    st.subheader("Crear usuario de Directiva para un grupo")
    # Solo grupos del distrito de la promotora
    mis_grupos = fetch_all("""
        SELECT id_grupo, Nombre
        FROM grupos
        WHERE id_distrito=%s
        ORDER BY Nombre
    """, (current_user()["id_distrito"],))
    opciones = {f"{g['Nombre']} (id {g['id_grupo']})": g["id_grupo"] for g in mis_grupos}

    with st.form("form_directiva", clear_on_submit=True):
        nombre = st.text_input("Nombre mostrado del usuario Directiva (p.ej., 'Directiva Grupo X')")
        dui = st.text_input("DUI para el usuario de Directiva")
        contr = st.text_input("Contraseña inicial", type="password")
        sel = st.selectbox("Grupo", list(opciones.keys())) if opciones else None
        crear = st.form_submit_button("Crear Directiva")
        if crear:
            if not (nombre and dui and contr and sel):
                st.warning("Complete todos los campos.")
            else:
                id_grupo = opciones[sel]
                # Asegurar un usuario por grupo
                existe = fetch_one("SELECT id_usuarios FROM usuarios WHERE Rol='DIRECTIVA' AND id_grupo=%s LIMIT 1", (id_grupo,))
                if existe:
                    st.error("Ese grupo ya tiene usuario de Directiva.")
                    return
                sql = """
                    INSERT INTO usuarios (Nombre, DUI, Contraseña, Rol, id_grupo, Activo, Creado_en)
                    VALUES (%s, %s, %s, 'DIRECTIVA', %s, '1', %s)
                """
                _, uid = execute(sql, (nombre, dui, contr, id_grupo, date.today()))
                st.success(f"Directiva creada (id={uid}) para el grupo {id_grupo}.")

def _descargar_reportes():
    st.subheader("Reportes consolidados por grupo (placeholder)")
    st.info("Aquí puedes agregar exportación a CSV/Excel con totales de ahorros, préstamos, mora, etc.")

def promotora_panel():
    _validar_rol_promotora()
    u = current_user()
    st.markdown(f"### Distrito asignado: **{u.get('id_distrito')}**")

    tabs = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])
    with tabs[0]:
        _crear_grupo(u["id_distrito"])
    with tabs[1]:
        _listado_grupos(u["id_distrito"])
    with tabs[2]:
        _crear_directiva_para_grupo()
    with tabs[3]:
        _descargar_reportes()
