"""Tests for historical sales queries and immutable receipt snapshots."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.checkout import CheckoutService
from kasirkita.services.sales_history import (
    SalesHistoryService,
    SalesHistoryValidationError,
)


class SalesHistoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('SNACK', 'Snack Original', 2000, 10)
            """
        )
        self.product_id = self.connection.execute(
            "SELECT id FROM products WHERE sku = 'SNACK'"
        ).fetchone()[0]
        checkout = CheckoutService(self.connection)
        self.sale = checkout.checkout(
            [{"product_id": self.product_id, "quantity": 2}],
            amount_received_rupiah=5000,
        )
        self.history = SalesHistoryService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_list_sales_returns_persisted_totals(self):
        sales = self.history.list_sales()
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0]["id"], self.sale["sale_id"])
        self.assertEqual(sales[0]["total_rupiah"], 4000)
        self.assertEqual(sales[0]["status"], "completed")

    def test_search_is_literal_and_case_insensitive(self):
        receipt = self.sale["receipt_number"]
        self.assertEqual(len(self.history.list_sales(search=receipt.lower())), 1)
        self.assertEqual(self.history.list_sales(search="%"), [])

    def test_detail_uses_historical_product_snapshot(self):
        self.connection.execute(
            "UPDATE products SET name = 'Nama Baru', unit_price_rupiah = 9999 WHERE id = ?",
            (self.product_id,),
        )
        detail = self.history.get_sale_detail(self.sale["sale_id"])
        self.assertEqual(detail["items"][0]["name"], "Snack Original")
        self.assertEqual(detail["items"][0]["unit_price_rupiah"], 2000)
        self.assertEqual(detail["items"][0]["line_total_rupiah"], 4000)
        self.assertEqual(detail["payments"][0]["amount_rupiah"], 4000)

    def test_missing_sale_returns_none(self):
        self.assertIsNone(self.history.get_sale_detail(999))

    def test_invalid_pagination_and_ids_are_rejected(self):
        for kwargs in [
            {"limit": 0},
            {"limit": 501},
            {"limit": True},
            {"offset": -1},
            {"offset": False},
            {"search": None},
        ]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(SalesHistoryValidationError):
                    self.history.list_sales(**kwargs)
        for sale_id in [0, -1, True, "1", None]:
            with self.subTest(sale_id=sale_id):
                with self.assertRaises(SalesHistoryValidationError):
                    self.history.get_sale_detail(sale_id)


if __name__ == "__main__":
    unittest.main()
