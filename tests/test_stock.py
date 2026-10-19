"""Tests for stock adjustments and their audit trail."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.infrastructure.product_repository import ProductNotFoundError
from kasirkita.services.stock import (
    InsufficientStockForAdjustmentError,
    StockAdjustmentError,
    StockService,
)


class StockServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('ITEM', 'Item', 1000, 5)
            """
        )
        self.product_id = self.connection.execute(
            "SELECT id FROM products WHERE sku = 'ITEM'"
        ).fetchone()[0]
        self.stock_service = StockService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_stock_increase_updates_product_and_records_movement(self):
        product = self.stock_service.adjust_stock(self.product_id, 4, "Barang masuk")
        self.assertEqual(product["stock_quantity"], 9)
        movement = self.connection.execute(
            "SELECT movement_type, quantity_delta, note FROM stock_movements"
        ).fetchone()
        self.assertEqual(tuple(movement), ("adjustment_in", 4, "Barang masuk"))

    def test_stock_decrease_updates_product_and_records_movement(self):
        product = self.stock_service.adjust_stock(self.product_id, -2, "Barang rusak")
        self.assertEqual(product["stock_quantity"], 3)
        movement = self.connection.execute(
            "SELECT movement_type, quantity_delta FROM stock_movements"
        ).fetchone()
        self.assertEqual(tuple(movement), ("adjustment_out", -2))

    def test_cannot_reduce_stock_below_zero(self):
        with self.assertRaises(InsufficientStockForAdjustmentError):
            self.stock_service.adjust_stock(self.product_id, -6, "Koreksi")
        self.assertEqual(
            self.connection.execute(
                "SELECT stock_quantity FROM products WHERE id = ?", (self.product_id,)
            ).fetchone()[0],
            5,
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0], 0
        )

    def test_invalid_adjustment_inputs_are_rejected(self):
        for delta in [0, True, 1.5, "2", 2_147_483_648]:
            with self.subTest(delta=delta):
                with self.assertRaises(StockAdjustmentError):
                    self.stock_service.adjust_stock(self.product_id, delta, "Koreksi")
        for note in ["", "   ", None, "x" * 201]:
            with self.subTest(note=note):
                with self.assertRaises(StockAdjustmentError):
                    self.stock_service.adjust_stock(self.product_id, 1, note)

    def test_missing_product_is_rejected(self):
        with self.assertRaises(ProductNotFoundError):
            self.stock_service.adjust_stock(999, 1, "Barang masuk")


if __name__ == "__main__":
    unittest.main()
