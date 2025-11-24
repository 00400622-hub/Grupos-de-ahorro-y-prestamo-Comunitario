# modulos/directiva/panel.py

import datetime as dt
import calendar
import streamlit as st

from modulos.config.conexion import fetch_one, fetch_all, execute
from modulos.auth.rbac import has_role, get_user


# -------------------------------------------------------
# Helpers generales
# -------------------------------------------------------
def _obtener_info_directiva_actual() -> dict | None:
    """
    Devuelve la fila de la directiva asociada al usuario en sesión
    (se busca por el DUI del usuario) junto con info del grupo.
    """
    user = get_user()
    if not user:
        return None

    dui = (user.get("DUI") or "").strip()
    if not dui:
        return None

    sql = """
    SELECT 
        d.Id_directiva,
        d.Nombre,
        d.DUI,
        d.Id_grupo,
        g.Nombre AS Nombre_grupo
    FROM directiva d
    JOIN grupos g ON g.Id_grupo = d.Id_grupo
    WHERE d.DUI = %s
    LIMIT 1
    """
    return fetch_one(sql, (dui,))


def _obtener_reglamento_por_grupo(id_grupo: int) -> dict | None:
    sql = """
    SELECT *
    FROM reglamento_grupo
    WHERE Id_grupo = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo,))


def _obtener_miembros_grupo(id_grupo: int):
    sql = """
    SELECT 
        Id_miembro,
        Nombre,
        DUI,
        Cargo,
        Sexo
    FROM miembros
    WHERE Id_grupo = %s
    ORDER BY Cargo, Nombre
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_reuniones_de_grupo(id_grupo: int):
    sql = """
    SELECT
        Id_reunion,
        Fecha,
        Numero_reunion,
        Tema
    FROM reuniones_grupo
    WHERE Id_grupo = %s
    ORDER BY Fecha, Numero_reunion
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_reunion_por_id(id_reunion: int) -> dict | None:
    sql = """
    SELECT Id_reunion, Id_grupo, Fecha, Numero_reunion, Tema
    FROM reuniones_grupo
    WHERE Id_reunion = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_reunion,))


def _sumar_meses(fecha: dt.date, meses: int) -> dt.date:
    """Suma 'meses' meses a una fecha sin usar librerías externas."""
    year = fecha.year + (fecha.month - 1 + meses) // 12
    month = (fecha.month - 1 + meses) % 12 + 1
    day = min(fecha.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def _sumar_float(sql: str, params=()) -> float:
    """Ejecuta un SUM(...) AS suma y devuelve 0.0 si es NULL."""
    fila = fetch_one(sql, params)
    if not fila or fila.get("suma") is None:
        return 0.0
    try:
        return float(fila["suma"])
    except Exception:
        return 0.0


# -------------------------------------------------------
# Helpers de Caja
# -------------------------------------------------------
def _obtener_caja_por_reunion(id_grupo: int, id_reunion: int) -> dict | None:
    sql = """
    SELECT *
    FROM caja_reunion
    WHERE Id_grupo = %s AND Id_reunion = %s
    LIMIT 1
    """
    return fetch_one(sql, (id_grupo, id_reunion))


def _obtener_saldo_cierre_anterior(id_grupo: int, fecha_reunion: dt.date) -> float:
    """
    Devuelve el saldo de cierre de la caja de la reunión inmediatamente anterior
    (por fecha) para el grupo. Si no hay, devuelve 0.
    """
    sql = """
    SELECT cr.Saldo_cierre AS saldo
    FROM caja_reunion cr
    JOIN reuniones_grupo rg ON rg.Id_reunion = cr.Id_reunion
    WHERE cr.Id_grupo = %s
      AND rg.Fecha < %s
    ORDER BY rg.Fecha DESC, rg.Numero_reunion DESC
    LIMIT 1
    """
    fila = fetch_one(sql, (id_grupo, fecha_reunion))
    if fila and fila.get("saldo") is not None:
        try:
            return float(fila["saldo"])
        except Exception:
            return 0.0
    return 0.0


def _obtener_saldo_caja_actual(id_grupo: int) -> float:
    """
    Devuelve el último saldo de cierre registrado en caja_reunion para el grupo.
    Se usa como disponibilidad de caja para nuevos préstamos.
    """
    sql = """
    SELECT Saldo_cierre AS saldo
    FROM caja_reunion
    WHERE Id_grupo = %s
    ORDER BY Id_caja DESC
    LIMIT 1
    """
    fila = fetch_one(sql, (id_grupo,))
    if fila and fila.get("saldo") is not None:
        try:
            return float(fila["saldo"])
        except Exception:
            return 0.0
    return 0.0


# -------------------------------------------------------
# Helpers de Cierre de ciclo
# -------------------------------------------------------
def _tiene_prestamos_pendientes(id_grupo: int) -> bool:
    """
    True si existe al menos un préstamo del grupo con saldo pendiente.
    """
    sql = """
    SELECT 
        p.Id_prestamo,
        p.Total_pagar,
        COALESCE(SUM(pp.Capital_pagado + pp.Interes_pagado), 0) AS Pagado
    FROM prestamos_miembro p
    LEFT JOIN pagos_prestamo pp ON pp.Id_prestamo = p.Id_prestamo
    WHERE p.Id_grupo = %s
    GROUP BY p.Id_prestamo, p.Total_pagar
    HAVING Pagado < p.Total_pagar - 0.01
    """
    filas = fetch_all(sql, (id_grupo,))
    return bool(filas)


def _tiene_multas_pendientes(id_grupo: int) -> bool:
    """
    True si hay multas NO pagadas en el grupo.
    """
    sql = """
    SELECT COUNT(*) AS c
    FROM multas_miembro
    WHERE Id_grupo = %s AND Pagada = 0
    """
    fila = fetch_one(sql, (id_grupo,))
    return bool(fila and fila.get("c", 0) > 0)


def _obtener_cierres_ciclo_grupo(id_grupo: int):
    """
    Devuelve todos los cierres de ciclo del grupo (historial).
    """
    sql = """
    SELECT 
        Id_cierre,
        Id_grupo,
        Fecha_cierre,
        Fecha_inicio_ciclo,
        Fecha_fin_ciclo,
        Total_ahorro_grupo,
        Porcion_fondo_grupo
    FROM cierres_ciclo
    WHERE Id_grupo = %s
    ORDER BY Fecha_cierre DESC, Id_cierre DESC
    """
    return fetch_all(sql, (id_grupo,))


def _obtener_detalle_cierre(id_cierre: int):
    """
    Devuelve el detalle por miembro de un cierre de ciclo.
    """
    sql = """
    SELECT 
        ccm.Id_cierre_miembro,
        ccm.Id_miembro,
        m.Nombre,
        m.Cargo,
        ccm.Total_ahorrado_ciclo,
        ccm.Total_correspondiente,
        ccm.Retiro_cierre,
        ccm.Saldo_siguiente_ciclo
    FROM cierres_ciclo_miembros ccm
    JOIN miembros m ON m.Id_miembro = ccm.Id_miembro
    WHERE ccm.Id_cierre = %s
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_cierre,))


def _obtener_totales_ahorro_ciclo(
    id_grupo: int,
    fecha_inicio: dt.date,
    fecha_fin: dt.date,
):
    """
    Calcula, para cada miembro, el total ahorrado durante el ciclo
    [fecha_inicio, fecha_fin].
    """
    sql = """
    SELECT 
        m.Id_miembro,
        m.Nombre,
        m.Cargo,
        COALESCE(SUM(
            COALESCE(a.Ahorro, 0)
          + COALESCE(a.Otras_actividades, 0)
          - COALESCE(a.Retiros, 0)
        ), 0) AS Total_ahorrado
    FROM miembros m
    LEFT JOIN ahorros_miembros a
        ON a.Id_miembro = m.Id_miembro
       AND a.Id_grupo = m.Id_grupo
    LEFT JOIN reuniones_grupo rg
        ON rg.Id_reunion = a.Id_reunion
    WHERE m.Id_grupo = %s
      AND (rg.Fecha IS NULL OR (rg.Fecha BETWEEN %s AND %s))
    GROUP BY m.Id_miembro, m.Nombre, m.Cargo
    ORDER BY m.Cargo, m.Nombre
    """
    return fetch_all(sql, (id_grupo, fecha_inicio, fecha_fin))


def _actualizar_saldo_final_ultimo_ahorro(
    id_grupo: int, id_miembro: int, nuevo_saldo: float
):
    """
    Actualiza el Saldo_final del último registro de ahorros_miembros
    del miembro (para que sea saldo inicial del siguiente ciclo).
    """
    sql_sel = """
    SELECT Id_ahorro
    FROM ahorros_miembros
    WHERE Id_grupo = %s AND Id_miembro = %s
    ORDER BY Id_reunion DESC, Id_ahorro DESC
    LIMIT 1
    """
    f
