"""Checkout tests covering totals, stock, payments, and rollback invariants."""
import sqlite3
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.tax_settings import TaxSettingsService
from kasirkita.services.checkout import (
    CheckoutService,
    InsufficientStockError,
    InvalidCartError,
    PaymentError,
    ProductUnavailableError,
)


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('TEH', 'Teh', 4500, 10)
            """
        )
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('ROTI', 'Roti', 3000, 4)
            """
        )
        self.teh_id = self.connection.execute(
            "SELECT id FROM products WHERE sku = 'TEH'"
        ).fetchone()[0]
        self.roti_id = self.connection.execute(
            "SELECT id FROM products WHERE sku = 'ROTI'"
        ).fetchone()[0]
        self.checkout_service = CheckoutService(self.connection)

    def tearDown(self):
        self.connection.close()

    def stock(self, product_id):
        return self.connection.execute(
            "SELECT stock_quantity FROM products WHERE id = ?", (product_id,)
        ).fetchone()[0]

    def test_successful_checkout_persists_sale_lines_payment_and_stock(self):
        result = self.checkout_service.checkout(
            [
                {"product_id": self.teh_id, "quantity": 2},
                {"product_id": self.roti_id, "quantity": 1},
            ],
            amount_received_rupiah=15000,
        )
        self.assertEqual(result["subtotal_rupiah"], 12000)
        self.assertEqual(result["tax_rupiah"], 0)
        self.assertEqual(result["total_rupiah"], 12000)
        self.assertEqual(result["change_rupiah"], 3000)
        self.assertEqual(self.stock(self.teh_id), 8)
        self.assertEqual(self.stock(self.roti_id), 3)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0], 2
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0], 1
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0], 2
        )

    def test_duplicate_product_lines_are_combined(self):
        result = self.checkout_service.checkout(
            [
                {"product_id": self.teh_id, "quantity": 1},
                {"product_id": self.teh_id, "quantity": 2},
            ],
            amount_received_rupiah=15000,
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["quantity"], 3)
        self.assertEqual(result["total_rupiah"], 13500)
        self.assertEqual(self.stock(self.teh_id), 7)

    def test_insufficient_cash_changes_nothing(self):
        with self.assertRaises(PaymentError):
            self.checkout_service.checkout(
                [{"product_id": self.teh_id, "quantity": 2}],
                amount_received_rupiah=8999,
            )
        self.assertEqual(self.stock(self.teh_id), 10)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0
        )

    def test_insufficient_stock_changes_nothing(self):
        with self.assertRaises(InsufficientStockError):
            self.checkout_service.checkout(
                [{"product_id": self.roti_id, "quantity": 5}],
                amount_received_rupiah=20000,
            )
        self.assertEqual(self.stock(self.roti_id), 4)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0
        )

    def test_inactive_product_cannot_be_sold(self):
        self.connection.execute(
            "UPDATE products SET is_active = 0 WHERE id = ?", (self.teh_id,)
        )
        with self.assertRaises(ProductUnavailableError):
            self.checkout_service.checkout(
                [{"product_id": self.teh_id, "quantity": 1}],
                amount_received_rupiah=5000,
            )
        self.assertEqual(self.stock(self.teh_id), 10)

    def test_invalid_cart_shapes_and_quantities_are_rejected(self):
        invalid_carts = [
            [],
            None,
            [{"product_id": self.teh_id, "quantity": 0}],
            [{"product_id": True, "quantity": 1}],
            [{"product_id": self.teh_id, "quantity": 1.5}],
            [{"product_id": self.teh_id}],
        ]
        for cart in invalid_carts:
            with self.subTest(cart=cart):
                with self.assertRaises(InvalidCartError):
                    self.checkout_service.checkout(cart, 10000)

    def test_non_cash_payment_is_rejected(self):
        with self.assertRaises(PaymentError):
            self.checkout_service.checkout(
                [{"product_id": self.teh_id, "quantity": 1}],
                5000,
                payment_method="transfer",
            )

    def test_failure_after_stock_update_rolls_back_everything(self):
        self.connection.execute(
            """
            CREATE TRIGGER force_sale_item_failure
            BEFORE INSERT ON sale_items
            BEGIN
                SELECT RAISE(ABORT, 'simulated database failure');
            END;
            """
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.checkout_service.checkout(
                [{"product_id": self.teh_id, "quantity": 2}],
                10000,
            )
        self.assertEqual(self.stock(self.teh_id), 10)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0], 0
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0], 0
        )

    def test_exclusive_tax_is_previewed_and_snapshotted_on_sale(self):
        settings = TaxSettingsService(self.connection)
        settings.save_config(True, 1100, "exclusive", "PPN")
        items = [{"product_id": self.teh_id, "quantity": 2}]
        preview = self.checkout_service.preview(items)
        self.assertEqual(preview["subtotal_rupiah"], 9000)
        self.assertEqual(preview["tax_rupiah"], 990)
        self.assertEqual(preview["total_rupiah"], 9990)

        result = self.checkout_service.checkout(items, amount_received_rupiah=10000)
        self.assertEqual(result["tax_rupiah"], 990)
        self.assertEqual(result["total_rupiah"], 9990)
        self.assertEqual(result["change_rupiah"], 10)
        sale = self.connection.execute(
            """
            SELECT subtotal_rupiah, tax_rupiah, total_rupiah, tax_enabled,
                   tax_rate_basis_points, tax_mode, tax_label
            FROM sales WHERE id = ?
            """,
            (result["sale_id"],),
        ).fetchone()
        self.assertEqual(tuple(sale), (9000, 990, 9990, 1, 1100, "exclusive", "PPN"))

    def test_inclusive_tax_keeps_customer_total_equal_to_gross_price(self):
        TaxSettingsService(self.connection).save_config(True, 1000, "inclusive", "PPN")
        result = self.checkout_service.checkout(
            [{"product_id": self.teh_id, "quantity": 2}],
            amount_received_rupiah=9000,
        )
        self.assertEqual(result["subtotal_rupiah"], 8182)
        self.assertEqual(result["tax_rupiah"], 818)
        self.assertEqual(result["total_rupiah"], 9000)

    def test_insufficient_cash_includes_configured_tax(self):
        TaxSettingsService(self.connection).save_config(True, 1100, "exclusive", "PPN")
        with self.assertRaises(PaymentError):
            self.checkout_service.checkout(
                [{"product_id": self.teh_id, "quantity": 2}],
                amount_received_rupiah=9000,
            )
        self.assertEqual(self.stock(self.teh_id), 10)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0
        )

    def test_zero_total_sale_does_not_create_zero_payment_record(self):
        self.connection.execute(
            "UPDATE products SET unit_price_rupiah = 0 WHERE id = ?", (self.teh_id,)
        )
        result = self.checkout_service.checkout(
            [{"product_id": self.teh_id, "quantity": 1}],
            amount_received_rupiah=0,
        )
        self.assertEqual(result["total_rupiah"], 0)
        self.assertEqual(result["change_rupiah"], 0)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0], 0
        )

    def test_zero_total_sale_returns_any_cash_received_as_change(self):
        self.connection.execute(
            "UPDATE products SET unit_price_rupiah = 0 WHERE id = ?", (self.teh_id,)
        )
        result = self.checkout_service.checkout(
            [{"product_id": self.teh_id, "quantity": 1}],
            amount_received_rupiah=1000,
        )
        self.assertEqual(result["total_rupiah"], 0)
        self.assertEqual(result["change_rupiah"], 1000)


if __name__ == "__main__":
    unittest.main()
