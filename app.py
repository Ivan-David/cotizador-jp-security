import streamlit as st
import pandas as pd
import json
import os
import base64
from utils import compute_totals
from fpdf import FPDF
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="wide")

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

# --- ESTILOS CSS PARA MEJOR UI ---
st.markdown(
    """
    <style>
    .stApp { font-family: 'Segoe UI', Roboto, Arial, sans-serif; }
    .company-card { background-color: #0b5f9f; color: white; padding: 12px; border-radius: 8px; }
    .muted { color: #6c757d; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
st.markdown("# 🔒 Cotizador JP SECURITY")

# Si no existe `logo.png`, crear un placeholder desde assets/logo_b64.txt
if not os.path.exists("logo.png"):
    # Intentar crear desde base64 incluido
    try:
        if os.path.exists("assets/logo_b64.txt"):
            with open("assets/logo_b64.txt", "r") as f:
                b64 = f.read().strip()
            with open("logo.png", "wb") as fo:
                fo.write(base64.b64decode(b64))
    except Exception:
        pass

    # Si sigue sin existir, generar un logo simple con Pillow
    if not os.path.exists("logo.png"):
        try:
            from PIL import Image, ImageDraw, ImageFont
            W, H = 400, 120
            img = Image.new('RGB', (W, H), color=(11,95,159))
            draw = ImageDraw.Draw(img)
            try:
                fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
            except Exception:
                fnt = ImageFont.load_default()
            text = "JP"
            w, h = draw.textsize(text, font=fnt)
            draw.text(((W-w)/2, (H-h)/2), text, font=fnt, fill=(255,255,255))
            img.save("logo.png")
        except Exception:
            pass

# Sidebar con información de la empresa y formulario cliente
with st.sidebar:
    # Company card
    st.markdown('<div class="company-card">', unsafe_allow_html=True)
    if os.path.exists("logo.png"):
        st.image("logo.png", use_column_width=True)
    st.markdown("**JP SECURITY**  ")
    st.markdown("NIT 1003084297-2  ")
    st.markdown("Puerto Libertador  ")
    st.markdown("Tel: 301 377 88 23  ")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 Información del Cliente")
    cliente_nombre = st.text_input("Cliente / Razón Social")
    cliente_direccion = st.text_input("Dirección")
    fecha_cot = st.date_input("Fecha Emisión", datetime.now())
    fecha_vence = st.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=7))

    st.markdown("---")
    st.caption("Consejo: mantén el nombre del cliente para poder generar PDF.")

# 2. SELECCIÓN PRODUCTOS
st.divider()
st.subheader("📦 Selección de Productos")

# Buscador y resultados en un formulario compacto
with st.form(key='add_item_form'):
    cols = st.columns([3,1])
    busqueda = cols[0].text_input("🔍 Buscar producto o servicio", placeholder="Ej: Cámara, Disco, Instalación...")
    mostrar = cols[1].checkbox("Mostrar todos", value=False)

    # Filtrado
    if busqueda:
        mask = df_productos['descripcion'].str.contains(busqueda, case=False, na=False) | \
               df_productos['sku'].str.contains(busqueda, case=False, na=False)
        resultados = df_productos[mask]
    elif mostrar:
        resultados = df_productos
    else:
        resultados = df_productos.head(8)

    opciones = [f"{r['sku']} — {r['descripcion']} — ${r['costo']:,.0f}" for i,r in resultados.iterrows()]
    seleccion = st.selectbox("Seleccionar item", opciones)
    cantidad = st.number_input("Cantidad", min_value=1, max_value=1000, value=1)
    agregar = st.form_submit_button("➕ Agregar al carrito")

    if agregar and seleccion:
        clave = seleccion.split(' — ')[0]
        item_data = resultados[resultados['sku'] == clave].iloc[0]
        precio_sugerido = item_data['costo'] * (1 + MARGEN)
        # Validación: cliente debe existir antes de agregar
        if not cliente_nombre or not cliente_nombre.strip():
            st.warning("Ingresa el nombre del cliente en la barra lateral antes de agregar items.")
        else:
            if 'carrito' not in st.session_state: st.session_state.carrito = []
            st.session_state.carrito.append({
                'cant': int(cantidad),
                'desc': item_data['descripcion'],
                'sku': item_data['sku'],
                'unit': float(precio_sugerido),
                'total': float(precio_sugerido) * int(cantidad)
            })
            st.success("Item agregado al carrito")

# 3. TABLA Y PDF
st.divider()
if 'carrito' in st.session_state and st.session_state.carrito:
    # Mostrar lista de items con opciones de editar/eliminar
    st.subheader("🛒 Carrito")
    for idx, item in enumerate(list(st.session_state.carrito)):
        # Permitir editar cantidad y eliminar
        c_qty, c_desc, c_price, c_actions = st.columns([1.2, 4, 2, 2])
        qty_val = c_qty.number_input("", min_value=1, value=int(item.get('cant', 1)), key=f"qty_{idx}")
        c_desc.markdown(f"**{item['desc']}**\n`SKU: {item.get('sku','')}`")
        c_price.write(f"${item['unit']:,.0f}")

        if c_actions.button("Actualizar", key=f"up_{idx}"):
            st.session_state.carrito[idx]['cant'] = int(qty_val)
            st.session_state.carrito[idx]['total'] = float(st.session_state.carrito[idx]['unit']) * int(qty_val)
            st.success("Cantidad actualizada")
            st.experimental_rerun()

        if c_actions.button("Eliminar", key=f"del_{idx}"):
            st.session_state.carrito.pop(idx)
            st.experimental_rerun()

    df_cart = pd.DataFrame(st.session_state.carrito)
    
    # Cálculos (externalizados para facilitar pruebas)
    totals = compute_totals(st.session_state.carrito, IVA_PCT)
    subtotal = totals['subtotal']
    monto_desc = totals['monto_desc']
    base_iva = totals['base_iva']
    monto_iva = totals['monto_iva']
    total_neto = totals['total_neto']
    
    col_res1, col_res2 = st.columns([2,1])
    with col_res1:
        st.markdown(f"- **Subtotal:** ${subtotal:,.0f}")
        if monto_desc > 0: st.markdown(f"- **Descuento:** -${monto_desc:,.0f}")
        st.markdown(f"- **Base IVA:** ${base_iva:,.0f}")
        st.markdown(f"- **IVA ({IVA_PCT*100:.0f}%):** ${monto_iva:,.0f}")
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
        folio = f"CT{datetime.now().strftime('%y%m%d%H%M%S')}"
        pdf.cell(90, 8, f"COTIZACIÓN NO {folio}", 0, 1, 'R')
        
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
        
        # Pie con firma
        pdf.ln(10)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, 'Atentamente,\nJP SECURITY\nTel: 301 377 88 23')
        return pdf.output(dest='S').encode('latin-1', 'replace')

    if st.button("📄 Descargar Cotización PDF", type="primary"):
        # Validaciones finales
        if not cliente_nombre or not cliente_nombre.strip():
            st.warning("⚠️ Debes ingresar el nombre del cliente en la barra lateral.")
        elif fecha_vence < fecha_cot:
            st.warning("⚠️ La fecha de vencimiento no puede ser anterior a la fecha de emisión.")
        else:
            pdf_bytes = generar_pdf_final()
            st.download_button("📥 Guardar PDF", pdf_bytes, "Cotizacion_JP_Security.pdf", "application/pdf")

    if st.button("🗑️ Limpiar Todo"):
        st.session_state.carrito = []
        st.rerun()
