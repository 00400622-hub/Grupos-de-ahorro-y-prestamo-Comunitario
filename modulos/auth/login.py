import streamlit as st
from modulos.config.conexion import db_conn


def _normalizar_dui(txt: str) -> str:
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _pick(colmap: dict[str, str], *cands: str) -> str:
    """Devuelve el nombre REAL de columna (respetando mayúsculas, acentos, guiones)."""
    for c in cands:
        real = colmap.get(c.lower())
        if real:
            return real
    raise KeyError(f"No se encontró ninguna de estas columnas: {cands}")


def _cols(table: str) -> dict[str, str]:
    """Mapea nombres en minúscula -> nombre real de la columna en la tabla."""
    with db_conn() as con:
        cur = con.cursor(dictionary=True)
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        res = {r["Field"].lower(): r["Field"] for r in cur.fetchall()}
        cur.close()
        return res


def login_screen():
    st.title("SGI GAPC — Iniciar sesión")

    dui_in = st.text_input("DUI (con o sin guion)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", type="primary"):
        dui = _normalizar_dui(dui_in)
        if len(dui) != 9:
            st.error("DUI inválido (9 dígitos).")
            return

        try:
            # --- detectar nombres REALES de columnas en `usuarios`
            uc = _cols("usuarios")
            c_id        = _pick(uc, "id_usuarios", "id", "id_usuario", "idusuarios")
            c_nombre    = _pick(uc, "nombre")
            c_dui       = _pick(uc, "dui")
            c_pass      = _pick(uc, "contraseña", "contrasena", "password", "clave")
            c_rol       = _pick(uc, "rol")
            c_distrito  = _pick(uc, "id_distrito", "distrito_id")
            # aquí aceptamos tanto `Id-grupo` como `Id_grupo`/`grupo_id`
            c_grupo     = _pick(uc, "id-grupo", "id_grupo", "grupo_id")
            c_activo    = _pick(uc, "activo", "estado")

            # --- consulta del usuario (TODOS los identificadores con backticks)
            with db_conn() as con:
                cur = con.cursor(dictionary=True)
                try:
                    sql = f"""
                        SELECT
                          `{c_id}`       AS id,
                          `{c_nombre}`   AS nombre,
                          `{c_dui}`      AS dui,
                          `{c_pass}`     AS password,
                          `{c_rol}`      AS rol,
                          `{c_distrito}` AS distrito_id,
                          `{c_grupo}`    AS grupo_id,
                          `{c_activo}`   AS activo
                        FROM `usuarios`
                        WHERE REPLACE(`{c_dui}`, '-', '') = %s
                        LIMIT 1
                    """
                    cur.execute(sql, (dui,))
                    data = cur.fetchone()
                finally:
                    cur.close()

            if not data:
                st.error("Usuario no encontrado.")
                return

            # contraseña en texto plano (como pediste)
            if str(password) != str(data["password"]):
                st.error("Contraseña incorrecta.")
                return

            # --- normalizar rol para que ADMINISTRADOR cuente como ADMIN
            rol_db = str(data["rol"]).strip().upper()
            if rol_db in ("ADMIN", "ADMINISTRADOR"):
                rol = "ADMIN"
            elif rol_db in ("PROMOTORA", "PROMOTOR", "PROMOTORA DISTRITAL"):
                rol = "PROMOTORA"
            elif rol_db in ("DIRECTIVA", "PRESIDENTE", "SECRETARIA"):
                rol = "DIRECTIVA"
            else:
                rol = rol_db

            # --- guardar sesión
            st.session_state["user"] = {
                "id": data["id"],
                "nombre": data["nombre"],
                "dui": data["dui"],
                "rol": rol,
                "distrito_id": data.get("distrito_id"),
                "grupo_id": data.get("grupo_id"),
            }
            st.session_state["autenticado"] = True
            st.success(f"Bienvenido, {data['nombre']}.")
            st.rerun()

        except Exception as e:
            st.error("Error al consultar la base de datos.")
            st.caption(f"Detalle: {e}")
