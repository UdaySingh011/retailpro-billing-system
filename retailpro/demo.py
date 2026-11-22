"""Sample data so the application can be demonstrated instantly."""
from datetime import datetime, timedelta

from . import billing, inventory

ITEMS = (
    ("RICE01", "Basmati Rice 5kg", "Grocery", 640, 40, 5),
    ("ATTA01", "Whole Wheat Atta 10kg", "Grocery", 455, 30, 5),
    ("OIL01", "Sunflower Oil 1L", "Grocery", 165, 50, 5),
    ("MILK01", "Full Cream Milk 1L", "Dairy", 68, 60, 0),
    ("PNR01", "Paneer 200g", "Dairy", 95, 25, 5),
    ("CHIP01", "Potato Chips 100g", "Snacks", 40, 80, 12),
    ("BISC01", "Chocolate Biscuits", "Snacks", 30, 4, 18),
    ("COLA01", "Cola 750ml", "Beverages", 45, 70, 28),
    ("JUIC01", "Mango Juice 1L", "Beverages", 110, 35, 12),
    ("NOTE01", "Notebook 200 pages", "Stationery", 85, 100, 12),
    ("PEN01", "Gel Pen (Pack of 5)", "Stationery", 60, 3, 18),
    ("SOAP01", "Bath Soap 100g", "Personal Care", 42, 90, 18),
    ("EARB01", "Wired Earphones", "Electronics", 499, 15, 18),
)

SALES = (
    (3, "Rohit Sharma", "9876543210", "UPI", "", (("RICE01", 2), ("OIL01", 3), ("MILK01", 4))),
    (2, "Priya Singh", "", "Cash", "FEST5", (("CHIP01", 5), ("COLA01", 4), ("NOTE01", 3))),
    (1, "Amit Verma", "9123456780", "Card", "", (("EARB01", 2), ("ATTA01", 2), ("PNR01", 3))),
    (0, "", "", "Cash", "", (("SOAP01", 6), ("PEN01", 1))),
)


def seed():
    added = 0
    existing = inventory.load_items()
    for row in ITEMS:
        if row[0] not in existing:
            inventory.add_item(*row)
            added += 1
    bills = 0
    if not billing.load_bills():
        for days_ago, name, phone, pay, coupon, lines in SALES:
            cart = []
            for code, qty in lines:
                billing.add_to_cart(cart, code, qty)
            billing.checkout(cart, name, phone, pay, coupon, now=datetime.now() - timedelta(days=days_ago))
            bills += 1
    return added, bills
