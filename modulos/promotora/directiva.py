# modulos/promotora/directiva.py

import streamlit as st
from datetime import date
from mysql.connector.errors import IntegrityError

from modulos.config.conexion import fetch_all, fetch_one, execute


def _normalizar_dui(txt: str) -> str:
    """Deja solo dígitos en el DUI."""
    return "".join(ch for ch in (txt or "") if ch.isdigit())


def _obtener_id_rol_directiva():
    """
    Devuelve el Id_rol de la tabla 'rol' para el tipo DIRECTIVA.
    Asegúrate de tener un registro en rol con 'Tipo de rol' = 'DIRECTIVA'.
    """
    fila = fetch_one("SELECT Id_rol FROM rol WHERE `Tipo de rol` = 'DIRECTIVA'")
    if not fila:
        st.error(
            "No se encontró el rol 'DIRECTIVA' en la tabla 'rol'. "
            "Crea ese rol en phpMyAdmin primero."
        )
        st.stop()
    return fila["Id_rol"]


def crear_directiva_panel(usuario, id_promotora: int):
    """
    Panel para que la promotora cree usuarios de DIRECTIVA.

    Requisitos:
    - Solo se listan grupos cuyo Id_promotora = id_promotora.
    - Se crea:
        1) Usuario en tabla 'usuario' con rol DIRECTIVA.
        2) Registro en tabla 'directiva' (Id_grupo, Nombre, DUI, Creado_en).
    """
    st.subheader("Crear usuario de Directiva para un grupo")

    # ------------------------------------------------------------------
    # 1. Obtener grupos de esta promotora
    # ------------------------------------------------------------------
    grupos = fetch_all(
        """
        SELECT Id_grupo, Nombre
        FROM grupos
        WHERE Id_promotora = %s
        ORDER BY Nombre ASC
        """,
        (id_promotora,),
    )

    if not grupos:
        st.info("Todavía no tienes grupos creados. Crea un grupo antes de asignar una directiva.")
        return

    opciones = {
        f'{g["Id_grupo"]} - {g["Nombre"]}': g["Id_grupo"] for g in grupos
    }

    # ------------------------------------------------------------------
    # 2. Formulario
    # ------------------------------------------------------------------
    with st.form("form_crear_directiva"):
        nombre = st.text_input("Nombre de la directiva")
        dui_in = st.text_input("DUI de la directiva (con o sin guion)")
        password = st.text_input("Contraseña inicial", type="password")
        etiqueta = st.selectbox("Grupo al que pertenece", list(opciones.keys()))
        enviado = st.form_submit_button("Crear usuario de directiva")

    if not enviado:
        st.info("Complete los campos y presione 'Crear usuario de directiva'.")
        return

    nombre = nombre.strip()
    dui = _normalizar_dui(dui_in)

    if not nombre or not dui or not password:
        st.warning("Todos los campos son obligatorios.")
        return

    if len(dui) != 9:
        st.warning("El DUI debe tener 9 dígitos (sin contar el guion).")
        return

    id_grupo = opciones[etiqueta]

    # ------------------------------------------------------------------
    # 3. Verificar si ya existe una directiva para ese grupo (opcional)
    # ------------------------------------------------------------------
    existente = fetch_one(
        "SELECT Id_directiva FROM directiva WHERE Id_grupo = %s",
        (id_grupo,),
    )
    if existente:
        st.warning("Este grupo ya tiene una directiva registrada.")
        return

    # ------------------------------------------------------------------
    # 4. Obtener Id_rol para DIRECTIVA
    # ------------------------------------------------------------------
    id_rol_directiva = _obtener_id_rol_directiva()

    # ------------------------------------------------------------------
    # 5. Crear usuario + registro en tabla directiva
    # ------------------------------------------------------------------
    hoy = date.today()

    try:
        # 5.1 Usuario
        _, id_usuario = execute(
            """
            INSERT INTO usuario (Nombre, DUI, Contraseña, Id_rol)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, dui, password, id_rol_directiva),
        )

        # 5.2 Registro directiva
        execute(
            """
            INSERT INTO directiva (Id_grupo, Nombre, DUI, Creado_en, Id_usuario)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_grupo, nombre, dui, hoy, id_usuario),
        )

        st.success(
            f"✅ Directiva creada correctamente para el grupo {etiqueta}. "
            f"El usuario podrá iniciar sesión con el DUI {dui}."
        )

    except IntegrityError as e:
        st.error(
            "No se pudo crear la directiva. "
            "Verifica que el DUI no esté repetido en la tabla 'usuario' o 'directiva'."
        )
