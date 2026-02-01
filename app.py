import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="centered")

# --- CARGA DE DATOS ---
@st.cache_data
def load_data():
    productos = pd.read_csv('db_productos.csv')
    with open('config_sistema.json', 'r') as f:
        config = json.load(f)
    return productos, config

try:
    df_productos, config = load_data()
except:
    st.error("Error cargando archivos base. Verifica que db_productos.csv y config_sistema.json estén en el repositorio.")
    st.stop()

# --- INTERFAZ MÓVIL ---
st.title("🔒 JP SECURITY")
st.caption(f"Cotizador Oficial | IVA: {config['iva']*100}% | Margen: {config['utilidad_default']*100}%")

# 1. Datos del Cliente
with st.expander("👤 Datos del Cliente", expanded=True):
    cliente = st.text_input("Nombre del Cliente")
    direccion = st.text_input("Ubicación / Dirección")

# 2. Selector de Productos
st.divider()
st.subheader("📦 Agregar Equipos")

# Buscador Inteligente
busqueda = st.text_input("Buscar (ej: Cámara, Disco, 2MP)", "")
if busqueda:
    filtro = df_productos[df_productos['descripcion'].str.contains(busqueda, case=False, na=False)]
else:
    filtro = df_productos.head(5) # Mostrar algunos por defecto

item_seleccionado = st.selectbox("Seleccionar Item:", filtro['descripcion'].tolist())

col1, col2 = st.columns(2)
with col1:
    cantidad = st.number_input("Cantidad", min_value=1, value=1)
with col2:
    # Botón para agregar (En una app real, aquí usaríamos Session State para ir armando la lista)
    if st.button("Agregar Item"):
        # Lógica para agregar a la 'canasta' temporal
        if 'carrito' not in st.session_state:
            st.session_state.carrito = []
        
        sku = df_productos[df_productos['descripcion'] == item_seleccionado].iloc[0]['sku']
        costo = df_productos[df_productos['descripcion'] == item_seleccionado].iloc[0]['costo']
        
        st.session_state.carrito.append({
            "sku": sku,
            "desc": item_seleccionado,
            "cant": cantidad,
            "costo_base": costo
        })
        st.success("Agregado")

# 3. Resumen y Totales
st.divider()
st.subheader("📋 Resumen de Cotización")

if 'carrito' in st.session_state and len(st.session_state.carrito) > 0:
    df_carrito = pd.DataFrame(st.session_state.carrito)
    
    # Cálculos Financieros
    margen = config['utilidad_default']
    df_carrito['Unitario Venta'] = df_carrito['costo_base'] * (1 + margen)
    df_carrito['Total Línea'] = df_carrito['Unitario Venta'] * df_carrito['cant']
    
    st.dataframe(df_carrito[['cant', 'desc', 'Total Línea']], use_container_width=True)
    
    subtotal = df_carrito['Total Línea'].sum()
    
    # Lógica de Descuentos
    desc_pct = 0
    if subtotal > 3000000: desc_pct = 0.05
    elif subtotal > 1000000: desc_pct = 0.03
    
    descuento = subtotal * desc_pct
    iva = (subtotal - descuento) * config['iva']
    total_final = (subtotal - descuento) + iva
    
    st.info(f"💰 TOTAL A COBRAR: ${total_final:,.0f}")
    
    if st.button("📄 Generar PDF para WhatsApp"):
        st.write("Generando PDF... (Aquí conectaremos el módulo de exportación)")
        # Aquí iría la llamada a tu script pdf_generator.py
else:
    st.warning("El carrito está vacío")
