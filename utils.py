def compute_totals(carrito, iva_pct=0.19):
    """Calcula subtotal, descuento, base IVA, monto IVA y total neto.

    Reglas de descuento:
    - >3.000.000 : 5%
    - >1.000.000 : 3%
    - else: 0
    """
    totals = {
        'subtotal': 0.0,
        'desc_factor': 0.0,
        'monto_desc': 0.0,
        'base_iva': 0.0,
        'monto_iva': 0.0,
        'total_neto': 0.0
    }
    if not carrito:
        return totals

    subtotal = sum([float(item.get('total', 0)) for item in carrito])
    if subtotal > 3000000:
        desc_factor = 0.05
    elif subtotal > 1000000:
        desc_factor = 0.03
    else:
        desc_factor = 0.0

    monto_desc = subtotal * desc_factor
    base_iva = subtotal - monto_desc
    monto_iva = base_iva * iva_pct
    total_neto = base_iva + monto_iva

    totals.update({
        'subtotal': subtotal,
        'desc_factor': desc_factor,
        'monto_desc': monto_desc,
        'base_iva': base_iva,
        'monto_iva': monto_iva,
        'total_neto': total_neto
    })
    return totals
