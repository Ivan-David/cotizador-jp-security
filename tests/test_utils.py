from utils import compute_totals


def test_empty_cart():
    t = compute_totals([], 0.19)
    assert t['subtotal'] == 0
    assert t['monto_desc'] == 0
    assert t['monto_iva'] == 0
    assert t['total_neto'] == 0


def test_small_cart_no_discount():
    cart = [{'total': 100000}, {'total': 200000}]
    t = compute_totals(cart, 0.19)
    assert t['subtotal'] == 300000
    assert t['desc_factor'] == 0
    assert round(t['monto_iva'], 2) == round((300000) * 0.19, 2)


def test_discount_3pct():
    cart = [{'total': 600000}, {'total': 500000}]
    t = compute_totals(cart, 0.19)
    assert t['subtotal'] == 1100000
    assert t['desc_factor'] == 0.03


def test_discount_5pct():
    cart = [{'total': 2000000}, {'total': 1500000}]
    t = compute_totals(cart, 0.19)
    assert t['subtotal'] == 3500000
    assert t['desc_factor'] == 0.05
