import streamlit as st
from modulos.config.conexion import obtener_conexion


def _normalizar_dui(txt: str) -> str:
    """Limpia el DUI y deja solo los dígitos."""
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _es_activo(valor) -> bool:
    """Interpreta si el valor de 'Activo' representa un usuario activo."""
    if valor is None:
        return True
    v = str(valor).strip().lower()
    return v in {"1", "si", "sí", "activo", "true", "t"}


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

        # Intentar conectar con la base de datos
        try:
            con = obtener_conexion()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.stop()

        cur = con.cursor(dictionary=True)

        # Buscar usuario
        try:
            sql = """
                SELECT
                    `id_usuarios`    AS id,
                    `Nombre`         AS nombre,
                    `DUI`            AS dui,
                    `Contraseña`     AS password,
                    `Rol`            AS rol,
                    `Id_distrito`    AS distrito_id,
                    `Id-grupo`       AS grupo_id,
                    `Activo`         AS activo
                FROM `usuarios`
                WHERE REPLACE(`DUI`, '-', '') = %s
                LIMIT 1
            """
            cur.execute(sql, (dui,))
            data = cur.fetchone()
        except Exception as e:
            st.error("Error al consultar la tabla `usuarios`. Verifica los nombres de columnas.")
            st.caption(f"Detalle técnico: {e}")
            cur.close()
            con.close()
            return

        # Validaciones
        if not data:
            st.error("Usuario no encontrado.")
            cur.close()
            con.close()
            return

        if not _es_activo(data.get("activo")):
            st.error("Usuario inactivo.")
            cur.close()
            con.close()
            return

        if str(password) != str(data["password"]):
            st.error("Contraseña incorrecta.")
            cur.close()
            con.close()
            return

        # Leer permisos según el rol detectando columnas
        try:
            cur.execute("SHOW COLUMNS FROM `permisos`")
            pcols = {row["Field"].lower(): row["Field"] for row in cur.fetchall()}

            p_id = pcols.get("id") or pcols.get("id_permisos") or pcols.get("idpermiso") or pcols.get("id_permiso")
            p_clave = pcols.get("clave") or pcols.get("nombre") or pcols.get("permiso") or pcols.get("descripcion")
            if not p_id or not p_clave:
                raise RuntimeError("No encuentro columnas 'id'/'clave' en la tabla `permisos`.")

            cur.execute("SHOW COLUMNS FROM `Rol_permiso`")
            rpcols = {row["Field"].lower(): row["Field"] for row in cur.fetchall()}

            rp_permiso_id = (
                rpcols.get("permiso_id")
                or rpcols.get("id_permiso")
                or rpcols.get("idpermisos")
                or rpcols.get("id_permisos")
            )
            rp_rol = rpcols.get("rol") or rpcols.get("Rol") or rpcols.get("ROL")
            if not rp_permiso_id or not rp_rol:
                raise RuntimeError("No encuentro columnas 'permiso_id' y/o 'rol' en la tabla `Rol_permiso`.")

            sql_perm = f"""
                SELECT p.`{p_clave}` AS clave
                FROM `Rol_permiso` rp
                JOIN `permisos` p ON p.`{p_id}` = rp.`{rp_permiso_id}`
                WHERE rp.`{rp_rol}` = %s
            """
            cur.execute(sql_perm, (data["rol"],))
            permisos = {r["clave"] for r in cur.fetchall()}
        except Exception as e:
            st.error("No pude leer permisos del rol. Revisa las tablas `Rol_permiso` y `permisos`.")
            st.caption(f"Detalle técnico: {e}")
            cur.close()
            con.close()
            return

        # --- Normalizar rol a valores canónicos ---
        rol_db = str(data["rol"]).strip().upper()

        if rol_db in ("ADMIN", "ADMINISTRADOR"):
            rol_canon = "ADMIN"
        elif rol_db in ("PROMOTORA", "PROMOTOR", "PROMOTORA DISTRITAL"):
            rol_canon = "PROMOTORA"
        elif rol_db in ("DIRECTIVA", "PRESIDENTE", "SECRETARIA"):
            rol_canon = "DIRECTIVA"
        else:
            rol_canon = rol_db

        # Guardar sesión usando el rol normalizado
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

        cur.close()
        con.close()

        # Recargar para mostrar el panel correspondiente
        st.success(f"Bienvenido, {data['nombre']}")
        st.rerun()
