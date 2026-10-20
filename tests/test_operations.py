"""Tests for operating costs, expenses, returns, and profit summaries."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.checkout import CheckoutService
from kasirkita.services.operations import (
    CostPriceService, ExpenseService, OperationError, ProfitService, ReturnService,
)


class OperationsServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            "INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity, unit_cost_rupiah) "
            "VALUES ('KOPI', 'Kopi', 10000, 8, 6000)"
        )
        self.product_id = self.connection.execute("SELECT id FROM products WHERE sku='KOPI'").fetchone()[0]

    def tearDown(self):
        self.connection.close()

    def test_cost_price_is_saved_and_low_stock_is_detected(self):
        costs = CostPriceService(self.connection)
        costs.set_cost(self.product_id, 6500)
        self.assertEqual(costs.list_products()[0]["unit_cost_rupiah"], 6500)
        costs.set_cost(self.product_id, 6000)
        self.connection.execute("UPDATE products SET stock_quantity = 2 WHERE id = ?", (self.product_id,))
        self.assertEqual(costs.low_stock(2)[0]["stock_quantity"], 2)

    def test_expense_can_be_recorded_listed_and_voided(self):
        expenses = ExpenseService(self.connection)
        item = expenses.add("Listrik", "Tagihan toko", 75000, "2026-10-20", "Oktober")
        self.assertEqual(expenses.list()[0]["amount_rupiah"], 75000)
        expenses.void(item["id"])
        self.assertEqual(expenses.list(), [])
        self.assertEqual(expenses.list(include_voided=True)[0]["is_voided"], 1)

    def test_checkout_snapshots_cost_and_profit_uses_cost_snapshot(self):
        checkout = CheckoutService(self.connection)
        sale = checkout.checkout([{"product_id": self.product_id, "quantity": 2}], 20000)
        line = self.connection.execute(
            "SELECT unit_cost_rupiah FROM sale_items WHERE sale_id = ?", (sale["sale_id"],)
        ).fetchone()
        self.assertEqual(line["unit_cost_rupiah"], 6000)
        profit = ProfitService(self.connection).summarize("2026-01-01", "2027-01-01")
        self.assertEqual(profit["revenue_rupiah"], 20000)
        self.assertEqual(profit["cost_of_goods_rupiah"], 12000)
        self.assertEqual(profit["gross_profit_rupiah"], 8000)

    def test_return_restores_stock_and_cannot_exceed_sold_quantity(self):
        sale = CheckoutService(self.connection).checkout(
            [{"product_id": self.product_id, "quantity": 2}], 20000
        )
        item = self.connection.execute("SELECT id FROM sale_items WHERE sale_id = ?", (sale["sale_id"],)).fetchone()
        returns = ReturnService(self.connection)
        result = returns.record(sale["sale_id"], [{"sale_item_id": item["id"], "quantity": 1}], "Barang rusak")
        self.assertEqual(result["refund_rupiah"], 10000)
        stock = self.connection.execute("SELECT stock_quantity FROM products WHERE id = ?", (self.product_id,)).fetchone()[0]
        self.assertEqual(stock, 7)
        with self.assertRaises(OperationError):
            returns.record(sale["sale_id"], [{"sale_item_id": item["id"], "quantity": 2}], "Retur berlebih")

    def test_invalid_expense_amount_and_missing_product_are_rejected(self):
        with self.assertRaises(OperationError):
            ExpenseService(self.connection).add("Listrik", "Tagihan", 0, "2026-10-20")
        with self.assertRaises(OperationError):
            CostPriceService(self.connection).set_cost(9999, 500)


if __name__ == "__main__":
    unittest.main()
