import streamlit as st
import pandas as pd
import json
from fpdf import FPDF
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador JP Security", page_icon="🔒", layout="centered")

# --- FUNCIÓN DE CARGA DE DATOS (BLINDADA NIVEL MÁXIMO) ---
@st.cache_data
def load_data():
    try:
        # 1. Carga Inteligente: Detecta automáticamente si usaste comas (,) o punto y coma (;)
        # engine='python' y sep=None activan el "olfato" de Python para adivinar el formato
        df = pd.read_csv('db_productos.csv', encoding='latin-1', sep=None, engine='python')
        
        # 2. Limpieza de Cabeceras: Quita espacios y pasa a minúsculas
        # Ejemplo: "  Descripcion  " se convierte en "descripcion"
        df.columns = df.columns.str.strip().str.lower()
        
        # 3. RENOMBRADO DE EMERGENCIA
        # Si por alguna razón los nombres siguen mal, renombramos las columnas por su posición
        # Asumimos que el orden en el CSV es: SKU, DESCRIPCION, COSTO, ...
        expected_cols = ['sku', 'descripcion', 'costo']
        
        # Verificamos si existen las columnas clave. Si no, forzamos el renombre.
        if not set(expected_cols).issubset(df.columns):
            if len(df.columns) >= 3:
                mapeo = {
                    df.columns[0]: 'sku',
                    df.columns[1]: 'descripcion',
                    df.columns[2]: 'costo'
                }
                df = df.rename(columns=mapeo)
            else:
                st.error("El archivo CSV tiene menos de 3 columnas. Revisa el formato en GitHub.")
                return pd.DataFrame(), {}

        # 4. Cargar Configuración JSON
        with open('config_sistema.json', 'r') as f:
            conf = json.load(f)
            
        return df, conf
        
    except FileNotFoundError:
        st.error("CRÍTICO: No se encuentra 'db_productos.csv'. Verifica que el nombre sea exacto en GitHub.")
        return pd.DataFrame(), {}
    except Exception as e:
        st.error(f"Error desconocido al cargar datos: {e}")
        return pd.DataFrame(), {}

# Ejecutar carga inicial
df_productos, config = load_data()

# Si falló la carga, detenemos la app aquí para no mostrar más errores
if df_productos.empty:
    st.stop()

# --- CONSTANTES ---
try:
    IVA = config.get('iva', 0.19)
    MARGEN = config.get('utilidad_default', 0.35)
    EMPRESA = config.get('empresa', {"nombre": "JP SECURITY"})
except:
    IVA = 0.19
    MARGEN = 0.35
    EMPRESA = {"nombre": "JP SECURITY"}

# --- INTERFAZ DE USUARIO ---
st.title("🔒 JP SECURITY")
st.markdown(f"**Cotizador Profesional** | Margen: `{MARGEN*100:.0f}%` | IVA: `{IVA*100:.0f}%`")

# 1. CLIENTE
with st.expander("👤 Datos del Cliente", expanded=True):
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nombre / Razón Social")
    nit_cliente = c2.text_input("NIT / Cédula")
    direccion = st.text_input("Dirección / Ciudad")

# 2. PRODUCTOS
st.divider()
st.subheader("📦 Agregar Equipos")

busqueda = st.text_input("🔍 Buscar (ej: Camara, Disco, Servicio)", "")

if busqueda:
    # Filtro tolerante a fallos (na=False)
    resultados = df_productos[
        df_productos['descripcion'].str.contains(busqueda, case=False, na=False) | 
        df_productos['sku'].str.contains(busqueda, case=False, na=False)
    ]
else:
    resultados = df_productos.head(10)

# Preparamos la lista para el selectbox
# Usamos un truco para guardar el índice y no fallar luego
if not resultados.empty:
    opciones_visuales = [
        f"{row['descripcion']} | Base: ${row['costo']:,.0f}" 
        for index, row in resultados.iterrows()
    ]
    
    seleccion = st.selectbox("Seleccione un item:", opciones_visuales)
    
    if seleccion:
        # Recuperar el dato original. Buscamos en el DF filtrado la fila que coincida
        # Hacemos split por el separador visual " | " para obtener solo la descripción limpia
        desc_temp = seleccion.split(" | ")[0]
        item_data = resultados[resultados['descripcion'] == desc_temp].iloc[0]
        
        precio_venta = item_data['costo'] * (1 + MARGEN)
        
        col_a, col_b, col_c = st.columns([2, 2, 1])
        col_a.text(f"SKU: {item_data['sku']}")
        col_b.metric("Precio Venta", f"${precio_venta:,.0f}")
        cantidad = col_c.number_input("Cant.", min_value=1, value=1)
        
        if st.button("➕ Agregar", use_container_width=True):
            if 'carrito' not in st.session_state:
                st.session_state.carrito = []
            
            st.session_state.carrito.append({
                "sku": item_data['sku'],
                "descripcion": item_data['descripcion'],
                "cantidad": cantidad,
                "precio_unit": precio_venta,
                "total": precio_venta * cantidad
            })
            st.success("Agregado")
else:
    st.info("No hay productos que coincidan con la búsqueda.")

# 3. RESUMEN
st.divider()
st.subheader("📋 Cotización Actual")

if 'carrito' in st.session_state and len(st.session_state.carrito) > 0:
    df_cart = pd.DataFrame(st.session_state.carrito)
    
    st.dataframe(
        df_cart[['cantidad', 'descripcion', 'precio_unit', 'total']], 
        use_container_width=True,
        hide_index=True
    )
    
    # Cálculos
    subtotal = df_cart['total'].sum()
    
    # Descuentos
    desc_pct = 0.0
    if subtotal > 3000000: desc_pct = 0.05
    elif subtotal > 1000000: desc_pct = 0.03
    
    val_desc = subtotal * desc_pct
    sub_neto = subtotal - val_desc
    val_iva = sub_neto * IVA
    total_final = sub_neto + val_iva
    
    # Mostrar Totales
    c_tot1, c_tot2 = st.columns(2)
    with c_tot1:
        st.write(f"Subtotal: **${subtotal:,.0f}**")
        if desc_pct > 0:
            st.write(f"Descuento ({desc_pct*100:.0f}%): **-${val_desc:,.0f}**")
        st.write(f"IVA ({IVA*100:.0f}%): **${val_iva:,.0f}**")
    with c_tot2:
        st.metric("TOTAL FINAL", f"${total_final:,.0f}")
        
    # --- PDF GENERATOR ---
    def generar_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # Encabezado
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, str(EMPRESA.get('nombre', 'JP SECURITY')), ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, f"NIT: {EMPRESA.get('nit', '')} | {EMPRESA.get('telefono', '')}", ln=True, align='C')
        pdf.ln(10)
        
        # Datos
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, f"CLIENTE: {cliente}", ln=True)
        pdf.cell(0, 5, f"FECHA: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(5)
        
        # Tabla Header
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(10, 8, "#", 1, 0, 'C', 1)
        pdf.cell(110, 8, "DESCRIPCION", 1, 0, 'C', 1)
        pdf.cell(35, 8, "UNITARIO", 1, 0, 'C', 1)
        pdf.cell(35, 8, "TOTAL", 1, 1, 'C', 1)
        
        # Tabla Body
        pdf.set_font("Arial", size=9)
        for item in st.session_state.carrito:
            # Truncar texto largo para que no rompa la tabla
            desc = (item['descripcion'][:60] + '..') if len(item['descripcion']) > 60 else item['descripcion']
            
            pdf.cell(10, 8, str(item['cantidad']), 1, 0, 'C')
            pdf.cell(110, 8, desc, 1, 0, 'L')
            pdf.cell(35, 8, f"${item['precio_unit']:,.0f}", 1, 0, 'R')
            pdf.cell(35, 8, f"${item['total']:,.0f}", 1, 1, 'R')
            
        # Totales Footer
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(155, 8, "TOTAL A PAGAR", 0, 0, 'R')
        pdf.cell(35, 8, f"${total_final:,.0f}", 1, 1, 'C')
        
        return pdf.output(dest='S').encode('latin-1')
        
    if st.button("📄 Descargar PDF", type="primary"):
        if cliente:
            try:
                bytes_pdf = generar_pdf()
                st.download_button(
                    label="📥 Guardar PDF",
                    data=bytes_pdf,
                    file_name="Cotizacion.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
        else:
            st.warning("Escribe el nombre del cliente primero.")

    if st.button("🗑️ Nueva Cotización"):
        st.session_state.carrito = []
        st.rerun()

else:
    st.info("👈 Agrega items desde el buscador.")
