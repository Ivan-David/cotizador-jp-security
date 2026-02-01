import streamlit as st
import pandas as pd
import json
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="centered")

# --- FUNCIÓN DE CARGA UNIVERSAL (Blindaje contra errores) ---
@st.cache_data
def load_data():
    df = None
    errores = []

    # INTENTO 1: Formato Estándar (Comas y UTF-8)
    try:
        df = pd.read_csv('db_productos.csv', sep=',', encoding='utf-8')
        if len(df.columns) < 2: raise ValueError("Formato incorrecto")
    except Exception as e:
        errores.append(f"UTF-8 Falló: {e}")

    # INTENTO 2: Formato Excel Latino (Punto y coma y Latin-1)
    if df is None:
        try:
            df = pd.read_csv('db_productos.csv', sep=';', encoding='latin-1')
            if len(df.columns) < 2: raise ValueError("Formato incorrecto")
        except Exception as e:
            errores.append(f"Latin-1 Falló: {e}")

    # INTENTO 3: Detección Automática (Motor Python)
    if df is None:
        try:
            df = pd.read_csv('db_productos.csv', sep=None, engine='python', encoding='latin-1')
        except Exception as e:
            errores.append(f"Auto Falló: {e}")

    # SI TODO FALLA
    if df is None or df.empty:
        st.error(f"❌ Error Crítico: No se pudo leer la base de datos. Detalles: {errores}")
        return pd.DataFrame(), {}

    # --- NORMALIZACIÓN DE COLUMNAS ---
    # Esto arregla si escribiste " Descripcion " o "COSTO"
    df.columns = df.columns.str.strip().str.lower()
    
    # Renombrado de emergencia si las columnas no coinciden
    if 'descripcion' not in df.columns:
        if len(df.columns) >= 3:
            # Asumimos orden: sku, descripcion, costo...
            col_names = list(df.columns)
            df = df.rename(columns={col_names[0]: 'sku', col_names[1]: 'descripcion', col_names[2]: 'costo'})

    # Cargar Configuración
    try:
        with open('config_sistema.json', 'r') as f:
            conf = json.load(f)
    except:
        conf = {}

    return df, conf

# --- INICIO DE LA APP ---
df_productos, config = load_data()

if df_productos.empty:
    st.stop()

# Constantes con valores por defecto si falla el JSON
IVA = config.get('iva', 0.19)
MARGEN = config.get('utilidad_default', 0.35)
EMPRESA = config.get('empresa', {"nombre": "JP SECURITY", "nit": "1003084297-2"})

# --- INTERFAZ ---
st.title("🔒 JP SECURITY")
st.caption(f"Cotizador Inteligente | Margen: {MARGEN*100:.0f}%")

# 1. Cliente
with st.expander("👤 Datos del Cliente", expanded=True):
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nombre / Empresa")
    nit = c2.text_input("NIT / CC")
    direccion = st.text_input("Dirección")

# 2. Buscador
st.divider()
st.subheader("📦 Agregar Productos")
busqueda = st.text_input("🔍 Buscar (Cámaras, Discos, Servicios)", "")

if busqueda:
    # Filtro tolerante a mayúsculas/minúsculas y vacíos
    f1 = df_productos['descripcion'].str.contains(busqueda, case=False, na=False)
    f2 = df_productos['sku'].str.contains(busqueda, case=False, na=False)
    resultados = df_productos[f1 | f2]
else:
    resultados = df_productos.head(10)

if not resultados.empty:
    # Creamos una lista amigable para el selector
    lista_items = [f"{r['descripcion']} | ${r['costo']:,.0f}" for i, r in resultados.iterrows()]
    seleccion = st.selectbox("Seleccionar:", lista_items)
    
    if seleccion:
        # Recuperar datos del item seleccionado
        desc_limpia = seleccion.split(" | $")[0]
        item = resultados[resultados['descripcion'] == desc_limpia].iloc[0]
        
        precio_venta = item['costo'] * (1 + MARGEN)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.caption(f"SKU: {item['sku']}")
        col2.metric("Precio Venta", f"${precio_venta:,.0f}")
        cantidad = col3.number_input("Cant.", 1, 100, 1)
        
        if st.button("➕ Agregar Item", type="primary", use_container_width=True):
            if 'carrito' not in st.session_state: st.session_state.carrito = []
            st.session_state.carrito.append({
                "sku": item['sku'],
                "descripcion": item['descripcion'],
                "cantidad": cantidad,
                "unitario": precio_venta,
                "total": precio_venta * cantidad
            })
            st.toast("Agregado exitosamente")
else:
    st.info("No se encontraron productos.")

# 3. Resumen
st.divider()
if 'carrito' in st.session_state and st.session_state.carrito:
    df_cart = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_cart[['cantidad', 'descripcion', 'total']], use_container_width=True, hide_index=True)
    
    subtotal = df_cart['total'].sum()
    
    # Descuentos
    desc_pct = 0.05 if subtotal > 3000000 else (0.03 if subtotal > 1000000 else 0)
    descuento = subtotal * desc_pct
    iva_val = (subtotal - descuento) * IVA
    total = (subtotal - descuento) + iva_val
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Subtotal: **${subtotal:,.0f}**")
        if descuento > 0: st.write(f"Descuento ({desc_pct*100:.0f}%): **-${descuento:,.0f}**")
        st.write(f"IVA ({IVA*100:.0f}%): **${iva_val:,.0f}**")
    with c2:
        st.metric("TOTAL A PAGAR", f"${total:,.0f}")

    # Generar PDF
    def generar_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, EMPRESA['nombre'], ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, f"NIT: {EMPRESA.get('nit','')} | {EMPRESA.get('telefono','')}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.cell(0, 5, f"CLIENTE: {cliente}", ln=True)
        pdf.cell(0, 5, f"FECHA: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(5)
        
        # Cabecera Tabla
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(10, 8, "#", 1, 0, 'C', 1)
        pdf.cell(100, 8, "DESCRIPCION", 1, 0, 'C', 1)
        pdf.cell(35, 8, "UNITARIO", 1, 0, 'C', 1)
        pdf.cell(40, 8, "TOTAL", 1, 1, 'C', 1)
        
        # Filas
        pdf.set_font("Arial", size=9)
        for row in st.session_state.carrito:
            desc = (row['descripcion'][:50] + '..') if len(row['descripcion']) > 50 else row['descripcion']
            pdf.cell(10, 8, str(row['cantidad']), 1, 0, 'C')
            pdf.cell(100, 8, desc, 1, 0, 'L')
            pdf.cell(35, 8, f"${row['unitario']:,.0f}", 1, 0, 'R')
            pdf.cell(40, 8, f"${row['total']:,.0f}", 1, 1, 'R')
            
        # Totales
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(145, 8, "TOTAL A PAGAR", 0, 0, 'R')
        pdf.cell(40, 8, f"${total:,.0f}", 1, 1, 'C')
        
        return pdf.output(dest='S').encode('latin-1', 'replace') # Fix characters in PDF too

    if st.button("📄 Descargar PDF", type="primary"):
        if cliente:
            st.download_button("📥 Guardar", generar_pdf(), "cotizacion.pdf", "application/pdf")
        else:
            st.warning("Escribe el nombre del cliente.")

    if st.button("🗑️ Borrar Todo"):
        st.session_state.carrito = []
        st.rerun()
