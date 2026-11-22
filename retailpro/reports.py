"""Sales analytics and CSV export built on the stored bills."""
from collections import Counter, defaultdict

from . import billing, inventory, storage


def active_bills():
    return [b for b in billing.load_bills() if b["status"] == "PAID"]


def sales_summary():
    bills = active_bills()
    revenue = round(sum(b["grand_total"] for b in bills), 2)
    return {"bills": len(bills), "revenue": revenue,
            "gst": round(sum(b["gst"] for b in bills), 2),
            "discounts": round(sum(b["discount_amt"] for b in bills), 2),
            "average": round(revenue / len(bills), 2) if bills else 0.0}


def by_payment():
    totals = defaultdict(float)
    for b in active_bills():
        totals[b["payment"]] += b["grand_total"]
    return sorted(((k, round(v, 2)) for k, v in totals.items()), key=lambda r: -r[1])


def by_category():
    totals = defaultdict(float)
    for b in active_bills():
        for ln in b["lines"]:
            totals[ln["category"]] += ln["amount"]
    return sorted(((k, round(v, 2)) for k, v in totals.items()), key=lambda r: -r[1])


def top_items(n=5):
    qty, rev = Counter(), defaultdict(float)
    for b in active_bills():
        for ln in b["lines"]:
            qty[ln["name"]] += ln["qty"]
            rev[ln["name"]] += ln["amount"]
    return [(name, q, round(rev[name], 2)) for name, q in qty.most_common(n)]


def daily_sales():
    totals = defaultdict(float)
    for b in active_bills():
        totals[b["timestamp"][:10]] += b["grand_total"]
    return sorted((d, round(v, 2)) for d, v in totals.items())


def export_bills_csv():
    rows = [(b["invoice"], b["timestamp"], b["customer"], b["payment"], b["subtotal"], b["discount_amt"],
             b["gst"], b["grand_total"], b["status"]) for b in billing.load_bills()]
    return storage.export_csv("bills.csv", ("Invoice", "Date", "Customer", "Payment", "Subtotal",
                                            "Discount", "GST", "Total", "Status"), rows)


def export_inventory_csv():
    rows = [(i["code"], i["name"], i["category"], i["price"], i["stock"], i["gst"])
            for i in inventory.list_items()]
    return storage.export_csv("inventory.csv", ("Code", "Name", "Category", "Price", "Stock", "GST%"), rows)
