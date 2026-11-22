"""Billing engine: item-wise calculation, discounts, GST, invoices, file storage."""
from datetime import datetime

from . import inventory, storage
from .errors import NotFoundError, StockError, ValidationError
from .validators import validate_customer, validate_int, validate_payment, validate_phone

BILLS_FILE = "bills.json"
DISCOUNT_TIERS = ((5000, 10), (2000, 7), (1000, 5))          # (min subtotal, % off)
COUPONS = {"WELCOME10": 10, "FEST5": 5}                      # best of tier / coupon applies


# ---------- cart (list of [code, qty] pairs) ----------
def add_to_cart(cart, code, qty, catalogue=None):
    catalogue = catalogue if catalogue is not None else inventory.load_items()
    code = str(code).strip().upper()
    if code not in catalogue:
        raise NotFoundError(f"No item with code {code}.")
    qty = validate_int(qty, 1, 10000, "Quantity")
    in_cart = sum(q for c, q in cart if c == code)
    if in_cart + qty > catalogue[code]["stock"]:
        raise StockError(f"Only {catalogue[code]['stock']} of {catalogue[code]['name']} in stock "
                         f"({in_cart} already in cart).")
    for line in cart:
        if line[0] == code:
            line[1] += qty
            return cart
    cart.append([code, qty])
    return cart


def remove_from_cart(cart, code):
    code = str(code).strip().upper()
    before = len(cart)
    cart[:] = [line for line in cart if line[0] != code]
    if len(cart) == before:
        raise NotFoundError(f"{code} is not in the cart.")
    return cart


# ---------- calculation (pure function, easy to test) ----------
def discount_percent(subtotal, coupon=None):
    tier = next((pct for floor, pct in DISCOUNT_TIERS if subtotal >= floor), 0)
    code = (coupon or "").strip().upper()
    if code and code not in COUPONS:
        raise ValidationError(f"Invalid coupon '{code}'.")
    return max(tier, COUPONS.get(code, 0))


def calculate_bill(cart, catalogue, coupon=None):
    if not cart:
        raise ValidationError("Cart is empty.")
    lines, subtotal = [], 0.0
    for code, qty in cart:
        item = catalogue[code]
        amount = round(item["price"] * qty, 2)
        subtotal += amount
        lines.append({"code": code, "name": item["name"], "category": item["category"],
                      "qty": qty, "price": item["price"], "gst_rate": item["gst"], "amount": amount})
    subtotal = round(subtotal, 2)
    pct = discount_percent(subtotal, coupon)
    discount_amt = round(subtotal * pct / 100, 2)
    gst = 0.0
    for ln in lines:
        ln["taxable"] = round(ln["amount"] * (1 - pct / 100), 2)
        ln["gst_amt"] = round(ln["taxable"] * ln["gst_rate"] / 100, 2)
        gst += ln["gst_amt"]
    gst = round(gst, 2)
    taxable = round(subtotal - discount_amt, 2)
    exact = taxable + gst
    grand = round(exact)
    return {"lines": lines, "subtotal": subtotal, "discount_pct": pct, "discount_amt": discount_amt,
            "taxable": taxable, "cgst": round(gst / 2, 2), "sgst": round(gst - round(gst / 2, 2), 2),
            "gst": gst, "round_off": round(grand - exact, 2), "grand_total": grand}


# ---------- persistence ----------
def load_bills():
    return storage.load(BILLS_FILE, [])


def checkout(cart, customer="", phone="", payment="Cash", coupon=None, now=None):
    customer, phone, payment = validate_customer(customer), validate_phone(phone), validate_payment(payment)
    items = inventory.load_items()
    for code, qty in cart:                                   # re-check stock at the last moment
        if code not in items or items[code]["stock"] < qty:
            raise StockError(f"Stock changed for {code}; please rebuild the cart.")
    bill = calculate_bill(cart, items, coupon)
    for code, qty in cart:
        items[code]["stock"] -= qty
    bills = load_bills()
    bill.update({"invoice": f"INV-{len(bills) + 1:05d}",
                 "timestamp": (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                 "customer": customer, "phone": phone, "payment": payment,
                 "coupon": (coupon or "").strip().upper(), "status": "PAID"})
    bills.append(bill)
    inventory.save_items(items)
    storage.save(BILLS_FILE, bills)
    storage.write_text("invoices", f"{bill['invoice']}.txt", format_invoice(bill))
    return bill


def get_bill(invoice):
    inv = str(invoice).strip().upper()
    for b in load_bills():
        if b["invoice"] == inv:
            return b
    raise NotFoundError(f"No invoice {inv}.")


def void_bill(invoice):
    """Cancel a bill: marks it VOID and returns the items to stock."""
    inv = str(invoice).strip().upper()
    bills, items = load_bills(), inventory.load_items()
    for b in bills:
        if b["invoice"] == inv:
            if b["status"] == "VOID":
                raise ValidationError(f"{inv} is already void.")
            for ln in b["lines"]:
                if ln["code"] in items:
                    items[ln["code"]]["stock"] += ln["qty"]
            b["status"] = "VOID"
            inventory.save_items(items)
            storage.save(BILLS_FILE, bills)
            storage.write_text("invoices", f"{inv}.txt", format_invoice(b))
            return b
    raise NotFoundError(f"No invoice {inv}.")


def format_invoice(bill, store="RETAILPRO SUPERMART"):
    w = 66
    out = ["=" * w, store.center(w), "Tax Invoice".center(w), "=" * w,
           f"Invoice : {bill['invoice']:<14} Date    : {bill['timestamp']}",
           f"Customer: {bill['customer']:<14} Payment : {bill['payment']}"]
    if bill["phone"]:
        out.append(f"Phone   : {bill['phone']}")
    out += ["-" * w, f"{'#':<3}{'Item':<24}{'Qty':>5}{'Rate':>10}{'GST%':>6}{'Amount':>14}", "-" * w]
    for i, ln in enumerate(bill["lines"], 1):
        out.append(f"{i:<3}{ln['name'][:23]:<24}{ln['qty']:>5}{ln['price']:>10.2f}"
                   f"{ln['gst_rate']:>6}{ln['amount']:>14.2f}")
    out += ["-" * w, f"{'Subtotal':>52}{bill['subtotal']:>14.2f}"]
    if bill["discount_pct"]:
        tag = f"Discount ({bill['discount_pct']}%" + (f", {bill['coupon']}" if bill["coupon"] else "") + ")"
        out.append(f"{tag:>52}{-bill['discount_amt']:>14.2f}")
    out += [f"{'CGST':>52}{bill['cgst']:>14.2f}", f"{'SGST':>52}{bill['sgst']:>14.2f}",
            f"{'Round off':>52}{bill['round_off']:>14.2f}", "=" * w,
            f"{'GRAND TOTAL (Rs.)':>52}{bill['grand_total']:>14.2f}", "=" * w]
    if bill["status"] == "VOID":
        out.append("*** THIS INVOICE HAS BEEN CANCELLED (VOID) ***".center(w))
    out.append("Thank you for shopping with us!".center(w))
    return "\n".join(out)
