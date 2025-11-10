import streamlit as st
from modulos.config.conexion import obtener_conexion

def _normalizar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())

def gestionar_distritos():
    st.subheader("Distritos")
    # Listar
    with obtener_conexion() as con:
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT id, nombre FROM distritos ORDER BY id")
        st.table(cur.fetchall())

    # Crear
    st.markdown("**Crear nuevo distrito**")
    nombre = st.text_input("Nombre del distrito", key="nuevo_distrito")
    if st.button("Crear distrito", type="primary"):
        if not nombre.strip():
            st.warning("Ingresa un nombre válido."); return
        with obtener_conexion() as con:
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO distritos (nombre) VALUES (%s)", (nombre.strip(),))
                con.commit(); st.success("Distrito creado."); st.rerun()
            except Exception as e:
                con.rollback(); st.error(f"No se pudo crear: {e}")

def gestionar_usuarios():
    st.subheader("Crear usuarios")
    rol = st.selectbox("Rol", ["PROMOTORA","DIRECTIVA","ADMIN"])
    nombre = st.text_input("Nombre completo")
    dui = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    distrito_id = None; grupo_id = None

    if rol == "PROMOTORA":
        with obtener_conexion() as con:
            c = con.cursor(dictionary=True)
            c.execute("SELECT id, nombre FROM distritos ORDER BY nombre")
            dists = c.fetchall()
        opts = {f"{d['nombre']} (id={d['id']})": d["id"] for d in dists}
        sel = st.selectbox("Distrito", list(opts.keys())) if opts else None
        distrito_id = opts.get(sel) if sel else None

    if rol == "DIRECTIVA":
        with obtener_conexion() as con:
            c = con.cursor(dictionary=True)
            c.execute("""SELECT g.id, CONCAT(g.nombre,' — ',d.nombre) AS nom
                         FROM grupos g JOIN distritos d ON d.id=g.distrito_id
                         WHERE g.estado='ACTIVO' ORDER BY d.nombre,g.nombre""")
            grupos = c.fetchall()
        og = {f"{g['nom']} (id={g['id']})": g["id"] for g in grupos}
        selg = st.selectbox("Grupo", list(og.keys())) if og else None
        grupo_id = og.get(selg) if selg else None

    if st.button("Guardar usuario", type="primary"):
        dui_digits = _normalizar_dui(dui or "")
        if not all([nombre.strip(), dui_digits, password.strip()]):
            st.warning("Completa nombre, DUI y contraseña."); return
        if len(dui_digits) != 9:
            st.warning("DUI inválido (9 dígitos)."); return
        if rol == "PROMOTORA" and not distrito_id:
            st.warning("Selecciona un distrito."); return
        if rol == "DIRECTIVA" and not grupo_id:
            st.warning("Selecciona un grupo."); return

        with obtener_conexion() as con:
            cur = con.cursor()
            try:
                # OJO: respeta tus nombres de columnas con backticks
                cur.execute("""
                    INSERT INTO `usuarios`
                        (`Nombre`, `DUI`, `Contraseña`, `Rol`, `Id_distrito`, `Id-grupo`, `Activo`)
                    VALUES (%s, %s, %s, %s, %s, %s, '1')
                """, (nombre.strip(), dui_digits, password.strip(), rol, distrito_id, grupo_id))
                con.commit(); st.success("Usuario creado.")
            except Exception as e:
                con.rollback(); st.error(f"No se pudo crear: {e}")

def panel_admin():
    st.header("Panel del Administrador")
    tabs = st.tabs(["Distritos", "Usuarios"])
    with tabs[0]: gestionar_distritos()
    with tabs[1]: gestionar_usuarios()
