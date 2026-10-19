"""Tests for backup creation, restore validation, and data preservation."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from kasirkita.infrastructure.backup import BackupError, DatabaseBackupService
from kasirkita.infrastructure.database import connect_database, initialize_database


class DatabaseBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.connection.execute(
            """
            INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
            VALUES ('BASE', 'Data awal', 1200, 7)
            """
        )
        self.backups = DatabaseBackupService(self.connection)

    def tearDown(self):
        self.connection.close()
        self.temp_dir.cleanup()

    def product_name(self, sku):
        row = self.connection.execute(
            "SELECT name FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        return row[0] if row else None

    def test_create_backup_produces_valid_database(self):
        path = self.backups.create_backup(str(self.directory / "backup.sqlite3"))
        self.assertTrue(path.is_file())
        with closing(sqlite3.connect(str(path))) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(
                connection.execute("SELECT name FROM products WHERE sku = 'BASE'").fetchone()[0],
                "Data awal",
            )

    def test_restore_replaces_live_data_from_valid_backup(self):
        backup_path = self.backups.create_backup(str(self.directory / "restore.sqlite3"))
        self.connection.execute(
            "INSERT INTO products (sku, name, unit_price_rupiah) VALUES ('NEW', 'Data baru', 3000)"
        )
        self.backups.restore_backup(str(backup_path))
        self.assertEqual(self.product_name("BASE"), "Data awal")
        self.assertIsNone(self.product_name("NEW"))

    def test_invalid_backup_is_rejected_without_changing_live_data(self):
        invalid_path = self.directory / "invalid.sqlite3"
        with closing(sqlite3.connect(str(invalid_path))) as connection:
            connection.execute("CREATE TABLE not_kasirkita (value TEXT)")
            connection.execute("PRAGMA user_version = 1")
        with self.assertRaises(BackupError):
            self.backups.restore_backup(str(invalid_path))
        self.assertEqual(self.product_name("BASE"), "Data awal")

    def test_missing_backup_is_rejected(self):
        with self.assertRaises(BackupError):
            self.backups.restore_backup(str(self.directory / "missing.sqlite3"))

    def test_restore_is_blocked_during_active_transaction(self):
        backup_path = self.backups.create_backup(str(self.directory / "safe.sqlite3"))
        self.connection.execute("BEGIN")
        try:
            with self.assertRaises(BackupError):
                self.backups.restore_backup(str(backup_path))
        finally:
            self.connection.execute("ROLLBACK")


if __name__ == "__main__":
    unittest.main()
