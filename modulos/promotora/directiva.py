# modulos/promotora/directiva.py
import datetime as dt
import bcrypt
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user


def _hash_password(plain: str) -> str:
    if not plain:
        return ""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@require_auth
@has_role("PROMOTORA")
def crear_directiva_panel(promotora: dict):
    """
    Panel para que la PROMOTORA cree y gestione directivas de sus grupos.

    - Crear nueva directiva (y su usuario) para un grupo.
    - Ver / eliminar directivas existentes de los grupos donde participa.
    """

    user = get_user()
    dui_prom = (promotora or {}).get("DUI") or (user or {}).get("DUI")

    st.subheader("Crear / gestionar directiva de grupo")

    st.caption(
        f"Promotora: **{promotora.get('Nombre', user.get('Nombre', ''))}** "
        f"— DUI: **{dui_prom or '-'}**"
    )

    # ------------------------------------------------------------------
    # 1) Cargar grupos donde esta promotora aparece en DUIs_promotoras
    # ------------------------------------------------------------------
    grupos = fetch_all(
        """
        SELECT g.Id_grupo, g.Nombre
        FROM grupos g
        WHERE FIND_IN_SET(%s, COALESCE(g.DUIs_promotoras, '')) > 0
        ORDER BY g.Nombre
        """,
        (dui_prom,),
    )

    if not grupos:
        st.info(
            "No se encontraron grupos asociados a tu DUI. "
            "Primero debes crear grupos en la pestaña **Crear grupo**."
        )
        return

    opciones_grupo = {
        f"{g['Id_grupo']} - {g['Nombre']}": g["Id_grupo"] for g in grupos
    }

    # ------------------------------------------------------------------
    # 2) Crear NUEVA directiva para un grupo
    # ------------------------------------------------------------------
    st.markdown("### Crear nueva directiva para un grupo")

    label_grupo_crear = st.selectbox(
        "Selecciona el grupo para la nueva directiva",
        list(opciones_grupo.keys()),
        key="sel_grupo_nueva_directiva",  # ← clave ÚNICA
    )
    id_grupo_crear = opciones_grupo[label_grupo_crear]

    nombre_dir = st.text_input("Nombre de la directiva")
    dui_dir = st.text_input("DUI de la directiva")
    pwd_dir = st.text_input("Contraseña para la cuenta de directiva", type="password")

    if st.button("Guardar nueva directiva para este grupo"):
        if not (nombre_dir.strip() and dui_dir.strip() and pwd_dir.strip()):
            st.warning("Completa **nombre**, **DUI** y **contraseña**.")
        else:
            try:
                hoy = dt.date.today()

                # 1) Rol DIRECTIVA
                rol = fetch_one(
                    "SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA' LIMIT 1"
                )
                if not rol:
                    st.error(
                        "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
                        "Créalo primero."
                    )
                    return
                id_rol_dir = rol["Id_rol"]

                # 2) Usuario (tabla Usuario) para esta directiva
                usuario = fetch_one(
                    "SELECT Id_usuario FROM Usuario WHERE DUI = %s LIMIT 1",
                    (dui_dir.strip(),),
                )

                pwd_hash = _hash_password(pwd_dir.strip())

                if usuario:
                    # Actualizar datos y rol por si cambian
                    execute(
                        """
                        UPDATE Usuario
                           SET Nombre = %s,
                               Contraseña = %s,
                               Id_rol = %s
                         WHERE Id_usuario = %s
                        """,
                        (
                            nombre_dir.strip(),
                            pwd_hash,
                            id_rol_dir,
                            usuario["Id_usuario"],
                        ),
                    )
                    id_usuario = usuario["Id_usuario"]
                else:
                    id_usuario = execute(
                        """
                        INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (nombre_dir.strip(), dui_dir.strip(), pwd_hash, id_rol_dir),
                        return_last_id=True,
                    )

                # 3) Insertar NUEVA directiva para ese grupo
                #    (ya NO hay restricción única por Id_grupo, así que se pueden
                #     tener varias directivas históricas para un mismo grupo)
                execute(
                    """
                    INSERT INTO directiva (Nombre, DUI, Id_grupo, Creado_en)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre_dir.strip(), dui_dir.strip(), id_grupo_crear, hoy),
                )

                st.success(
                    f"Directiva creada correctamente para el grupo {label_grupo_crear}."
                )
                st.experimental_rerun()

            except Exception as e:
                st.error(f"Error al crear la directiva: {e}")

    st.write("---")

    # ------------------------------------------------------------------
    # 3) Gestionar / eliminar directivas existentes
    # ------------------------------------------------------------------
    st.markdown("### Gestionar directivas existentes")

    # Cargar todas las directivas de los grupos donde participa la promotora
    directivas = fetch_all(
        """
        SELECT d.Id_directiva,
               d.Nombre,
               d.DUI,
               d.Id_grupo,
               d.Creado_en,
               g.Nombre AS NombreGrupo
          FROM directiva d
          JOIN grupos g ON g.Id_grupo = d.Id_grupo
         WHERE FIND_IN_SET(%s, COALESCE(g.DUIs_promotoras, '')) > 0
         ORDER BY g.Nombre, d.Creado_en DESC, d.Id_directiva DESC
        """,
        (dui_prom,),
    )

    if not directivas:
        st.info("Aún no hay directivas registradas en tus grupos.")
        return

    # 3.1 Seleccionar grupo para gestionar sus directivas
    opciones_grupo_dir = sorted(
        {f"{d['Id_grupo']} - {d['NombreGrupo']}": d["Id_grupo"] for d in directivas}.items()
    )
    etiquetas_grp = [k for k, _ in opciones_grupo_dir]
    mapa_grp = {k: v for k, v in opciones_grupo_dir}

    label_grupo_gestion = st.selectbox(
        "Selecciona el grupo a gestionar",
        etiquetas_grp,
        key="sel_grupo_gestion_directiva",  # ← otra clave ÚNICA
    )
    id_grupo_gestion = mapa_grp[label_grupo_gestion]

    directivas_del_grupo = [
        d for d in directivas if d["Id_grupo"] == id_grupo_gestion
    ]

    if not directivas_del_grupo:
        st.info("Este grupo aún no tiene directivas registradas.")
        return

    # Mostrar listado
    st.write("**Directivas registradas para este grupo:**")
    st.table(
        [
            {
                "Id_directiva": d["Id_directiva"],
                "Nombre": d["Nombre"],
                "DUI": d["DUI"],
                "Creado_en": d["Creado_en"],
            }
            for d in directivas_del_grupo
        ]
    )

    # 3.2 Seleccionar directiva a eliminar
    opciones_dir = {
        f"{d['Id_directiva']} - {d['Nombre']} ({d['DUI']})": d["Id_directiva"]
        for d in directivas_del_grupo
    }

    label_dir_eliminar = st.selectbox(
        "Selecciona la directiva que deseas eliminar",
        list(opciones_dir.keys()),
        key="sel_directiva_eliminar",  # ← otra clave distinta
    )
    id_dir_eliminar = opciones_dir[label_dir_eliminar]

    confirmar = st.checkbox(
        "Confirmo que deseo eliminar esta directiva (no se puede deshacer)."
    )

    if st.button("Eliminar directiva seleccionada"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            try:
                execute(
                    "DELETE FROM directiva WHERE Id_directiva = %s",
                    (id_dir_eliminar,),
                )
                st.success("Directiva eliminada correctamente.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al eliminar la directiva: {e}")
