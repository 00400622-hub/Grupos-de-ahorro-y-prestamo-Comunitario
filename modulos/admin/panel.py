import streamlit as st
from datetime import date
from modulos.auth.rbac import require_auth, has_role
from modulos.config.conexion import fetch_all, fetch_one, execute

def _titulo(p): st.markdown(f"## {p}")

def _validar_rol_admin():
    require_auth()
    if not has_role("ADMINISTRADOR"):
        st.error("Acceso restringido al Administrador.")
        st.stop()

def _crud_distritos():
    _titulo("Distritos")
    st.caption("Crear y listar distritos.")
    with st.form("form_distrito", clear_on_submit=True):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")
        if enviar:
            if not nombre.strip():
                st.warning("Nombre requerido.")
            else:
                sql = "INSERT INTO distritos (Nombre, Creado_en) VALUES (%s, %s)"
                _, last_id = execute(sql, (nombre.strip(), date.today()))
                st.success(f"Distrito creado (id={last_id}).")

    distritos = fetch_all("SELECT id_distrito, Nombre, Creado_en FROM distritos ORDER BY id_distrito DESC")
    st.dataframe(distritos, use_container_width=True)

def _crear_promotora():
    _titulo("Promotoras")
    st.caption("Crear cuentas de promotora y asignarlas a un distrito (1 por distrito).")

    distritos = fetch_all("SELECT id_distrito, Nombre FROM distritos ORDER BY Nombre ASC")
    mapa = {f"{d['Nombre']} (id {d['id_distrito']})": d["id_distrito"] for d in distritos}
    nombres = list(mapa.keys())

    with st.form("form_promotora", clear_on_submit=True):
        nombre = st.text_input("Nombre de la promotora")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña inicial", type="password")
        distrito_sel = st.selectbox("Distrito", nombres) if nombres else None
        crear = st.form_submit_button("Crear promotora")

        if crear:
            if not (nombre and dui and contr and distrito_sel):
                st.warning("Complete todos los campos.")
            else:
                id_distrito = mapa[distrito_sel]
                # Enforzar 1 promotora por distrito
                existente = fetch_one("SELECT id_usuarios FROM usuarios WHERE Rol='PROMOTORA' AND id_distrito=%s LIMIT 1", (id_distrito,))
                if existente:
                    st.error("Ya existe una promotora para ese distrito.")
                else:
                    sql = """
                        INSERT INTO usuarios (Nombre, DUI, Contraseña, Rol, id_distrito, Activo, Creado_en)
                        VALUES (%s, %s, %s, 'PROMOTORA', %s, '1', %s)
                    """
                    _, uid = execute(sql, (nombre, dui, contr, id_distrito, date.today()))
                    st.success(f"Promotora creada (id={uid}) para el distrito {id_distrito}.")

    # Listado
    prom = fetch_all("""
        SELECT u.id_usuarios, u.Nombre, u.DUI, u.id_distrito, d.Nombre AS Distrito
        FROM usuarios u
        LEFT JOIN distritos d ON d.id_distrito = u.id_distrito
        WHERE u.Rol='PROMOTORA'
        ORDER BY d.Nombre, u.Nombre
    """)
    st.dataframe(prom, use_container_width=True)

def _reportes_globales():
    _titulo("Reportes globales")
    st.info("Aquí puedes agregar KPIs globales, totales por distrito y cartera consolidada.\nDe momento es un placeholder.")

def admin_panel():
    _validar_rol_admin()
    tabs = st.tabs(["Distritos", "Promotoras", "Reportes globales"])
    with tabs[0]:
        _crud_distritos()
    with tabs[1]:
        _crear_promotora()
    with tabs[2]:
        _reportes_globales()
