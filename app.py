import streamlit as st
from modulos.venta import mostrar_venta
from modulos.compras import mostrar_compras
from modulos.clientes import mostrar_clientes

if "sesion_iniciada" in st.session_state and st.session_state["sesion_iniciada"]:
    seleccion = st.sidebar.selectbox("Selecciona una opción", ["Ventas", "Compras","Clientes"])

    if seleccion == "Ventas":
        mostrar_venta()          # <-- SOLO Ventas aquí
    elif seleccion == "Compras":
        mostrar_compras()        # <-- SOLO Compras aquí
    elif seleccion == "Clientes":
        mostrar_clientes()
    else:
        st.write("Has seleccionado otra opción.")
        
else:
    login()
