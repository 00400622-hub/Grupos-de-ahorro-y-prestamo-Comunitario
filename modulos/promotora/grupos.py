import streamlit as st
from modulos.config.conexion import obtener_conexion
from modulos.auth.rbac import requiere

@requiere("grupo.ver_distrito")
def listado_grupos_distrito():
    st.header("📋 Grupos de mi distrito")
    distrito_id = st.session_state["user"]["distrito_id"]

    with obtener_conexion() as con:
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT g.id, g.nombre, g.estado, d.nombre AS distrito
            FROM grupos g
            JOIN distritos d ON d.id = g.distrito_id
            WHERE g.distrito_id = %s
            ORDER BY g.estado DESC, g.nombre ASC
        """, (distrito_id,))
        grupos = cur.fetchall()

    if not grupos:
        st.info("No hay grupos registrados en tu distrito todavía.")
    else:
        for g in grupos:
            cols = st.columns([4,2,2])
            with cols[0]:
                st.write(f"**{g['nombre']}** · Estado: {g['estado']}")
            with cols[1]:
                st.link_button("Ver Detalle", f"#grupo-{g['id']}", disabled=True)
            with cols[2]:
                if g["estado"] == "ACTIVO" and st.session_state["user"]["rol"] == "PROMOTORA":
                    if st.button(f"🗑 Eliminar", key=f"del-{g['id']}"):
                        _eliminar_grupo_distrito_seguro(g["id"], distrito_id)

    st.divider()
    crear_grupo_form()

@requiere("grupo.crear")
def crear_grupo_form():
    st.subheader("➕ Crear nuevo grupo")
    nombre = st.text_input("Nombre del grupo")
    if st.button("Guardar grupo", type="primary"):
        if not nombre.strip():
            st.warning("Debes ingresar un nombre válido.")
            return
        distrito_id = st.session_state["user"]["distrito_id"]
        with obtener_conexion() as con:
            cur = con.cursor()
            try:
                cur.execute("""
                    INSERT INTO grupos (nombre, distrito_id, creado_por)
                    VALUES (%s, %s, %s)
                """, (nombre.strip(), distrito_id, st.session_state["user"]["id"]))
                con.commit()
                st.success("✅ Grupo creado exitosamente.")
                st.experimental_rerun()
            except Exception as e:
                con.rollback()
                st.error(f"Error al crear el grupo: {e}")

@requiere("grupo.eliminar")
def _eliminar_grupo_distrito_seguro(grupo_id: int, distrito_id: int):
    with obtener_conexion() as con:
        cur = con.cursor()
        try:
            cur.execute("""
                UPDATE grupos
                SET estado = 'INACTIVO'
                WHERE id = %s AND distrito_id = %s AND estado = 'ACTIVO'
            """, (grupo_id, distrito_id))
            if cur.rowcount == 0:
                st.warning("⚠️ No se pudo eliminar. Verifica el distrito o el estado.")
            else:
                con.commit()
                st.success("🗑 Grupo inactivado correctamente.")
                st.experimental_rerun()
        except Exception as e:
            con.rollback()
            st.error(f"Error al eliminar el grupo: {e}")

