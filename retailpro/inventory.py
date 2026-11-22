"""Item catalogue: compound data structure = dict of item-dicts, persisted to items.json."""
from . import storage
from .errors import DuplicateError, NotFoundError, ValidationError
from .validators import validate_code, validate_int, validate_price, validate_text

FILE = "items.json"
GST_SLABS = (0, 5, 12, 18, 28)
CATEGORIES = ("Grocery", "Dairy", "Snacks", "Beverages", "Stationery", "Personal Care", "Electronics")
LOW_STOCK = 5


def load_items():
    return storage.load(FILE, {})


def save_items(items):
    storage.save(FILE, items)


def resolve_category(value):
    v = str(value).strip()
    if v.isdigit() and 1 <= int(v) <= len(CATEGORIES):
        return CATEGORIES[int(v) - 1]
    for c in CATEGORIES:
        if c.lower() == v.lower():
            return c
    raise ValidationError("Choose a category from the list.")


def validate_gst(value):
    rate = validate_int(value, 0, 28, "GST rate")
    if rate not in GST_SLABS:
        raise ValidationError(f"GST must be one of {GST_SLABS}.")
    return rate


def add_item(code, name, category, price, stock, gst):
    code = validate_code(code)
    items = load_items()
    if code in items:
        raise DuplicateError(f"Item {code} already exists.")
    items[code] = {"code": code, "name": validate_text(name, "Item name"),
                   "category": resolve_category(category), "price": validate_price(price),
                   "stock": validate_int(stock, 0, 100000, "Stock"), "gst": validate_gst(gst)}
    save_items(items)
    return items[code]


def get_item(code):
    code = validate_code(code)
    items = load_items()
    if code not in items:
        raise NotFoundError(f"No item with code {code}.")
    return items[code]


def update_price(code, price):
    code = validate_code(code)
    items = load_items()
    if code not in items:
        raise NotFoundError(f"No item with code {code}.")
    items[code]["price"] = validate_price(price)
    save_items(items)
    return items[code]


def restock(code, qty):
    code = validate_code(code)
    items = load_items()
    if code not in items:
        raise NotFoundError(f"No item with code {code}.")
    items[code]["stock"] += validate_int(qty, 1, 100000, "Quantity")
    save_items(items)
    return items[code]


def remove_item(code):
    code = validate_code(code)
    items = load_items()
    if code not in items:
        raise NotFoundError(f"No item with code {code}.")
    removed = items.pop(code)
    save_items(items)
    return removed


def list_items(category=None):
    rows = sorted(load_items().values(), key=lambda i: (i["category"], i["name"]))
    return [i for i in rows if category is None or i["category"] == category]


def search_items(query):
    q = str(query).strip().lower()
    return [i for i in list_items() if q in i["name"].lower() or q in i["code"].lower()
            or q in i["category"].lower()]


def low_stock(threshold=LOW_STOCK):
    return sorted((i for i in load_items().values() if i["stock"] <= threshold), key=lambda i: i["stock"])
