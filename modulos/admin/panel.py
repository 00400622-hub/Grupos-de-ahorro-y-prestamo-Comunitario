import streamlit as st
from modulos.config.conexion import obtener_conexion


# -------- utilidades de autodetección --------
def _cols(table: str) -> dict[str, str]:
    """Devuelve {lower_name: RealName} para una tabla."""
    with obtener_conexion() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        return {r["Field"].lower(): r["Field"] for r in cur.fetchall()}

def _pick(colmap: dict[str, str], *cands: str) -> str:
    """Toma el primer nombre de columna que exista en el colmap."""
    for c in cands:
        r = colmap.get(c.lower())
        if r:
            return r
    raise KeyError(f"No se encontró ninguna de estas columnas: {cands}")

def _norm_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())


# -------- Distritos (listar/crear) --------
def gestionar_distritos():
    st.subheader("Distritos")

    try:
        dc = _cols("distritos")           # columnas reales de distritos
        d_id = _pick(dc, "id", "id_distrito", "iddistrito")
        d_nombre = _pick(dc, "nombre", "name")
    except Exception as e:
        st.error("No pude leer la estructura de la tabla `distritos`.")
        st.caption(f"Detalle: {e}")
        return

    # Listado
    try:
        with obtener_conexion() as con:
            cur = con.cursor(dictionary=True)
            cur.execute(
                f"SELECT `{d_id}` AS id, `{d_nombre}` AS nombre FROM `distritos` ORDER BY `{d_id}`"
            )
            st.table(cur.fetchall())
    except Exception as e:
        st.error("No pude consultar los distritos.")
        st.caption(f"Detalle: {e}")

    # Crear
    st.markdown("**Crear nuevo distrito**")
    nombre = st.text_input("Nombre del distrito", key="nuevo_distrito")
    if st.button("Crear distrito", type="primary"):
        if not nombre.strip():
            st.warning("Ingresa un nombre válido."); return
        try:
            with obtener_conexion() as con:
                cur = con.cursor()
                cur.execute(
                    f"INSERT INTO `distritos` (`{d_nombre}`) VALUES (%s)",
                    (nombre.strip(),),
                )
                con.commit()
            st.success("Distrito creado.")
            st.rerun()
        except Exception as e:
            st.error("No se pudo crear el distrito.")
            st.caption(f"Detalle: {e}")


# -------- Usuarios (crear con tus columnas) --------
def gestionar_usuarios():
    st.subheader("Crear usuarios")

    # detectamos columnas reales de `usuarios`
    try:
        uc = _cols("usuarios")
        u_nombre = _pick(uc, "nombre")
        u_dui = _pick(uc, "dui")
        u_pass = _pick(uc, "contraseña", "contrasena", "password", "clave")
        u_rol = _pick(uc, "rol")
        u_id_distrito = _pick(uc, "id_distrito", "distrito_id")
        u_id_grupo = _pick(uc, "id-grupo", "id_grupo", "grupo_id")
        u_activo = _pick(uc, "activo", "estado")
    except Exception as e:
        st.error("No pude leer la estructura de la tabla `usuarios`.")
        st.caption(f"Detalle: {e}")
        return

    # datos del formulario
    rol = st.selectbox("Rol", ["PROMOTORA", "DIRECTIVA", "ADMIN"])
    nombre = st.text_input("Nombre completo")
    dui = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    # selector de distrito para Promotora
    distrito_id = None
    if rol == "PROMOTORA":
        try:
            dc = _cols("distritos")
            d_id = _pick(dc, "id", "id_distrito", "iddistrito")
            d_nombre = _pick(dc, "nombre", "name")
            with obtener_conexion() as con:
                cur = con.cursor(dictionary=True)
                cur.execute(
                    f"SELECT `{d_id}` AS id, `{d_nombre}` AS nom FROM `distritos` ORDER BY `{d_nombre}`"
                )
                dists = cur.fetchall()
            opts = {f"{d['nom']} (id={d['id']})": d["id"] for d in dists}
            sel = st.selectbox("Distrito", list(opts.keys())) if opts else None
            distrito_id = opts.get(sel) if sel else None
        except Exception as e:
            st.error("No pude cargar distritos para la promotora.")
            st.caption(f"Detalle: {e}")

    # selector de grupo para Directiva
    grupo_id = None
    if rol == "DIRECTIVA":
        try:
            # columnas de grupos
            gc = _cols("grupos")
            g_id = _pick(gc, "id", "id_grupo", "idgrupos")
            g_nombre = _pick(gc, "nombre", "name")
            g_distrito_fk = _pick(gc, "distrito_id", "id_distrito")
            g_estado = gc.get("estado")  # puede que no exista

            # columnas de distritos para join (solo para mostrar)
            dc = _cols("distritos")
            d_id = _pick(dc, "id", "id_distrito", "iddistrito")
            d_nombre = _pick(dc, "nombre", "name")

            where_estado = f"WHERE g.`{g_estado}`='ACTIVO'" if g_estado else ""
            sql = f"""
                SELECT g.`{g_id}` AS id, CONCAT(g.`{g_nombre}`,' — ',d.`{d_nombre}`) AS nom
                FROM `grupos` g
                JOIN `distritos` d ON d.`{d_id}` = g.`{g_distrito_fk}`
                {where_estado}
                ORDER BY d.`{d_nombre}`, g.`{g_nombre}`
            """
            with obtener_conexion() as con:
                cur = con.cursor(dictionary=True)
                cur.execute(sql)
                grupos = cur.fetchall()
            og = {f"{g['nom']} (id={g['id']})": g["id"] for g in grupos}
            selg = st.selectbox("Grupo", list(og.keys())) if og else None
            grupo_id = og.get(selg) if selg else None
        except Exception as e:
            st.error("No pude cargar grupos para la directiva.")
            st.caption(f"Detalle: {e}")

    # guardar usuario
    if st.button("Guardar usuario", type="primary"):
        dui_digits = _norm_dui(dui or "")
        if not all([nombre.strip(), dui_digits, password.strip()]):
            st.warning("Completa nombre, DUI y contraseña."); return
        if len(dui_digits) != 9:
            st.warning("DUI inválido (9 dígitos)."); return
        if rol == "PROMOTORA" and not distrito_id:
            st.warning("Selecciona un distrito."); return
        if rol == "DIRECTIVA" and not grupo_id:
            st.warning("Selecciona un grupo."); return

        try:
            with obtener_conexion() as con:
                cur = con.cursor()
                cur.execute(
                    f"""
                    INSERT INTO `usuarios`
                        (`{u_nombre}`, `{u_dui}`, `{u_pass}`, `{u_rol}`, `{u_id_distrito}`, `{u_id_grupo}`, `{u_activo}`)
                    VALUES (%s, %s, %s, %s, %s, %s, '1')
                    """,
                    (nombre.strip(), dui_digits, password.strip(), rol, distrito_id, grupo_id),
                )
                con.commit()
            st.success("Usuario creado.")
        except Exception as e:
            st.error("No se pudo crear el usuario.")
            st.caption(f"Detalle: {e}")


def panel_admin():
    st.header("Panel del Administrador")
    tabs = st.tabs(["Distritos", "Usuarios"])
    with tabs[0]:
        gestionar_distritos()
    with tabs[1]:
        gestionar_usuarios()
