import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retailpro import billing, demo, inventory, reports, storage
from retailpro import validators as v
from retailpro.errors import DuplicateError, NotFoundError, StockError, ValidationError


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        storage.set_data_dir(self.tmp.name)
        inventory.add_item("A1", "Apple", "Grocery", 100, 10, 5)
        inventory.add_item("B1", "Biscuit", "Snacks", 50, 3, 18)

    def tearDown(self):
        self.tmp.cleanup()


class TestValidators(unittest.TestCase):
    def test_all(self):
        self.assertEqual(v.validate_code(" rice01 "), "RICE01")
        self.assertEqual(v.validate_phone("+91 98765-43210"), "9876543210")
        self.assertEqual(v.validate_phone(""), "")
        self.assertEqual(v.validate_customer(""), "Walk-in Customer")
        self.assertEqual(v.validate_payment("2"), "UPI")
        for bad in (lambda: v.validate_price("-5"), lambda: v.validate_price("abc"),
                    lambda: v.validate_phone("12345"), lambda: v.validate_code("!"),
                    lambda: v.validate_int("x", 1, 5), lambda: v.validate_payment("bitcoin")):
            with self.assertRaises(ValidationError):
                bad()


class TestInventory(Base):
    def test_crud(self):
        with self.assertRaises(DuplicateError):
            inventory.add_item("A1", "x", "Grocery", 1, 1, 0)
        inventory.update_price("A1", 120)
        inventory.restock("A1", 5)
        self.assertEqual(inventory.get_item("A1")["stock"], 15)
        self.assertEqual(inventory.get_item("A1")["price"], 120)
        self.assertEqual([i["code"] for i in inventory.low_stock()], ["B1"])
        self.assertEqual(len(inventory.search_items("snack")), 1)
        inventory.remove_item("B1")
        with self.assertRaises(NotFoundError):
            inventory.get_item("B1")

    def test_bad_gst(self):
        with self.assertRaises(ValidationError):
            inventory.add_item("Z9", "x", "Grocery", 10, 1, 7)


class TestBilling(Base):
    def test_calculation_no_discount(self):
        b = billing.calculate_bill([["A1", 2]], inventory.load_items())
        self.assertEqual(b["subtotal"], 200)
        self.assertEqual(b["gst"], 10)
        self.assertEqual(b["grand_total"], 210)

    def test_tier_discount_and_coupon(self):
        self.assertEqual(billing.discount_percent(999), 0)
        self.assertEqual(billing.discount_percent(1000), 5)
        self.assertEqual(billing.discount_percent(5000), 10)
        self.assertEqual(billing.discount_percent(100, "fest5"), 5)
        self.assertEqual(billing.discount_percent(5000, "FEST5"), 10)
        with self.assertRaises(ValidationError):
            billing.discount_percent(100, "FAKE")

    def test_cart_merges_and_checks_stock(self):
        cart = []
        billing.add_to_cart(cart, "a1", 4)
        billing.add_to_cart(cart, "A1", 3)
        self.assertEqual(cart, [["A1", 7]])
        with self.assertRaises(StockError):
            billing.add_to_cart(cart, "A1", 4)
        with self.assertRaises(NotFoundError):
            billing.add_to_cart(cart, "NOPE", 1)
        billing.remove_from_cart(cart, "A1")
        self.assertEqual(cart, [])

    def test_checkout_stock_invoice_and_void(self):
        cart = [["A1", 4]]
        bill = billing.checkout(cart, "ravi kumar", "9876543210", "UPI")
        self.assertEqual(bill["invoice"], "INV-00001")
        self.assertEqual(bill["customer"], "Ravi Kumar")
        self.assertEqual(inventory.get_item("A1")["stock"], 6)
        self.assertTrue(os.path.exists(storage.path_for("invoices", "INV-00001.txt")))
        billing.void_bill("INV-00001")
        self.assertEqual(inventory.get_item("A1")["stock"], 10)
        with self.assertRaises(ValidationError):
            billing.void_bill("INV-00001")
        self.assertEqual(reports.sales_summary()["bills"], 0)

    def test_empty_cart(self):
        with self.assertRaises(ValidationError):
            billing.checkout([], "", "", "Cash")


class TestReportsAndDemo(Base):
    def test_demo_and_reports(self):
        added, bills = demo.seed()
        self.assertGreater(added, 5)
        self.assertEqual(bills, 4)
        self.assertEqual(demo.seed()[1], 0)           # idempotent
        s = reports.sales_summary()
        self.assertEqual(s["bills"], 4)
        self.assertAlmostEqual(sum(a for _, a in reports.by_payment()), s["revenue"], places=0)
        self.assertTrue(reports.top_items())
        self.assertTrue(os.path.exists(reports.export_bills_csv()))
        self.assertTrue(os.path.exists(reports.export_inventory_csv()))

    def test_corrupt_file_recovery(self):
        with open(storage.path_for("bills.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(billing.load_bills(), [])


if __name__ == "__main__":
    unittest.main()
