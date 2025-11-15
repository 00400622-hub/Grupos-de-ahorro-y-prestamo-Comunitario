def _crud_usuarios():
    _titulo("Usuarios")
    st.caption("Crear y eliminar usuarios seleccionando el rol desde la tabla 'rol'.")

    # --------- FORMULARIO PARA CREAR USUARIO --------- #
    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY `Tipo de rol`")
    opciones = {r["Tipo de rol"]: r["Id_rol"] for r in roles}

    with st.form("form_usuario", clear_on_submit=True):
        nombre = st.text_input("Nombre del usuario")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña (por ahora sin cifrar)")
        rol_sel = st.selectbox(
            "Tipo de rol",
            list(opciones.keys())
        ) if opciones else None
        enviar = st.form_submit_button("Crear usuario")

        if enviar:
            if not (nombre and dui and contr and rol_sel):
                st.warning("Complete todos los campos.")
            else:
                id_rol = opciones[rol_sel]
                # evitar DUI duplicado
                existe = fetch_one(
                    "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
                    (dui,)
                )
                if existe:
                    st.error("Ya existe un usuario con ese DUI.")
                else:
                    try:
                        sql = """
                            INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                            VALUES (%s, %s, %s, %s)
                        """
                        _, uid = execute(sql, (nombre, dui, contr, id_rol))
                        st.success(f"Usuario creado con Id_usuario={uid} y rol={rol_sel}.")
                    except mysql.connector.IntegrityError as e:
                        st.error(f"Error de integridad MySQL [{e.errno}]: {e.msg}")
                    except Exception as e:
                        st.exception(e)

    st.markdown("---")

    # --------- LISTADO DE USUARIOS --------- #
    usuarios = fetch_all("""
        SELECT u.Id_usuario, u.Nombre, u.DUI, r.`Tipo de rol` AS Rol
        FROM Usuario u
        LEFT JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
    """)

    st.subheader("Lista de usuarios")
    if usuarios:
        st.dataframe(usuarios, use_container_width=True)
    else:
        st.info("No hay usuarios registrados aún.")
        return  # si no hay usuarios, no tiene sentido mostrar la sección de eliminar

    # --------- FORMULARIO PARA ELIMINAR USUARIO --------- #
    st.markdown("### Eliminar usuario")

    opciones_usuario = {
        f"{u['Id_usuario']} - {u['Nombre']} ({u['DUI']}) [{u['Rol'] or 'SIN ROL'}]": u["Id_usuario"]
        for u in usuarios
    }

    with st.form("form_eliminar_usuario"):
        sel = st.selectbox(
            "Seleccione el usuario a eliminar",
            list(opciones_usuario.keys())
        )
        confirmar = st.checkbox(
            "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
        )
        eliminar = st.form_submit_button("Eliminar usuario", type="secondary")

        if eliminar:
            if not confirmar:
                st.warning("Debes marcar la casilla de confirmación.")
            else:
                id_sel = opciones_usuario[sel]
                try:
                    sql = "DELETE FROM Usuario WHERE Id_usuario = %s"
                    filas, _ = execute(sql, (id_sel,))
                    if filas > 0:
                        st.success(f"Usuario {sel} eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("No se encontró el usuario seleccionado.")
                except mysql.connector.IntegrityError as e:
                    st.error(
                        "No se puede eliminar el usuario porque está siendo usado "
                        "por otros registros. Detalle MySQL "
                        f"[{e.errno}]: {e.msg}"
                    )
                except Exception as e:
                    st.exception(e)
