"""Tests for SQLite configuration, schema constraints, and rollback behavior."""
import sqlite3
import unittest

from kasirkita.infrastructure.database import (
    DatabaseError,
    connect_database,
    initialize_database,
    transaction,
)


class DatabaseFoundationTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_schema_version_is_initialized(self):
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(version, 1)

    def test_foreign_keys_are_enabled(self):
        enabled = self.connection.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(enabled, 1)

    def test_product_constraints_reject_negative_price(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)",
                ("SKU-1", "Teh", -1),
            )

    def test_product_constraints_reject_blank_sku(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)",
                ("   ", "Teh", 1000),
            )

    def test_duplicate_sku_is_rejected(self):
        values = ("SKU-1", "Teh", 1000)
        self.connection.execute(
            "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)", values
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)",
                values,
            )

    def test_transaction_rolls_back_all_changes_on_error(self):
        with self.assertRaises(RuntimeError):
            with transaction(self.connection):
                self.connection.execute(
                    "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)",
                    ("SKU-ROLLBACK", "Produk sementara", 500),
                )
                raise RuntimeError("simulated failure")

        count = self.connection.execute(
            "SELECT COUNT(*) FROM products WHERE sku = ?", ("SKU-ROLLBACK",)
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_nested_transaction_is_rejected_without_mutating_data(self):
        self.connection.execute("BEGIN")
        try:
            with self.assertRaises(DatabaseError):
                with transaction(self.connection):
                    pass
        finally:
            self.connection.execute("ROLLBACK")

    def test_future_schema_version_is_blocked(self):
        self.connection.execute("PRAGMA user_version = 999")
        with self.assertRaises(DatabaseError):
            initialize_database(self.connection)

    def test_initialization_is_idempotent(self):
        self.connection.execute(
            "INSERT INTO products (sku, name, unit_price_rupiah) VALUES (?, ?, ?)",
            ("SKU-KEEP", "Tetap ada", 1000),
        )
        initialize_database(self.connection)
        count = self.connection.execute(
            "SELECT COUNT(*) FROM products WHERE sku = ?", ("SKU-KEEP",)
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
