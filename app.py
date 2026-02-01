import streamlit as st
import pandas as pd
import json
import os
from fpdf import FPDF
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="centered")

# --- CLASE PDF PERSONALIZADA (ESTILO "JP SECURITY") ---
class PDF(FPDF):
    def header(self):
        # 1. Logo (Intenta cargarlo si existe)
        if os.path.exists("logo.png"):
            # x=10, y=8, w=40 (Ajusta el ancho según tu logo real)
            self.image("logo.png", 10, 10, 40)
        
        # 2. Datos de la Empresa (Centrados/Derecha según referencia)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 6, 'JP SECURITY', 0, 1, 'C')
        
        self.set_font('Arial', '', 9)
        self.cell(0, 5, 'NIT 1003084297-2', 0, 1, 'C')
        self.cell(0, 5, 'PUERTO LIBERTADOR', 0, 1, 'C')
        self.cell(0, 5, 'Tel: 301 377 88 23', 0, 1, 'C')
        self.ln(15) # Espacio antes del cuerpo

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, 'Garantía de 12 meses en equipos de seguridad electrónica.', 0, 1, 'C')
        self.cell(0, 5, 'La validez de esta oferta es de 7 días calendario.', 0, 1, 'C')

# --- FUNCIÓN DE CARGA BLINDADA (Como definimos antes) ---
@st.cache_data
def load_data():
    df = None
    errores = []
    # Intento 1: UTF-8
    try:
        df = pd.read_csv('db_productos.csv', sep=',', encoding='utf-8')
        if len(df.columns) < 2: raise Exception("Mal formato")
    except: pass
    
    # Intento 2: Latin-1
    if df is None:
        try:
            df = pd.read_csv('db_productos.csv', sep=None, engine='python', encoding='latin-1')
        except Exception as e:
            errores.append(str(e))
            
    if df is None or df.empty:
        return pd.DataFrame(), {}

    # Limpieza
    df.columns = df.columns.str.strip().str.lower()
    if 'descripcion' not in df.columns and len(df.columns) >= 3:
        cols = df.columns
        df = df.rename(columns={cols[0]:'sku', cols[1]:'descripcion', cols[2]:'costo'})

    # Config
    try:
        with open('config_sistema.json', 'r') as f: conf = json.load(f)
    except: conf = {}
    
    return df, conf

# --- CARGA ---
df_productos, config = load_data()
if df_productos.empty: st.stop()

# Constantes
IVA_PCT = config.get('iva', 0.19)
MARGEN = config.get('utilidad_default', 0.35)

# --- INTERFAZ ---
st.title("🔒 Cotizador JP SECURITY")

# 1. FORMULARIO CLIENTE
with st.expander("📝 Información del Cliente", expanded=True):
    col1, col2 = st.columns(2)
    cliente_nombre = col1.text_input("Cliente / Razón Social")
    cliente_direccion = col2.text_input("Dirección")
    
    c_fecha1, c_fecha2 = st.columns(2)
    fecha_cot = c_fecha1.date_input("Fecha Emisión", datetime.now())
    # Autocalcular vencimiento a 7 días
    fecha_vence = c_fecha2.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=7))

# 2. SELECCIÓN PRODUCTOS
st.divider()
st.subheader("📦 Items de la Cotización")
busqueda = st.text_input("🔍 Buscar Producto o Servicio", placeholder="Ej: Cámara, Disco, Instalación...")

if busqueda:
    mask = df_productos['descripcion'].str.contains(busqueda, case=False, na=False) | \
           df_productos['sku'].str.contains(busqueda, case=False, na=False)
    resultados = df_productos[mask]
else:
    resultados = df_productos.head(5)

if not resultados.empty:
    lista_display = [f"{r['descripcion']} | ${r['costo']:,.0f}" for i,r in resultados.iterrows()]
    seleccion = st.selectbox("Seleccionar Item:", lista_display)
    
    if seleccion:
        desc_raw = seleccion.split(" | $")[0]
        item_data = resultados[resultados['descripcion'] == desc_raw].iloc[0]
        
        precio_sugerido = item_data['costo'] * (1 + MARGEN)
        
        c1, c2, c3 = st.columns([3, 2, 2])
        c1.caption(f"Ref: {item_data['sku']}")
        c2.metric("Precio Unitario", f"${precio_sugerido:,.0f}")
        cantidad = c3.number_input("Cantidad", 1, 1000, 1)
        
        if st.button("➕ Agregar a la Lista", type="primary"):
            if 'carrito' not in st.session_state: st.session_state.carrito = []
            st.session_state.carrito.append({
                'cant': cantidad,
                'desc': item_data['descripcion'],
                'unit': precio_sugerido,
                'total': precio_sugerido * cantidad
            })
            st.success("Item agregado")

# 3. TABLA Y PDF
st.divider()
if 'carrito' in st.session_state and st.session_state.carrito:
    # Mostrar tabla en pantalla
    df_cart = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_cart, use_container_width=True, hide_index=True)
    
    # Cálculos
    subtotal = df_cart['total'].sum()
    desc_factor = 0.05 if subtotal > 3000000 else (0.03 if subtotal > 1000000 else 0)
    monto_desc = subtotal * desc_factor
    base_iva = subtotal - monto_desc
    monto_iva = base_iva * IVA_PCT
    total_neto = base_iva + monto_iva
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.write(f"Subtotal: **${subtotal:,.0f}**")
        if monto_desc > 0: st.write(f"Descuento: **-${monto_desc:,.0f}**")
        st.write(f"IVA ({IVA_PCT*100:.0f}%): **${monto_iva:,.0f}**")
    with col_res2:
        st.metric("TOTAL A PAGAR", f"${total_neto:,.0f}")

    # --- GENERADOR PDF IDENTICO ---
    def generar_pdf_final():
        pdf = PDF()
        pdf.add_page()
        
        # --- BLOQUE INFO (Lado Izq: Cliente | Lado Der: Cotización) ---
        pdf.set_font("Arial", 'B', 10)
        
        # Posición inicial Y
        top_y = pdf.get_y()
        
        # COLUMNA IZQUIERDA (Cliente)
        pdf.set_xy(10, top_y)
        pdf.cell(90, 6, f"CLIENTE:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(90, 5, f"{cliente_nombre}\n{cliente_direccion}", 0, 'L')
        
        # COLUMNA DERECHA (Datos Cotización)
        pdf.set_xy(110, top_y)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(90, 8, "COTIZACIÓN NO CT0076", 0, 1, 'R') # Folio automático o fijo
        
        pdf.set_xy(110, pdf.get_y())
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 6, "FECHA:", 0, 0, 'R')
        pdf.set_font("Arial", '', 9)
        pdf.cell(40, 6, str(fecha_cot), 0, 1, 'R')
        
        pdf.set_xy(110, pdf.get_y())
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 6, "VENCE:", 0, 0, 'R')
        pdf.set_font("Arial", '', 9)
        pdf.cell(40, 6, str(fecha_vence), 0, 1, 'R')
        
        pdf.ln(15)
        
        # --- TABLA DE ITEMS ---
        # Encabezado Tabla (Estilo Idéntico)
        pdf.set_fill_color(240, 240, 240) # Gris claro
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(15, 8, "CANT", 1, 0, 'C', 1)
        pdf.cell(110, 8, "DESCRIPCION", 1, 0, 'C', 1)
        pdf.cell(35, 8, "PRECIO UNIT", 1, 0, 'C', 1)
        pdf.cell(30, 8, "TOTAL", 1, 1, 'C', 1)
        
        # Cuerpo Tabla
        pdf.set_font("Arial", '', 9)
        for item in st.session_state.carrito:
            desc = item['desc'][:65] # Recortar si es muy largo
            pdf.cell(15, 8, str(item['cant']), 1, 0, 'C')
            pdf.cell(110, 8, desc, 1, 0, 'L')
            pdf.cell(35, 8, f"${item['unit']:,.0f}", 1, 0, 'R')
            pdf.cell(30, 8, f"${item['total']:,.0f}", 1, 1, 'R')
            
        # --- TOTALES (Alineados a la derecha) ---
        pdf.ln(5)
        
        # Subtotal
        pdf.set_x(120) # Mover cursor a la derecha
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 6, "SUBTOTAL", 0, 0, 'R')
        pdf.set_font("Arial", '', 9)
        pdf.cell(30, 6, f"${subtotal:,.0f}", 1, 1, 'R')
        
        # Descuento (Solo si aplica)
        if monto_desc > 0:
            pdf.set_x(120)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(40, 6, f"DESCUENTO", 0, 0, 'R')
            pdf.set_font("Arial", '', 9)
            pdf.cell(30, 6, f"-${monto_desc:,.0f}", 1, 1, 'R')

        # IVA
        pdf.set_x(120)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 6, f"IVA {IVA_PCT*100:.0f}%", 0, 0, 'R')
        pdf.set_font("Arial", '', 9)
        pdf.cell(30, 6, f"${monto_iva:,.0f}", 1, 1, 'R')
        
        # Total Final (Resaltado)
        pdf.set_x(120)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(40, 8, "TOTAL", 0, 0, 'R')
        pdf.cell(30, 8, f"${total_neto:,.0f}", 1, 1, 'R')
        
        return pdf.output(dest='S').encode('latin-1', 'replace')

    if st.button("📄 Descargar Cotización PDF", type="primary"):
        if cliente_nombre:
            pdf_bytes = generar_pdf_final()
            st.download_button("📥 Guardar PDF", pdf_bytes, "Cotizacion_JP_Security.pdf", "application/pdf")
        else:
            st.warning("⚠️ Debes ingresar el nombre del cliente primero.")

    if st.button("🗑️ Limpiar Todo"):
        st.session_state.carrito = []
        st.rerun()
