"""Tests for date-scoped sales reports."""
import unittest
from datetime import datetime, timezone

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.checkout import CheckoutService
from kasirkita.services.sales_report import SalesReportService, SalesReportValidationError


class SalesReportTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('REPORT', 'Produk laporan', 1000, 20)
            """
        )
        product_id = self.connection.execute(
            "SELECT id FROM products WHERE sku = 'REPORT'"
        ).fetchone()[0]
        self.checkout = CheckoutService(self.connection)
        self.report = SalesReportService(self.connection)
        self.product_id = product_id

    def tearDown(self):
        self.connection.close()

    def _set_sale_date(self, sale_id, date_text):
        self.connection.execute(
            "UPDATE sales SET created_at = ? WHERE id = ?",
            (date_text + "T12:00:00.000Z", sale_id),
        )

    def test_summary_uses_completed_persisted_sales(self):
        sale = self.checkout.checkout(
            [{"product_id": self.product_id, "quantity": 3}],
            amount_received_rupiah=5000,
        )
        self._set_sale_date(sale["sale_id"], "2026-10-10")
        summary = self.report.summarize("2026-10-10", "2026-10-10")
        self.assertEqual(summary["sales_count"], 1)
        self.assertEqual(summary["total_rupiah"], 3000)
        self.assertEqual(summary["items_sold"], 3)
        self.assertEqual(summary["average_sale_rupiah"], 3000)
        self.assertEqual(summary["daily"][0]["date"], "2026-10-10")

    def test_empty_range_returns_zero_totals(self):
        summary = self.report.summarize("2020-01-01", "2020-01-31")
        self.assertEqual(summary["sales_count"], 0)
        self.assertEqual(summary["total_rupiah"], 0)
        self.assertEqual(summary["items_sold"], 0)
        self.assertEqual(summary["average_sale_rupiah"], 0)
        self.assertEqual(summary["daily"], [])

    def test_date_range_validation(self):
        invalid_ranges = [
            ("2026-10-02", "2026-10-01"),
            ("10/01/2026", "2026-10-02"),
            ("2026-02-30", "2026-03-01"),
            (None, "2026-10-02"),
            ("2020-01-01", "2031-01-01"),
        ]
        for start, end in invalid_ranges:
            with self.subTest(start=start, end=end):
                with self.assertRaises(SalesReportValidationError):
                    self.report.summarize(start, end)


if __name__ == "__main__":
    unittest.main()
