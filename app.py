import streamlit as st
import pandas as pd
import json
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="centered")

# --- FUNCIÓN DE CARGA DE DATOS (BLINDADA) ---
@st.cache_data
def load_data():
    try:
        # 1. Cargar CSV con encoding 'latin-1' para soportar tildes y ñ
        df = pd.read_csv('db_productos.csv', encoding='latin-1')
        
        # 2. Normalizar nombres de columnas (Quitar espacios y pasar a minúsculas)
        # Esto evita errores si en el Excel pusiste "Descripcion " o "COSTO"
        df.columns = df.columns.str.strip().str.lower()
        
        # 3. Cargar Configuración
        with open('config_sistema.json', 'r') as f:
            conf = json.load(f)
            
        return df, conf
        
    except FileNotFoundError as e:
        st.error(f"Error crítico: No se encuentra el archivo. Detalle: {e}")
        return pd.DataFrame(), {}
    except Exception as e:
        st.error(f"Error inesperado cargando datos: {e}")
        return pd.DataFrame(), {}

# Carga inicial
df_productos, config = load_data()

# Validación de seguridad: Si falla la carga, detenemos la app
if df_productos.empty:
    st.warning("⚠️ No se pudieron cargar los productos. Revisa tu archivo CSV en GitHub.")
    st.stop()

# --- CONSTANTES DE NEGOCIO ---
try:
    IVA = config.get('iva', 0.19)
    MARGEN = config.get('utilidad_default', 0.35)
    EMPRESA = config.get('empresa', {})
except:
    IVA = 0.19
    MARGEN = 0.35
    EMPRESA = {"nombre": "JP SECURITY"}

# --- INTERFAZ GRÁFICA ---
st.title("🔒 JP SECURITY")
st.markdown(f"**Sistema de Cotización Móvil** | Margen Aplicado: `{MARGEN*100:.0f}%`")

# SECCIÓN 1: DATOS DEL CLIENTE
with st.expander("👤 1. Datos del Cliente", expanded=True):
    col1, col2 = st.columns(2)
    cliente = col1.text_input("Nombre / Razón Social")
    nit_cliente = col2.text_input("NIT / Cédula")
    direccion = st.text_input("Dirección del proyecto")

# SECCIÓN 2: BUSCADOR DE PRODUCTOS
st.divider()
st.subheader("📦 2. Selección de Equipos")

# Buscador inteligente
busqueda = st.text_input("🔍 Buscar (ej: Camara, Disco, 2MP, Servicio)", "")

if busqueda:
    # Filtramos buscando en la columna 'descripcion' (ya normalizada a minúsculas)
    # na=False evita errores si hay celdas vacías
    resultados = df_productos[
        df_productos['descripcion'].str.contains(busqueda, case=False, na=False) | 
        df_productos['sku'].str.contains(busqueda, case=False, na=False)
    ]
else:
    resultados = df_productos.head(10) # Mostrar los primeros 10 si no hay búsqueda

# Selector visual
opciones = results_list = resultados.apply(
    lambda x: f"{x['descripcion']} (Base: ${x['costo']:,.0f})", axis=1
).tolist()

producto_seleccionado_txt = st.selectbox("Resultados:", opciones)

# Lógica de Agregado
if producto_seleccionado_txt:
    # Recuperamos el item original basado en el texto seleccionado
    idx = opciones.index(producto_seleccionado_txt)
    item_data = resultados.iloc[idx]
    
    # Cálculo de Precio
    precio_venta = item_data['costo'] * (1 + MARGEN)
    
    c1, c2, c3 = st.columns([2, 2, 1])
    c1.info(f"SKU: {item_data['sku']}")
    c2.success(f"Precio Venta: ${precio_venta:,.0f}")
    cantidad = c3.number_input("Cantidad", min_value=1, value=1)

    if st.button("➕ Agregar Item", use_container_width=True):
        if 'carrito' not in st.session_state:
            st.session_state.carrito = []
            
        st.session_state.carrito.append({
            "sku": item_data['sku'],
            "descripcion": item_data['descripcion'],
            "cantidad": cantidad,
            "precio_unit": precio_venta,
            "total": precio_venta * cantidad
        })
        st.toast("✅ Item agregado correctamente")

# SECCIÓN 3: CARRITO Y CIERRE
st.divider()
st.subheader("📋 3. Resumen y Generación")

if 'carrito' in st.session_state and len(st.session_state.carrito) > 0:
    # Convertimos carrito a DataFrame para visualizar
    df_cart = pd.DataFrame(st.session_state.carrito)
    
    # Mostrar tabla simple (ocultamos columnas técnicas si queremos)
    st.dataframe(
        df_cart[['cantidad', 'descripcion', 'precio_unit', 'total']], 
        use_container_width=True,
        hide_index=True
    )
    
    # --- CÁLCULOS FINALES ---
    subtotal_bruto = df_cart['total'].sum()
    
    # Regla de Descuentos (JTS Catalog Logic)
    descuento_pct = 0.0
    if subtotal_bruto > 3000000:
        descuento_pct = 0.05
    elif subtotal_bruto > 1000000:
        descuento_pct = 0.03
        
    monto_descuento = subtotal_bruto * descuento_pct
    subtotal_neto = subtotal_bruto - monto_descuento
    monto_iva = subtotal_neto * IVA
    total_final = subtotal_neto + monto_iva
    
    # Panel de Totales
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown(f"**Subtotal:** ${subtotal_bruto:,.0f}")
        if descuento_pct > 0:
            st.markdown(f"**Descuento ({descuento_pct*100:.0f}%):** -${monto_descuento:,.0f}")
        st.markdown(f"**IVA ({IVA*100:.0f}%):** ${monto_iva:,.0f}")
    
    with col_t2:
        st.metric(label="TOTAL A PAGAR", value=f"${total_final:,.0f}")

    # --- GENERADOR DE PDF ---
    def crear_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # 1. Encabezado
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, EMPRESA.get('nombre', 'JP SECURITY'), ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, f"NIT: {EMPRESA.get('nit', '')}", ln=True, align='C')
        pdf.cell(0, 5, f"{EMPRESA.get('direccion', '')} | Tel: {EMPRESA.get('telefono', '')}", ln=True, align='C')
        pdf.ln(10)
        
        # 2. Info Cliente
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 8, f"CLIENTE: {cliente}", 0, 0)
        pdf.cell(0, 8, f"FECHA: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
        pdf.cell(100, 8, f"NIT/CC: {nit_cliente}", 0, 0)
        pdf.cell(0, 8, f"VENCE: {(datetime.now() + pd.Timedelta(days=7)).strftime('%Y-%m-%d')}", 0, 1)
        pdf
