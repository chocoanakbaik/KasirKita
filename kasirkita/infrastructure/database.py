"""SQLite lifecycle and schema initialization for KasirKita.

This module intentionally contains persistence mechanics only. Business decisions
such as tax policy and checkout rules belong in domain/services modules.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Union

DatabasePath = Union[str, Path]
SCHEMA_VERSION = 1


class DatabaseError(RuntimeError):
    """Raised when the database cannot be initialized or used safely."""


def connect_database(path: DatabasePath) -> sqlite3.Connection:
    """Open a configured SQLite connection.

    Parent directories are created for file-backed databases. The special path
    ':memory:' remains in-memory and is not treated as a filesystem path.
    """
    if str(path) == ":memory:":
        database_name = ":memory:"
    else:
        database_path = Path(path).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_name = str(database_path)

    try:
        connection = sqlite3.connect(
            database_name,
            timeout=5.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA trusted_schema = OFF")
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        if enabled != 1:
            connection.close()
            raise DatabaseError("SQLite foreign-key enforcement could not be enabled.")
        return connection
    except (OSError, sqlite3.Error) as exc:
        raise DatabaseError("Unable to open the KasirKita database.") from exc


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a group of database statements atomically.

    The connection must not already be inside a transaction. Nested transaction
    semantics should be introduced explicitly with savepoints if ever required.
    """
    if connection.in_transaction:
        raise DatabaseError("Nested transactions are not supported by this helper.")

    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.execute("COMMIT")
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit_price_rupiah INTEGER NOT NULL CHECK (unit_price_rupiah >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (length(trim(sku)) > 0),
    CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    receipt_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('completed', 'voided')),
    subtotal_rupiah INTEGER NOT NULL CHECK (subtotal_rupiah >= 0),
    tax_rupiah INTEGER NOT NULL DEFAULT 0 CHECK (tax_rupiah >= 0),
    total_rupiah INTEGER NOT NULL CHECK (total_rupiah >= 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (total_rupiah = subtotal_rupiah + tax_rupiah),
    CHECK (length(trim(receipt_number)) > 0)
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE RESTRICT,
    product_id INTEGER REFERENCES products(id) ON DELETE RESTRICT,
    sku_snapshot TEXT NOT NULL,
    product_name_snapshot TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_rupiah INTEGER NOT NULL CHECK (unit_price_rupiah >= 0),
    line_total_rupiah INTEGER NOT NULL CHECK (line_total_rupiah >= 0),
    CHECK (line_total_rupiah = quantity * unit_price_rupiah),
    CHECK (length(trim(sku_snapshot)) > 0),
    CHECK (length(trim(product_name_snapshot)) > 0)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE RESTRICT,
    method TEXT NOT NULL CHECK (length(trim(method)) > 0),
    amount_rupiah INTEGER NOT NULL CHECK (amount_rupiah > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    sale_id INTEGER REFERENCES sales(id) ON DELETE RESTRICT,
    movement_type TEXT NOT NULL CHECK (
        movement_type IN ('sale', 'adjustment_in', 'adjustment_out', 'sale_void')
    ),
    quantity_delta INTEGER NOT NULL CHECK (quantity_delta <> 0),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (
        (movement_type IN ('sale', 'adjustment_out') AND quantity_delta < 0)
        OR (movement_type IN ('adjustment_in', 'sale_void') AND quantity_delta > 0)
    )
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY CHECK (length(trim(key)) > 0),
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_payments_sale_id ON payments(sale_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_sale_id ON stock_movements(sale_id);
"""


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the initial schema or reject a schema version this app cannot read."""
    try:
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise DatabaseError(
                "The database was created by a newer KasirKita version. "
                "Opening it with this version is blocked to protect the data."
            )
        if current_version == SCHEMA_VERSION:
            return
        if current_version != 0:
            raise DatabaseError(
                "No migration path exists for database schema version "
                + str(current_version)
                + "."
            )

        with transaction(connection):
            connection.executescript(_SCHEMA_SQL)
            connection.execute("PRAGMA user_version = 1")
    except DatabaseError:
        raise
    except sqlite3.Error as exc:
        raise DatabaseError("The KasirKita database schema could not be initialized.") from exc
