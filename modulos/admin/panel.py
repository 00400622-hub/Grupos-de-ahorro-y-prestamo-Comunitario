# modulos/admin/panel.py

import streamlit as st
import pandas as pd  # 👈 Para armar los DataFrames de las gráficas

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role


# ==========================
#  Helpers para REPORTES
# ==========================

def _obtener_ciclos_disponibles_para_grupo(id_grupo: int):
    """
    Devuelve una lista de ciclos disponibles para el grupo, combinando:
    - Cierres de ciclo ya registrados en 'cierres_ciclo'
    - Ciclo actual definido en reglamento_grupo (si tiene fechas)
    Cada elemento es:
    {
        "label": str,
        "fecha_inicio": date,
        "fecha_fin": date,
        "tipo": "cierre" | "actual"
    }
    """
    ciclos = []

    # 1) Cierres de ciclo históricos
    cierres = fetch_all(
        """
        SELECT 
            Id_cierre,
            Fecha_cierre,
            Fecha_inicio_ciclo,
            Fecha_fin_ciclo,
            Total_ahorro_grupo
        FROM cierres_ciclo
        WHERE Id_grupo = %s
        ORDER BY Fecha_fin_ciclo DESC, Fecha_cierre DESC
        """,
        (id_grupo,),
    )

    for c in cierres or []:
        fi = c["Fecha_inicio_ciclo"]
        ff = c["Fecha_fin_ciclo"]
        fc = c["Fecha_cierre"]
        total = float(c.get("Total_ahorro_grupo") or 0.0)
        label = (
            f"Cierre del {fi} al {ff} "
            f"(Fecha cierre: {fc}, Total ahorro grupo: ${total:.2f})"
        )
        ciclos.append(
            {
                "label": label,
                "fecha_inicio": fi,
                "fecha_fin": ff,
                "tipo": "cierre",
            }
        )

    # 2) Ciclo actual desde reglamento
    reglamento = fetch_one(
        """
        SELECT Fecha_inicio_ciclo, Fecha_fin_ciclo
        FROM reglamento_grupo
        WHERE Id_grupo = %s
        LIMIT 1
        """,
        (id_grupo,),
    )
    if reglamento:
        fi = reglamento.get("Fecha_inicio_ciclo")
        ff = reglamento.get("Fecha_fin_ciclo")
        if fi and ff:
            label = f"Ciclo actual (según reglamento): del {fi} al {ff}"
            ciclos.append(
                {
                    "label": label,
                    "fecha_inicio": fi,
                    "fecha_fin": ff,
                    "tipo": "actual",
                }
            )

    return ciclos


def _obtener_movimientos_caja_por_ciclo(id_grupo: int, fecha_ini, fecha_fin):
    """
    Devuelve las filas de caja_reunion del grupo, unidas a reuniones_grupo
    para obtener la fecha de la reunión, filtradas entre fecha_ini y fecha_fin.
    Cada fila incluye:
      - Fecha
      - Multas, Ahorros, Otras_actividades, Pagos_prestamos, Otros_ingresos
      - Retiros_ahorros, Desembolsos_prestamos, Otros_gastos
    """
    filas = fetch_all(
        """
        SELECT 
            rg.Fecha,
            cr.Multas,
            cr.Ahorros,
            cr.Otras_actividades,
            cr.Pagos_prestamos,
            cr.Otros_ingresos,
            cr.Retiros_ahorros,
            cr.Desembolsos_prestamos,
            cr.Otros_gastos
        FROM caja_reunion cr
        JOIN reuniones_grupo rg ON rg.Id_reunion = cr.Id_reunion
        WHERE cr.Id_grupo = %s
          AND rg.Fecha BETWEEN %s AND %s
        ORDER BY rg.Fecha ASC
        """,
        (id_grupo, fecha_ini, fecha_fin),
    )
    return filas or []


def _seccion_reportes_admin():
    st.subheader("Reportes de grupos por distrito")

    # 1) Seleccionar distrito
    distritos = fetch_all(
        """
        SELECT Id_distrito, Nombre
        FROM distritos
        ORDER BY Nombre ASC
        """
    )
    if not distritos:
        st.info("No hay distritos registrados. Primero crea distritos.")
        return

    mapa_distritos = {f'{d["Nombre"]} (Id {d["Id_distrito"]})': d for d in distritos}

    etiqueta_dist = st.selectbox(
        "Selecciona un distrito",
        list(mapa_distritos.keys()),
        key="rep_admin_distrito",
    )
    dist_sel = mapa_distritos.get(etiqueta_dist)
    if not dist_sel:
        st.info("Selecciona un distrito válido.")
        return

    id_distrito = dist_sel["Id_distrito"]

    # 2) Seleccionar grupo dentro del distrito
    grupos = fetch_all(
        """
        SELECT Id_grupo, Nombre
        FROM grupos
        WHERE Id_distrito = %s
        ORDER BY Nombre ASC
        """,
        (id_distrito,),
    )

    if not grupos:
        st.info(
            "Este distrito todavía no tiene grupos registrados. "
            "Ve a la pestaña de Promotora para crear grupos."
        )
        return

    mapa_grupos = {
        f'{g["Nombre"]} (Id_grupo {g["Id_grupo"]})': g for g in grupos
    }

    etiqueta_grupo = st.selectbox(
        "Selecciona el grupo para ver sus reportes",
        list(mapa_grupos.keys()),
        key="rep_admin_grupo",
    )
    grupo_sel = mapa_grupos.get(etiqueta_grupo)
    if not grupo_sel:
        st.info("Selecciona un grupo válido.")
        return

    id_grupo = grupo_sel["Id_grupo"]

    st.markdown(
        f"Has seleccionado el grupo **{grupo_sel['Nombre']}** "
        f"(Id_grupo {id_grupo}) del distrito **{dist_sel['Nombre']}**."
    )

    # 3) Seleccionar ciclo (cierres anteriores o ciclo actual)
    ciclos = _obtener_ciclos_disponibles_para_grupo(id_grupo)
    if not ciclos:
        st.info(
            "Este grupo todavía no tiene cierres de ciclo ni ciclo configurado en el reglamento. "
            "Primero define el reglamento y/o realiza cierres desde el panel de Directiva."
        )
        return

    opciones_ciclos = {c["label"]: c for c in ciclos}

    etiqueta_ciclo = st.selectbox(
        "Selecciona el ciclo a analizar",
        list(opciones_ciclos.keys()),
        key="rep_admin_ciclo",
    )
    ciclo_sel = opciones_ciclos.get(etiqueta_ciclo)
    if not ciclo_sel:
        st.info("Selecciona un ciclo válido.")
        return

    fi = ciclo_sel["fecha_inicio"]
    ff = ciclo_sel["fecha_fin"]

    st.markdown(
        f"Mostrando información de caja para el periodo **{fi}** a **{ff}**."
    )

    # 4) Obtener movimientos de caja para ese ciclo
    movimientos = _obtener_movimientos_caja_por_ciclo(id_grupo, fi, ff)
    if not movimientos:
        st.info(
            "No se encontraron registros de caja para este grupo en el rango seleccionado. "
            "Verifica que la directiva haya registrado la caja en cada reunión."
        )
        return

    # 5) Preparar datos para las gráficas
    fechas = []
    ingresos = []
    egresos = []
    saldos_acum = []

    saldo_acumulado = 0.0

    for fila in movimientos:
        f = fila["Fecha"]
        # Por si viene como datetime, lo convertimos a .date()
        try:
            fecha_simple = f.date() if hasattr(f, "date") else f
        except Exception:
            fecha_simple = f

        multas = float(fila.get("Multas") or 0.0)
        ahorros = float(fila.get("Ahorros") or 0.0)
        otras_act = float(fila.get("Otras_actividades") or 0.0)
        pagos_prest = float(fila.get("Pagos_prestamos") or 0.0)
        otros_ing = float(fila.get("Otros_ingresos") or 0.0)

        retiros = float(fila.get("Retiros_ahorros") or 0.0)
        desembolsos = float(fila.get("Desembolsos_prestamos") or 0.0)
        otros_gastos = float(fila.get("Otros_gastos") or 0.0)

        ingreso = multas + ahorros + otras_act + pagos_prest + otros_ing
        egreso = retiros + desembolsos + otros_gastos

        saldo_acumulado += ingreso - egreso

        fechas.append(fecha_simple)
        ingresos.append(ingreso)
        egresos.append(egreso)
        saldos_acum.append(saldo_acumulado)

    df = pd.DataFrame(
        {
            "Fecha": fechas,
            "Ingresos": ingresos,
            "Egresos": egresos,
            "Saldo_acumulado": saldos_acum,
        }
    )

    st.markdown("### Gráfico de ingresos del grupo (por reunión en el ciclo)")
    st.line_chart(df, x="Fecha", y="Ingresos")

    st.markdown("### Gráfico de egresos del grupo (por reunión en el ciclo)")
    st.line_chart(df, x="Fecha", y="Egresos")

    st.markdown("### Consolidado del ciclo (Ingresos, Egresos y Saldo acumulado)")
    st.line_chart(df, x="Fecha", y=["Ingresos", "Egresos", "Saldo_acumulado"])


# ==========================
#  CRUD DISTRITOS
# ==========================

def _crud_distritos():
    st.subheader("Distritos")

    # ------- Listado -------
    try:
        distritos = fetch_all(
            """
            SELECT Id_distrito, Nombre
            FROM distritos
            ORDER BY Id_distrito ASC
            """
        )
    except Exception as e:
        st.error(
            "Error al consultar la tabla 'distritos'. "
            "Revisa nombres de tabla/columnas en phpMyAdmin."
        )
        st.code(str(e))
        return

    st.write("### Lista de distritos")
    if distritos:
        st.table(distritos)
    else:
        st.info("No hay distritos registrados.")

    # ------- Crear distrito -------
    st.write("---")
    st.write("### Crear nuevo distrito")

    with st.form("form_crear_distrito"):
        nombre = st.text_input("Nombre del distrito")
        enviar = st.form_submit_button("Crear distrito")

    if enviar:
        if not nombre.strip():
            st.warning("Ingrese un nombre válido.")
        else:
            try:
                execute(
                    "INSERT INTO distritos (Nombre) VALUES (%s)",
                    (nombre.strip(),),
                )
                st.success("Distrito creado correctamente.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo crear el distrito.")
                st.code(str(e))

    # ------- Eliminar distrito -------
    st.write("---")
    st.write("### Eliminar distrito")

    if not distritos:
        st.info("No hay distritos para eliminar.")
        return

    opciones = {
        f'{d["Id_distrito"]} - {d["Nombre"]}': d["Id_distrito"]
        for d in distritos
    }

    etiqueta = st.selectbox(
        "Seleccione el distrito a eliminar", list(opciones.keys())
    )
    id_sel = opciones[etiqueta]
    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este distrito (no se puede deshacer)."
    )

    if st.button("Eliminar distrito"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            try:
                execute("DELETE FROM distritos WHERE Id_distrito = %s", (id_sel,))
                st.success("Distrito eliminado correctamente.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo eliminar el distrito.")
                st.code(str(e))


# ==========================
#  Sincronizar promotora con usuario
# ==========================

def _sync_promotora_from_usuario(uid: int):
    """
    Si el usuario tiene rol PROMOTORA, asegura que exista la fila
    correspondiente en la tabla 'promotora'.
    """
    usuario = fetch_one(
        """
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               r.`Tipo de rol` AS RolNombre
        FROM Usuario u
        JOIN rol r ON r.Id_rol = u.Id_rol
        WHERE u.Id_usuario = %s
        """,
        (uid,),
    )

    if not usuario:
        return

    rol = (usuario["RolNombre"] or "").upper().strip()
    if rol != "PROMOTORA":
        # Solo sincronizamos si el rol es PROMOTORA
        return

    # ¿Ya existe en promotora?
    existe = fetch_one(
        "SELECT Id_promotora FROM promotora WHERE DUI = %s LIMIT 1",
        (usuario["DUI"],),
    )
    if existe:
        return

    # Crear registro en promotora
    execute(
        "INSERT INTO promotora (Nombre, DUI) VALUES (%s, %s)",
        (usuario["Nombre"], usuario["DUI"]),
    )


# ==========================
#  CRUD USUARIOS
# ==========================

def _crud_usuarios():
    st.subheader("Usuarios")

    # ------- Listado -------
    usuarios = fetch_all(
        """
        SELECT u.Id_usuario,
               u.Nombre,
               u.DUI,
               r.`Tipo de rol` AS Rol,
               u.Id_rol
        FROM Usuario u
        JOIN rol r ON r.Id_rol = u.Id_rol
        ORDER BY u.Id_usuario ASC
        """
    )

    st.write("### Lista de usuarios")
    if usuarios:
        st.table(usuarios)
    else:
        st.info("No hay usuarios registrados.")

    # ------- Crear usuario -------
    st.write("---")
    st.write("### Crear usuario")

    roles = fetch_all("SELECT Id_rol, `Tipo de rol` FROM rol ORDER BY Id_rol")
    mapa_roles = {r["`Tipo de rol`"] if "`Tipo de rol`" in r else r["Tipo de rol"]: r["Id_rol"] for r in roles} if roles else {}

    # Normalizamos claves del diccionario para evitar problema del nombre del campo
    if roles:
        mapa_roles = {}
        for r in roles:
            # el alias puede venir como 'Tipo de rol' o '`Tipo de rol`' según fetch_all
            tipo = r.get("Tipo de rol", r.get("`Tipo de rol`"))
            mapa_roles[tipo] = r["Id_rol"]

    with st.form("form_crear_usuario"):
        nombre = st.text_input("Nombre completo")
        dui = st.text_input("DUI")
        contr = st.text_input("Contraseña", type="password")
        rol_nombre = (
            st.selectbox("Rol", list(mapa_roles.keys()))
            if mapa_roles
            else None
        )
        enviar = st.form_submit_button("Crear usuario")

    if enviar:
        if not (nombre.strip() and dui.strip() and contr.strip()):
            st.warning("Complete todos los campos.")
        elif not rol_nombre:
            st.warning("Debe existir al menos un rol en la tabla 'rol'.")
        else:
            id_rol = mapa_roles[rol_nombre]
            try:
                uid = execute(
                    """
                    INSERT INTO Usuario (Nombre, DUI, Contraseña, Id_rol)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (nombre.strip(), dui.strip(), contr.strip(), id_rol),
                    return_last_id=True,
                )

                # Si el usuario es PROMOTORA, lo sincronizamos en la tabla promotora
                _sync_promotora_from_usuario(uid)

                st.success(f"Usuario creado correctamente (Id_usuario={uid}).")
                st.rerun()
            except Exception as e:
                st.error("No se pudo crear el usuario.")
                st.code(str(e))

    # ------- Eliminar usuario -------
    st.write("---")
    st.write("### Eliminar usuario")

    if not usuarios:
        st.info("No hay usuarios para eliminar.")
        return

    opciones = {
        f'{u["Id_usuario"]} - {u["Nombre"]} ({u["DUI"]})': u["Id_usuario"]
        for u in usuarios
    }
    etiqueta = st.selectbox(
        "Seleccione el usuario a eliminar", list(opciones.keys())
    )
    uid_sel = opciones[etiqueta]
    confirmar = st.checkbox(
        "Confirmo que deseo eliminar este usuario (no se puede deshacer)."
    )

    if st.button("Eliminar usuario"):
        if not confirmar:
            st.warning("Debes marcar la casilla de confirmación.")
        else:
            try:
                execute("DELETE FROM Usuario WHERE Id_usuario = %s", (uid_sel,))
                st.success("Usuario eliminado.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo eliminar el usuario.")
                st.code(str(e))


# ==========================
#  PANEL ADMINISTRADOR
# ==========================

@require_auth()
@has_role("ADMINISTRADOR")
def admin_panel():
    st.title("Panel de Administración — SGI GAPC")

    pestañas = st.tabs(["Distritos", "Usuarios", "Reportes"])

    with pestañas[0]:
        _crud_distritos()

    with pestañas[1]:
        _crud_usuarios()

    with pestañas[2]:
        _seccion_reportes_admin()
