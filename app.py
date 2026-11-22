"""RetailPro web app - local server (standard library only).  Run:  python app.py"""
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from retailpro import billing, demo, inventory, reports
from retailpro import validators as v
from retailpro.errors import AppError, NotFoundError

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCK = threading.Lock()


def make_cart(data):
    items = inventory.load_items()
    cart = []
    for row in data.get("items", []):
        billing.add_to_cart(cart, row["code"], row["qty"], items)
    return cart, items


def dashboard():
    bills = billing.load_bills()
    return {"summary": reports.sales_summary(), "items_count": len(inventory.load_items()),
            "by_payment": reports.by_payment(), "by_category": reports.by_category(),
            "daily": reports.daily_sales()[-7:], "top_items": reports.top_items(),
            "low_stock": inventory.low_stock(), "recent": list(reversed(bills))[:6]}


def api(method, path, data):
    r = path.strip("/").split("/")[1:]
    if r == ["meta"]:
        return {"categories": inventory.CATEGORIES, "gst": inventory.GST_SLABS, "payments": v.PAYMENT_MODES,
                "coupons": list(billing.COUPONS), "tiers": billing.DISCOUNT_TIERS, "low": inventory.LOW_STOCK}
    if r == ["dashboard"]:
        return dashboard()
    if r == ["demo"] and method == "POST":
        added, bills = demo.seed()
        return {"items": added, "bills": bills}
    if r[0] == "items":
        if len(r) == 1:
            if method == "POST":
                return inventory.add_item(data.get("code", ""), data.get("name", ""), data.get("category", ""),
                                          data.get("price", ""), data.get("stock", ""), data.get("gst", ""))
            return inventory.list_items()
        code = r[1]
        if method == "PUT":
            if "price" in data:
                inventory.update_price(code, data["price"])
            if data.get("restock"):
                inventory.restock(code, data["restock"])
            return inventory.get_item(code)
        if method == "DELETE":
            return inventory.remove_item(code)
    if r[0] == "preview" and method == "POST":
        cart, items = make_cart(data)
        return billing.calculate_bill(cart, items, data.get("coupon")) if cart else {"empty": True}
    if r[0] == "bills":
        if len(r) == 1:
            if method == "POST":
                cart, _ = make_cart(data)
                return billing.checkout(cart, data.get("customer", ""), data.get("phone", ""),
                                        data.get("payment", "Cash"), data.get("coupon"))
            return list(reversed(billing.load_bills()))
        if len(r) == 3 and r[2] == "void" and method == "POST":
            return billing.void_bill(r[1])
        return billing.get_bill(r[1])
    raise NotFoundError("Unknown endpoint.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_bytes(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, val in (extra or {}).items():
            self.send_header(k, val)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, obj):
        self.send_bytes(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def handle_any(self, method):
        path = urlparse(self.path).path
        if method == "GET" and not path.startswith("/api"):
            with open(os.path.join(ROOT, "static", "index.html"), "rb") as f:
                return self.send_bytes(200, f.read(), "text/html; charset=utf-8")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}") if n else {}
            with LOCK:
                if path.startswith("/api/export/") and method == "GET":
                    name = path.rsplit("/", 1)[1]
                    fn = reports.export_bills_csv if name == "bills" else reports.export_inventory_csv
                    with open(fn(), "rb") as f:
                        return self.send_bytes(200, f.read(), "text/csv; charset=utf-8",
                                               {"Content-Disposition": f"attachment; filename={name}.csv"})
                return self.send_json(200, api(method, path, data))
        except NotFoundError as e:
            self.send_json(404, {"error": str(e)})
        except AppError as e:
            self.send_json(400, {"error": str(e)})
        except Exception as e:                                   # never crash the server
            self.send_json(500, {"error": f"Server error: {e}"})

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def do_PUT(self): self.handle_any("PUT")
    def do_DELETE(self): self.handle_any("DELETE")


def main():
    port = int(os.environ.get("PORT", 8000))
    server = None
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if not server:
        sys.exit("No free port found.")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"\n  RetailPro is running at {url}\n  Press Ctrl+C to stop.\n")
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped. All data is saved.")


if __name__ == "__main__":
    main()
