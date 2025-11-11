import streamlit as st
from modulos.config.conexion import db_conn


def _solo_digitos(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _esta_activo(v) -> bool:
    if v is None:
        return True
    v = str(v).strip().lower()
    return v in {"1", "si", "sí", "activo", "true"}


def login_screen():
    st.title("SGI GAPC — Iniciar sesión")

    dui_in = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        dui = _solo_digitos(dui_in)
        if len(dui) != 9:
            st.error("DUI inválido (9 dígitos).")
            return

        try:
            with db_conn() as con:
                cur = con.cursor(dictionary=True)
                try:
                    # OJO: usamos exactamente los nombres de tu tabla
                    cur.execute(
                        """
                        SELECT
                          `Id_usuarios`  AS id,
                          `Nombre`       AS nombre,
                          `DUI`          AS dui,
                          `Contraseña`   AS pass,
                          `Rol`          AS rol,
                          `Id_distrito`  AS distrito_id,
                          `Id_grupo`     AS grupo_id,
                          `Activo`       AS activo
                        FROM `usuarios`
                        WHERE REPLACE(`DUI`, '-', '') = %s
                        LIMIT 1
                        """,
                        (dui,),
                    )
                    data = cur.fetchone()
                finally:
                    cur.close()

            if not data:
                st.error("Usuario no encontrado.")
                return

            if not _esta_activo(data.get("activo")):
                st.error("Usuario inactivo.")
                return

            # Contraseña en texto plano (como acordamos)
            if str(password) != str(data["pass"]):
                st.error("Contraseña incorrecta.")
                return

            # Normalizar rol para el ruteo
            rol_db = str(data["rol"]).strip().upper()
            if rol_db in ("ADMIN", "ADMINISTRADOR"):
                rol = "ADMIN"
            elif rol_db in ("PROMOTORA", "PROMOTOR", "PROMOTORA DISTRITAL"):
                rol = "PROMOTORA"
            elif rol_db in ("DIRECTIVA", "PRESIDENTE", "SECRETARIA"):
                rol = "DIRECTIVA"
            else:
                rol = rol_db

            # Guardar sesión
            st.session_state["user"] = {
                "id": data["id"],
                "nombre": data["nombre"],
                "dui": data["dui"],
                "rol": rol,
                "distrito_id": data.get("distrito_id"),
                "grupo_id": data.get("grupo_id"),
            }
            st.session_state["autenticado"] = True

            st.success(f"Bienvenid@, {data['nombre']}.")
            st.rerun()

        except Exception as e:
            st.error("Error al consultar la base de datos.")
            st.caption(f"Detalle: {e}")
