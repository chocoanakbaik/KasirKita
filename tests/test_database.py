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
        self.assertEqual(version, 4)

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

    def test_v1_database_migrates_and_preserves_historical_sales(self):
        legacy = connect_database(":memory:")
        try:
            legacy.executescript(
                """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY, sku TEXT NOT NULL, name TEXT NOT NULL,
                    unit_price_rupiah INTEGER NOT NULL, stock_quantity INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY,
                    receipt_number TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    subtotal_rupiah INTEGER NOT NULL,
                    tax_rupiah INTEGER NOT NULL DEFAULT 0,
                    total_rupiah INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE sale_items (
                    id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL, product_id INTEGER,
                    sku_snapshot TEXT NOT NULL, product_name_snapshot TEXT NOT NULL,
                    quantity INTEGER NOT NULL, unit_price_rupiah INTEGER NOT NULL,
                    line_total_rupiah INTEGER NOT NULL
                );
                INSERT INTO sales
                    (receipt_number, status, subtotal_rupiah, tax_rupiah, total_rupiah, created_at)
                VALUES ('OLD-RECEIPT', 'completed', 5000, 0, 5000, '2026-01-01T00:00:00.000Z');
                PRAGMA user_version = 1;
                """
            )
            initialize_database(legacy)
            version = legacy.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, 4)
            row = legacy.execute(
                """
                SELECT receipt_number, total_rupiah, tax_enabled,
                       tax_rate_basis_points, tax_mode, tax_label
                FROM sales WHERE receipt_number = 'OLD-RECEIPT'
                """
            ).fetchone()
            self.assertEqual(tuple(row), ("OLD-RECEIPT", 5000, 0, 0, "exclusive", "PPN"))
        finally:
            legacy.close()

    def test_failed_migration_keeps_old_schema_version(self):
        legacy = connect_database(":memory:")
        try:
            legacy.executescript(
                """
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY,
                    tax_enabled INTEGER NOT NULL DEFAULT 0
                );
                PRAGMA user_version = 1;
                """
            )
            with self.assertRaises(DatabaseError):
                initialize_database(legacy)
            self.assertEqual(
                legacy.execute("PRAGMA user_version").fetchone()[0], 1
            )
        finally:
            legacy.close()

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
