
# modulos/promotora/grupos.py
import datetime as dt
import mysql.connector
import streamlit as st

from modulos.config.conexion import fetch_all, fetch_one, execute
from modulos.auth.rbac import require_auth, has_role, get_user
from modulos.promotora.directiva import crear_directiva_panel


# ---------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------
def _promotora_actual_por_dui(dui: str) -> dict | None:
"""
Devuelve la fila de la tabla 'promotora' que coincide con el DUI.
"""
return fetch_one(
"SELECT Id_promotora, Nombre, DUI FROM promotora WHERE DUI = %s LIMIT 1",
(dui,),
)


def _grupos_de_promotora_por_dui(dui_prom: str):
"""
Grupos donde el DUI de la promotora aparece en DUIs_promotoras.
"""
sql = """
SELECT g.Id_grupo,
g.Nombre,
d.Nombre AS Distrito,
g.Estado,
g.Creado_en,
g.DUIs_promotoras
FROM grupos g
JOIN distritos d ON d.Id_distrito = g.Id_distrito
WHERE FIND_IN_SET(%s, g.DUIs_promotoras)
ORDER BY g.Id_grupo
"""
return fetch_all(sql, (dui_prom,))


# ---------------------------------------------------
# Pestaña: Crear grupo
# ---------------------------------------------------
def _crear_grupo_tab(dui_prom: str, promotora_row: dict):
st.subheader("Crear grupo")

st.caption(
f"Promotora principal: **{promotora_row['Nombre']}** "
f"— DUI: **{promotora_row['DUI']}**"
)

nombre_grupo = st.text_input("Nombre del grupo")

distritos = fetch_all(
"SELECT Id_distrito, Nombre FROM distritos ORDER BY Nombre"
)
map_distritos = {d["Nombre"]: d["Id_distrito"] for d in distritos}
nombre_distrito_sel = st.selectbox(
"Distrito",
list(map_distritos.keys()) if map_distritos else [],
)
id_distrito_sel = map_distritos.get(nombre_distrito_sel)

if st.button("Guardar grupo"):
if not (nombre_grupo.strip() and id_distrito_sel):
st.warning("Debes ingresar el nombre del grupo y seleccionar un distrito.")
return

hoy = dt.date.today()
try:
# Insertamos el grupo con la promotora principal y su DUI
execute(
"""
INSERT INTO grupos
(Nombre, Id_distrito, Estado, Creado_en, DUIs_promotoras, Id_promotora)
VALUES (%s, %s, %s, %s, %s, %s)
""",
(
nombre_grupo.strip(),
id_distrito_sel,
"ACTIVO",
hoy,
dui_prom, # DUIs_promotoras inicial = DUI de la promotora
promotora_row["Id_promotora"], # Id_promotora principal
),
)
st.success("Grupo creado correctamente.")
st.experimental_rerun()
except mysql.connector.Error as err:
st.error(
f"Error al crear el grupo en la base de datos: "
f"{err.errno} - {err.msg}"
)


# ---------------------------------------------------
# Pestaña: Mis grupos
# - listado
# - eliminar grupo
# - gestionar promotoras (agregar/quitar DUIs)
# ---------------------------------------------------
def _mis_grupos_tab(dui_prom: str):
st.subheader("Mis grupos")

grupos = _grupos_de_promotora_por_dui(dui_prom)

if not grupos:
st.info("Todavía no tienes grupos asignados.")
return

# ----- Listado -----
st.write("### Listado de grupos donde tu DUI aparece como promotora responsable.")
st.table(grupos)

st.markdown("---")

# ----- Eliminar grupo -----
st.write("### Eliminar grupo")

opciones_grupos = {
f'{g["Id_grupo"]} - {g["Nombre"]} ({g["Distrito"]})': g["Id_grupo"]
for g in grupos
}

etiqueta_grupo_del = st.selectbox(
"Selecciona el grupo a eliminar",
list(opciones_grupos.keys()),
key="sel_grupo_eliminar",
)
id_grupo_del = opciones_grupos[etiqueta_grupo_del]

confirmar = st.checkbox(
"Confirmo que deseo eliminar este grupo (esta acción no se puede deshacer).",
key="chk_confirma_eliminar_grupo",
)

if st.button("Eliminar grupo"):
if not confirmar:
st.warning("Debes marcar la casilla de confirmación para eliminar el grupo.")
else:
try:
execute("DELETE FROM grupos WHERE Id_grupo = %s", (id_grupo_del,))
st.success("Grupo eliminado correctamente.")
st.experimental_rerun()
except mysql.connector.Error as err:
st.error(
f"Error al eliminar el grupo: {err.errno} - {err.msg}"
)

st.markdown("---")

# ----- Gestionar promotoras (DUIs_promotoras) -----
st.write("### Gestionar promotoras asignadas a un grupo")

etiqueta_grupo_gest = st.selectbox(
"Selecciona el grupo a gestionar",
list(opciones_grupos.keys()),
key="sel_grupo_gestion",
)
id_grupo_gest = opciones_grupos[etiqueta_grupo_gest]

grupo_sel = next(g for g in grupos if g["Id_grupo"] == id_grupo_gest)
duis_actuales = [
d.strip()
for d in (grupo_sel["DUIs_promotoras"] or "").split(",")
if d.strip()
]

st.caption(
"DUIs asignados actualmente: "
+ (", ".join(duis_actuales) if duis_actuales else "(ninguno)")
)

# Obtener todas las promotoras para poder agregarlas o quitarlas
promotoras = fetch_all("SELECT Nombre, DUI FROM promotora ORDER BY Nombre")
opciones_duis = [p["DUI"] for p in promotoras]

# Seleccionar DUIs a quitar
duis_quitar = st.multiselect(
"Selecciona los DUIs que deseas quitar del grupo",
options=duis_actuales,
key="multiquitar_duis",
)

# Seleccionar DUIs a agregar
duis_agregar = st.multiselect(
"Selecciona los DUIs que deseas agregar al grupo",
options=[d for d in opciones_duis if d not in duis_actuales],
key="multiagregar_duis",
)

if st.button("Actualizar promotoras del grupo"):
nuevos = set(duis_actuales)
for d in duis_quitar:
nuevos.discard(d)
for d in duis_agregar:
if d:
nuevos.add(d)

nueva_cadena = ",".join(sorted(nuevos)) if nuevos else None

try:
execute(
"UPDATE grupos SET DUIs_promotoras = %s WHERE Id_grupo = %s",
(nueva_cadena, id_grupo_gest),
)
st.success("Promotoras del grupo actualizadas correctamente.")
st.experimental_rerun()
except mysql.connector.Error as err:
st.error(
f"Error al actualizar las promotoras del grupo: {err.errno} - {err.msg}"
)


# ---------------------------------------------------
# Panel principal de PROMOTORA
# ---------------------------------------------------
@require_auth
@has_role("PROMOTORA")
def promotora_panel():
"""
Panel principal para el rol PROMOTORA.
Contiene pestañas:
- Crear grupo
- Mis grupos (incluye eliminar / gestionar promotoras)
- Crear Directiva (usa crear_directiva_panel de modulos.promotora.directiva)
- Reportes (pendiente)
"""
user = get_user()
dui_prom = (user.get("DUI") or "").strip()

promotora_row = _promotora_actual_por_dui(dui_prom)
if not promotora_row:
st.error(
"No se encontró una promotora asociada a este usuario. "
"Verifica que el DUI del usuario exista en la tabla 'promotora'."
)
return

st.title("Panel de Promotora")

pestañas = st.tabs(["Crear grupo", "Mis grupos", "Crear Directiva", "Reportes"])

# Pestaña 0: Crear grupo
with pestañas[0]:
_crear_grupo_tab(dui_prom, promotora_row)

# Pestaña 1: Mis grupos
with pestañas[1]:
_mis_grupos_tab(dui_prom)

# Pestaña 2: Crear Directiva
# IMPORTANTE: crear_directiva_panel NO recibe parámetros
with pestañas[2]:
crear_directiva_panel()

# Pestaña 3: Reportes
with pestañas[3]:
st.info("Aquí se implementarán los reportes de la promotora.")
