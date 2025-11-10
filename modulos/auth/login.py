import streamlit as st
from modulos.config.conexion import obtener_conexion


def _normalizar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _es_activo(valor) -> bool:
    if valor is None:
        return True
    v = str(valor).strip().lower()
    return v in {"1", "si", "sí", "activo", "true", "t"}


def _first_match(colmap: dict[str, str], *candidates: str) -> str:
    """
    Devuelve el nombre REAL de la columna en la tabla, buscando entre varias variantes.
    colmap: dict {lower_name: RealName}
    """
    for c in candidates:
        real = colmap.get(c.lower())
        if real:
            return real
    raise KeyError(f"No se encontró ninguna de estas columnas: {candidates}")


def login_screen():
    st.title("SGI GAPC — Iniciar sesión")

    dui_in = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        dui = _normalizar_dui(dui_in)
        if len(dui) != 9:
            st.warning("Ingresa un DUI válido (9 dígitos).")
            return
        if not password:
            st.warning("Ingresa la contraseña.")
            return

        # Conexión
        try:
            con = obtener_conexion()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.stop()
        cur = con.cursor(dictionary=True)

        # --- Detectar nombres REALES de columnas en `usuarios`
        try:
            cur.execute("SHOW COLUMNS FROM `usuarios`")
            ucols = {row["Field"].lower(): row["Field"] for row in cur.fetchall()}

            col_id = _first_match(ucols, "id", "id_usuarios", "idusuarios", "id_usuario")
            col_nombre = _first_match(ucols, "nombre")
            col_dui = _first_match(ucols, "dui")
            col_pass = _first_match(ucols, "contraseña", "contrasena", "password", "clave")
            col_rol = _first_match(ucols, "rol")
            col_dist = _first_match(ucols, "id_distrito", "distrito_id")
            # ← aquí aceptamos tanto Id-grupo (con guion) como Id_grupo / grupo_id
            col_grupo = _first_match(ucols, "id-grupo", "id_grupo", "grupo_id")
            col_activo = _first_match(ucols, "activo", "estado")

            sql = f"""
                SELECT
                    `{col_id}`      AS id,
                    `{col_nombre}`  AS nombre,
                    `{col_dui}`     AS dui,
                    `{col_pass}`    AS password,
                    `{col_rol}`     AS rol,
                    `{col_dist}`    AS distrito_id,
                    `{col_grupo}`   AS grupo_id,
                    `{col_activo}`  AS activo
                FROM `usuarios`
                WHERE REPLACE(`{col_dui}`, '-', '') = %s
                LIMIT 1
            """
            cur.execute(sql, (dui,))
            data = cur.fetchone()
        except Exception as e:
            st.error("Error al consultar la tabla `usuarios`. Verifica los nombres de columnas.")
            st.caption(f"Detalle técnico: {e}")
            cur.close(); con.close()
            return

        if not data:
            st.error("Usuario no encontrado.")
            cur.close(); con.close()
            return

        if not _es_activo(data.get("activo")):
            st.error("Usuario inactivo.")
            cur.close(); con.close()
            return

        if str(password) != str(data["password"]):
            st.error("Contraseña incorrecta.")
            cur.close(); con.close()
            return

        # --- Permisos (detección automática en permisos / Rol_permiso)
        try:
            cur.execute("SHOW COLUMNS FROM `permisos`")
            pcols = {row["Field"].lower(): row["Field"] for row in cur.fetchall()}
            p_id = _first_match(pcols, "id", "id_permisos", "id_permiso")
            p_clave = _first_match(pcols, "clave", "nombre", "permiso", "descripcion")

            cur.execute("SHOW COLUMNS FROM `Rol_permiso`")
            rpcols = {row["Field"].lower(): row["Field"] for row in cur.fetchall()}
            rp_permiso_id = _first_match(rpcols, "permiso_id", "id_permiso", "id_permisos")
            rp_rol = _first_match(rpcols, "rol")

            sql_perm = f"""
                SELECT p.`{p_clave}` AS clave
                FROM `Rol_permiso` rp
                JOIN `permisos` p ON p.`{p_id}` = rp.`{rp_permiso_id}`
                WHERE rp.`{rp_rol}` = %s
            """
            cur.execute(sql_perm, (data["rol"],))
            permisos = {r["clave"] for r in cur.fetchall()}
        except Exception as e:
            st.error("No pude leer permisos del rol. Revisa `permisos` y `Rol_permiso`.")
            st.caption(f"Detalle técnico: {e}")
            cur.close(); con.close()
            return

        # --- Normalizar rol (ADMINISTRADOR → ADMIN, etc.)
        rol_db = str(data["rol"]).strip().upper()
        if rol_db in ("ADMIN", "ADMINISTRADOR"):
            rol_canon = "ADMIN"
        elif rol_db in ("PROMOTORA", "PROMOTOR", "PROMOTORA DISTRITAL"):
            rol_canon = "PROMOTORA"
        elif rol_db in ("DIRECTIVA", "PRESIDENTE", "SECRETARIA"):
            rol_canon = "DIRECTIVA"
        else:
            rol_canon = rol_db

        # Guardar sesión
        st.session_state["user"] = {
            "id": data["id"],
            "nombre": data["nombre"],
            "dui": data["dui"],
            "rol": rol_canon,
            "distrito_id": data.get("distrito_id"),
            "grupo_id": data.get("grupo_id"),
        }
        st.session_state["permisos"] = permisos
        st.session_state["autenticado"] = True

        cur.close(); con.close()

        st.success(f"Bienvenido, {data['nombre']}")
        st.rerun()
