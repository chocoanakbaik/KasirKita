"""Unit and integration tests for the product catalogue."""
import sqlite3
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.infrastructure.product_repository import (
    DuplicateSKUError,
    ProductNotFoundError,
    ProductRepository,
)
from kasirkita.services.product_catalog import ProductCatalog, ProductValidationError


class ProductCatalogTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.catalog = ProductCatalog(ProductRepository(self.connection))

    def tearDown(self):
        self.connection.close()

    def test_create_normalizes_sku_and_trims_name(self):
        product = self.catalog.create_product(" tea-01 ", "  Teh Botol  ", 4500, 8)
        self.assertEqual(product["sku"], "TEA-01")
        self.assertEqual(product["name"], "Teh Botol")
        self.assertEqual(product["unit_price_rupiah"], 4500)
        self.assertEqual(product["stock_quantity"], 8)
        self.assertTrue(product["is_active"])

    def test_duplicate_sku_is_rejected_case_insensitively(self):
        self.catalog.create_product("abc", "Produk A", 1000)
        with self.assertRaises(DuplicateSKUError):
            self.catalog.create_product("ABC", "Produk B", 2000)

    def test_blank_fields_are_rejected(self):
        for sku, name in [("", "Produk"), ("SKU", "  ")]:
            with self.subTest(sku=sku, name=name):
                with self.assertRaises(ProductValidationError):
                    self.catalog.create_product(sku, name, 1000)

    def test_invalid_price_types_and_ranges_are_rejected(self):
        for price in [-1, True, 1.5, "1000", 9_000_000_000_000_001]:
            with self.subTest(price=price):
                with self.assertRaises(ProductValidationError):
                    self.catalog.create_product("SKU-" + str(type(price).__name__), "Produk", price)

    def test_invalid_stock_is_rejected(self):
        for stock in [-1, True, 1.5, "2", 2_147_483_648]:
            with self.subTest(stock=stock):
                with self.assertRaises(ProductValidationError):
                    self.catalog.create_product("SKU-" + str(type(stock).__name__), "Produk", 1000, stock)

    def test_create_duplicate_does_not_corrupt_existing_product(self):
        original = self.catalog.create_product("DUP", "Asli", 1000, 5)
        with self.assertRaises(DuplicateSKUError):
            self.catalog.create_product("DUP", "Pengganti", 2000, 9)
        stored = self.catalog.get_product(original["id"])
        self.assertEqual(stored["name"], "Asli")
        self.assertEqual(stored["stock_quantity"], 5)

    def test_list_hides_inactive_products_by_default(self):
        product = self.catalog.create_product("OFF", "Produk nonaktif", 1000)
        self.catalog.set_product_active(product["id"], False)
        self.assertEqual(self.catalog.list_products(), [])
        self.assertEqual(len(self.catalog.list_products(include_inactive=True)), 1)

    def test_search_treats_percent_as_literal(self):
        self.catalog.create_product("ABC", "Produk biasa", 1000)
        self.catalog.create_product("PCT", "Diskon 50% khusus", 2000)
        matches = self.catalog.list_products(search="%")
        self.assertEqual([item["sku"] for item in matches], ["PCT"])

    def test_update_preserves_stock_and_rejects_missing_id(self):
        product = self.catalog.create_product("SKU1", "Awal", 1000, 12)
        updated = self.catalog.update_product(product["id"], "SKU2", "Baru", 1500)
        self.assertEqual(updated["stock_quantity"], 12)
        self.assertEqual(updated["unit_price_rupiah"], 1500)
        with self.assertRaises(ProductNotFoundError):
            self.catalog.update_product(999, "MISSING", "Tidak ada", 1000)

    def test_invalid_product_ids_are_rejected(self):
        for value in [0, -1, True, 1.0, "1", None]:
            with self.subTest(value=value):
                with self.assertRaises(ProductValidationError):
                    self.catalog.get_product(value)

    def test_active_status_requires_boolean(self):
        product = self.catalog.create_product("ACT", "Aktif", 1000)
        with self.assertRaises(ProductValidationError):
            self.catalog.set_product_active(product["id"], 1)


if __name__ == "__main__":
    unittest.main()
