import streamlit as st
from modulos.config.conexion import db_conn


def _solo_digitos(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


# ==============================
# Distritos
# ==============================
def gestionar_distritos():
    st.subheader("Distritos")

    # Listado
    try:
        with db_conn() as con:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT `Id_distrito` AS id, `Nombre` AS nombre, `Creado_en` AS creado
                FROM `distritos`
                ORDER BY `Id_distrito`
                """
            )
            filas = cur.fetchall()
            cur.close()

        if filas:
            st.table(filas)
        else:
            st.markdown("_empty_")

    except Exception as e:
        st.error("No pude consultar los distritos.")
        st.caption(f"Detalle: {e}")

    # Crear
    st.markdown("**Crear nuevo distrito**")
    nombre = st.text_input("Nombre del distrito", key="nuevo_distrito")

    if st.button("Crear distrito", type="primary"):
        if not nombre.strip():
            st.warning("Ingresa un nombre válido.")
            return

        try:
            with db_conn() as con:
                cur = con.cursor()
                # Tu columna 'Creado_en' es DATE -> usamos CURDATE()
                cur.execute(
                    "INSERT INTO `distritos` (`Nombre`, `Creado_en`) VALUES (%s, CURDATE())",
                    (nombre.strip(),),
                )
                con.commit()
                cur.close()

            st.success("Distrito creado.")
            st.rerun()

        except Exception as e:
            st.error("No se pudo crear el distrito.")
            st.caption(f"Detalle: {e}")


# ==============================
# Usuarios
# ==============================
def gestionar_usuarios():
    st.subheader("Usuarios")

    # Formulario
    rol = st.selectbox("Rol", ["PROMOTORA", "DIRECTIVA", "ADMIN"])
    nombre = st.text_input("Nombre completo")
    dui = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    # Seleccionar distrito (para PROMOTORA)
    distrito_id = None
    if rol == "PROMOTORA":
        try:
            with db_conn() as con:
                cur = con.cursor(dictionary=True)
                cur.execute(
                    "SELECT `Id_distrito` AS id, `Nombre` AS nom FROM `distritos` ORDER BY `Nombre`"
                )
                dists = cur.fetchall()
                cur.close()
            opts = {f"{d['nom']} (id={d['id']})": d["id"] for d in dists}
            sel = st.selectbox("Distrito", list(opts.keys())) if opts else None
            distrito_id = opts.get(sel) if sel else None
        except Exception as e:
            st.error("No pude cargar distritos.")
            st.caption(f"Detalle: {e}")

    # Seleccionar grupo (para DIRECTIVA) — si aún no tienes tabla grupos poblada, puedes omitir
    grupo_id = None
    if rol == "DIRECTIVA":
        try:
            with db_conn() as con:
                cur = con.cursor(dictionary=True)
                cur.execute(
                    "SELECT `Id_grupo` AS id, `Nombre` AS nom FROM `grupos` ORDER BY `Nombre`"
                )
                grupos = cur.fetchall()
                cur.close()
            og = {f"{g['nom']} (id={g['id']})": g["id"] for g in grupos}
            selg = st.selectbox("Grupo", list(og.keys())) if og else None
            grupo_id = og.get(selg) if selg else None
        except Exception as e:
            # Si no existe o está vacía, no bloquees la pantalla
            st.info("Aún no hay grupos cargados o la tabla no existe.")
            st.caption(f"Detalle (opcional): {e}")

    # Guardar
    if st.button("Guardar usuario", type="primary"):
        dui_digits = _solo_digitos(dui)
        if not all([nombre.strip(), dui_digits, password.strip()]):
            st.warning("Completa nombre, DUI y contraseña.")
            return
        if len(dui_digits) != 9:
            st.warning("DUI inválido (9 dígitos).")
            return
        if rol == "PROMOTORA" and not distrito_id:
            st.warning("Selecciona un distrito.")
            return
        if rol == "DIRECTIVA" and not grupo_id:
            st.warning("Selecciona un grupo.")
            return

        try:
            with db_conn() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    INSERT INTO `usuarios`
                       (`Nombre`, `DUI`, `Contraseña`, `Rol`, `Id_distrito`, `Id_grupo`, `Activo`, `Creado_en`)
                    VALUES (%s, %s, %s, %s, %s, %s, '1', CURDATE())
                    """,
                    (nombre.strip(), dui_digits, password.strip(), rol, distrito_id, grupo_id),
                )
                con.commit()
                cur.close()

            st.success("Usuario creado.")
        except Exception as e:
            st.error("No se pudo crear el usuario.")
            st.caption(f"Detalle: {e}")


# ==============================
# Panel del Administrador
# ==============================
def panel_admin():
    st.header("Panel del Administrador")
    tabs = st.tabs(["Distritos", "Usuarios"])
    with tabs[0]:
        gestionar_distritos()
    with tabs[1]:
        gestionar_usuarios()
