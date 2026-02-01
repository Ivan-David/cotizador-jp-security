import streamlit as st
import pandas as pd
import json
from fpdf import FPDF
from datetime import datetime, timedelta

# --- CONFIGURACIÓN E INICIO ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒")

# Función para cargar datos
@st.cache_data
def load_data():
    try:
        # Agregamos encoding='latin-1' para que acepte tildes y eñes sin fallar
        df = pd.read_csv('db_productos.csv', encoding='latin-1')
        with open('config_sistema.json', 'r') as f:
            conf = json.load(f)
        return df, conf
    except FileNotFoundError:
        st.error("Error: No se encuentran los archivos CSV o JSON.")
        return pd.DataFrame(), {}

df_productos, config = load_data()

if df_productos.empty:
    st.stop()

# --- LÓGICA DE NEGOCIO ---
IVA = config['iva']
MARGEN = config['utilidad_default']

# --- INTERFAZ DE USUARIO ---
st.title("🔒 JP SECURITY - Cotizador")
st.markdown(f"**Gestión de Cotizaciones en Campo** | Margen: `{MARGEN*100}%`")

# 1. Datos del Cliente
with st.container():
    st.subheader("1. Datos del Cliente")
    col1, col2 = st.columns(2)
    cliente = col1.text_input("Cliente / Empresa")
    nit = col2.text_input("NIT / Cédula")
    direccion = st.text_input("Dirección / Ubicación")

# 2. Selección de Productos
st.divider()
st.subheader("2. Agregar Productos")

# Buscador
busqueda = st.text_input("🔍 Buscar equipo (ej: camara, disco, 2mp)", "")

if busqueda:
    resultados = df_productos[df_productos['descripcion'].str.contains(busqueda, case=False, na=False)]
else:
    resultados = df_productos.head(5)

producto_sel = st.selectbox("Seleccione un item:", resultados['descripcion'].tolist())

# Obtener datos del item seleccionado
if producto_sel:
    item_data = df_productos[df_productos['descripcion'] == producto_sel].iloc[0]
    precio_venta_sugerido = item_data['costo'] * (1 + MARGEN)

    c1, c2, c3 = st.columns([2,2,1])
    c1.metric("Costo Base", f"${item_data['costo']:,.0f}")
    c2.metric("Precio Venta (+Margen)", f"${precio_venta_sugerido:,.0f}")

    cantidad = c3.number_input("Cant.", min_value=1, value=1)

    if st.button("➕ Agregar a la Cotización"):
        if 'carrito' not in st.session_state:
            st.session_state.carrito = []

        st.session_state.carrito.append({
            "sku": item_data['sku'],
            "descripcion": item_data['descripcion'],
            "cantidad": cantidad,
            "precio_unit": precio_venta_sugerido,
            "total": precio_venta_sugerido * cantidad
        })
        st.success("Item agregado")

# 3. Resumen y PDF
st.divider()
st.subheader("3. Resumen de Propuesta")

if 'carrito' in st.session_state and len(st.session_state.carrito) > 0:
    df_cart = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_cart, use_container_width=True)

    # Cálculos Finales
    subtotal = df_cart['total'].sum()

    # Descuentos Automáticos
    descuento_pct = 0
    if subtotal > 3000000: descuento_pct = 0.05
    elif subtotal > 1000000: descuento_pct = 0.03

    valor_descuento = subtotal * descuento_pct
    subtotal_neto = subtotal - valor_descuento
    valor_iva = subtotal_neto * IVA
    total_final = subtotal_neto + valor_iva

    # Mostrar Totales
    c_tot1, c_tot2 = st.columns(2)
    c_tot1.markdown(f"**Subtotal:** ${subtotal:,.0f}")
    c_tot1.markdown(f"**Descuento ({descuento_pct*100}%):** -${valor_descuento:,.0f}")
    c_tot1.markdown(f"**IVA ({IVA*100}%):** ${valor_iva:,.0f}")
    c_tot2.metric("TOTAL A PAGAR", f"${total_final:,.0f}")

    # --- GENERADOR PDF ---
    def generar_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Encabezado
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=config['empresa']['nombre'], ln=1, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"NIT: {config['empresa']['nit']} | Tel: {config['empresa']['contacto']}", ln=1, align='C')

        pdf.line(10, 30, 200, 30)
        pdf.ln(10)

        # Cliente
        pdf.cell(200, 10, txt=f"Cliente: {cliente}", ln=1)
        pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=1)

        # Tabla
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 10, "Descripción", 1)
        pdf.cell(30, 10, "Cant", 1)
        pdf.cell(30, 10, "Unitario", 1)
        pdf.cell(30, 10, "Total", 1)
        pdf.ln()

        pdf.set_font("Arial", size=9)
        for item in st.session_state.carrito:
            pdf.cell(100, 10, item['descripcion'][:45], 1) # Recortar nombre largo
            pdf.cell(30, 10, str(item['cantidad']), 1)
            pdf.cell(30, 10, f"${item['precio_unit']:,.0f}", 1)
            pdf.cell(30, 10, f"${item['total']:,.0f}", 1)
            pdf.ln()

        # Totales
        pdf.ln(5)
        pdf.cell(160, 10, "TOTAL A PAGAR (IVA Incluido)", 0, 0, 'R')
        pdf.cell(30, 10, f"${total_final:,.0f}", 1, 1, 'C')

        return pdf.output(dest='S').encode('latin-1')

    if st.button("📄 Generar PDF Final"):
        if cliente:
            pdf_bytes = generar_pdf()
            st.download_button(
                label="📥 Descargar Cotización PDF",
                data=pdf_bytes,
                file_name=f"Cotizacion_{cliente}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Por favor ingrese el nombre del cliente arriba.")

# Botón Reset
if st.button("Borrar Todo / Nueva Cotización"):
    st.session_state.carrito = []
    st.rerun()
