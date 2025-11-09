import streamlit as st, bcrypt
from modulos.config.conexion import obtener_conexion
from modulos.auth.rbac import requiere

@requiere("distrito.crear")
def gestionar_distritos():
    st.subheader("Distritos")
    with obtener_conexion() as con:
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT id,nombre,creado_en FROM distritos ORDER BY id")
        lista = cur.fetchall()
    if lista:
        st.table(lista)
    st.markdown("**Crear nuevo distrito**")
    nombre = st.text_input("Nombre del distrito")
    if st.button("Crear distrito", type="primary"):
        if not nombre.strip():
            st.warning("Ingresa un nombre válido."); return
        with obtener_conexion() as con:
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO distritos (nombre) VALUES (%s)", (nombre.strip(),))
                con.commit(); st.success("Distrito creado."); st.experimental_rerun()
            except Exception as e:
                con.rollback(); st.error(f"No se pudo crear: {e}")

@requiere("admin.usuarios")
def gestionar_usuarios():
    st.subheader("Usuarios")
    # Crear usuario
    rol = st.selectbox("Rol", ["PROMOTORA","DIRECTIVA","ADMIN"])
    nombre = st.text_input("Nombre")
    email = st.text_input("Email")
    password = st.text_input("Contraseña temporal", type="password")

    distrito_id = None; grupo_id = None

    # Si Promotora: seleccionar distrito
    if rol == "PROMOTORA":
        with obtener_conexion() as con:
            cur = con.cursor(dictionary=True)
            cur.execute("SELECT id,nombre FROM distritos ORDER BY nombre")
            dists = cur.fetchall()
        dist_map = {f"{d['nombre']} (id={d['id']})": d["id"] for d in dists}
        sel = st.selectbox("Distrito", list(dist_map.keys())) if dists else None
        distrito_id = dist_map.get(sel) if sel else None

    # Si Directiva: seleccionar grupo (de cualquier distrito)
    if rol == "DIRECTIVA":
        with obtener_conexion() as con:
            cur = con.cursor(dictionary=True)
            cur.execute("""SELECT g.id, CONCAT(g.nombre,' — ',d.nombre) AS nom
                           FROM grupos g JOIN distritos d ON d.id=g.distrito_id
                           WHERE g.estado='ACTIVO' ORDER BY d.nombre,g.nombre""")
            grupos = cur.fetchall()
        grp_map = {f"{g['nom']} (id={g['id']})": g["id"] for g in grupos}
        selg = st.selectbox("Grupo", list(grp_map.keys())) if grupos else None
        grupo_id = grp_map.get(selg) if selg else None

    if st.button("Crear usuario", type="primary"):
        if not all([nombre.strip(), email.strip(), password.strip()]):
            st.warning("Completa nombre, email y contraseña."); return
        if rol == "PROMOTORA" and not distrito_id:
            st.warning("Selecciona un distrito."); return
        if rol == "DIRECTIVA" and not grupo_id:
            st.warning("Selecciona un grupo."); return
        hpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with obtener_conexion() as con:
            cur = con.cursor()
            try:
                cur.execute("""INSERT INTO usuarios
                               (nombre,email,hash_password,rol,distrito_id,grupo_id)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (nombre.strip(), email.strip(), hpw, rol, distrito_id, grupo_id))
                con.commit(); st.success("Usuario creado.")
            except Exception as e:
                con.rollback(); st.error(f"No se pudo crear: {e}")

def panel_admin():
    st.header("Panel del Administrador")
    tabs = st.tabs(["Distritos","Usuarios"])
    with tabs[0]: gestionar_distritos()
    with tabs[1]: gestionar_usuarios()
