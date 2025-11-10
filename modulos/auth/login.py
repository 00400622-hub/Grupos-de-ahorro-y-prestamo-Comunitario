                                                                                                                                                        import streamlit as st
import bcrypt
from modulos.config.conexion import obtener_conexion

def _row_to_dict(cursor, row):
    return {d[0]: v for d, v in zip(cursor.description, row)}

def _normalizar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())

def _es_activo(valor) -> bool:
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

        try:
            con = obtener_conexion()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.stop()

        # Usa dictionary=True para mapear por nombre
        cur = con.cursor(dictionary=True)

        try:
            # NOMBRES EXACTOS de tu tabla (con backticks)
            # id_usuarios, Nombre, DUI, Contraseña, Rol, Id_distrito, Id_grupo, Activo
            sql = """
                SELECT
                    `id_usuarios`    AS id,
                    `Nombre`         AS nombre,
                    `DUI`            AS dui,
                    `Contraseña`     AS hash_password,
                    `Rol`            AS rol,
                    `Id_distrito`    AS distrito_id,
                    `Id_grupo`       AS grupo_id,
                    `Activo`         AS activo
                FROM `usuarios`
                WHERE REPLACE(`DUI`, '-', '') = %s
                LIMIT 1
            """
            cur.execute(sql, (dui,))
            data = cur.fetchone()
        except Exception as e:
            st.error("Error al consultar la tabla `usuarios`. "
                     "Verifica que las columnas existan EXACTAMENTE con estos nombres: "
                     "`id_usuarios`, `Nombre`, `DUI`, `Contraseña`, `Rol`, `Id_distrito`, `Id_grupo`, `Activo`.")
            st.caption(f"Detalle técnico: {e}")
            cur.close(); con.close()
            return

        if not data:
            st.error("Usuario no encontrado.")
            cur.close(); con.close()
            return

        # Activo
        if not _es_activo(data.get("activo")):
            st.error("Usuario inactivo.")
            cur.close(); con.close()
            return

        # Validar contraseña (hash guardado en columna `Contraseña`)
        try:
            ok = bcrypt.checkpw(password.encode(), str(data["hash_password"]).encode())
        except Exception as e:
            st.error("El hash de contraseña en la BD no es válido (columna `Contraseña`).")
            st.caption(f"Detalle técnico: {e}")
            cur.close(); con.close()
            return

        if not ok:
            st.error("Contraseña incorrecta.")
            cur.close(); con.close()
            return

        # Cargar permisos por rol (tu tabla con mayúscula inicial: Rol_permiso)
        try:
            cur.execute("""
                SELECT p.clave
                FROM `Rol_permiso` rp
                JOIN `permisos` p ON p.id = rp.permiso_id
                WHERE rp.rol = %s
            """, (data["rol"],))
            permisos = {r["clave"] for r in cur.fetchall()}
        except Exception as e:
            st.error("No pude leer permisos del rol. Revisa la tabla `Rol_permiso` y `permisos`.")
            st.caption(f"Detalle técnico: {e}")
            cur.close(); con.close()
            return

        # Guardar sesión
        st.session_state["user"] = {
            "id": data["id"],
            "nombre": data["nombre"],
            "dui": data["dui"],
            "rol": data["rol"],
            "distrito_id": data.get("distrito_id"),
            "grupo_id": data.get("grupo_id"),
        }
        st.session_state["permisos"] = permisos
        st.session_state["autenticado"] = True

        cur.close(); con.close()
        st.success(f"Bienvenido, {data['nombre']}")
                                                                                                                                         
                WHERE rp.rol = %s
            """, (data["rol"],))
            permisos = {r[0] for r in cur.fetchall()}

            # Guardar sesión
            st.session_state["user"] = {
                "id": data["id"],
                "nombre": data["nombre"],
                "dui": data["dui"],
                "rol": data["rol"],
                "distrito_id": data.get("distrito_id"),
                "grupo_id": data.get("grupo_id"),
            }
            st.session_state["permisos"] = permisos
            st.session_state["autenticado"] = True
            st.success(f"Bienvenido, {data['nombre']}")

        finally:
            cur.close(); con.close()
