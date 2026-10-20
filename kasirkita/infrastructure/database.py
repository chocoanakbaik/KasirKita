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
SCHEMA_VERSION = 4


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


_MIGRATION_1_TO_2_SQL = """
ALTER TABLE sales ADD COLUMN tax_enabled INTEGER NOT NULL DEFAULT 0
    CHECK (tax_enabled IN (0, 1));
ALTER TABLE sales ADD COLUMN tax_rate_basis_points INTEGER NOT NULL DEFAULT 0
    CHECK (tax_rate_basis_points BETWEEN 0 AND 10000);
ALTER TABLE sales ADD COLUMN tax_mode TEXT NOT NULL DEFAULT 'exclusive'
    CHECK (tax_mode IN ('exclusive', 'inclusive'));
ALTER TABLE sales ADD COLUMN tax_label TEXT NOT NULL DEFAULT 'PPN'
    CHECK (length(trim(tax_label)) > 0);
"""


def _execute_script_atomically(connection: sqlite3.Connection, script: str) -> None:
    """Run a schema script as one SQLite transaction."""
    try:
        connection.executescript("BEGIN IMMEDIATE;\n" + script + "\nCOMMIT;")
    except sqlite3.Error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


_MIGRATION_2_TO_3_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 100),
    role TEXT NOT NULL CHECK (role IN ('owner', 'employee')),
    nik_hash TEXT NOT NULL,
    nik_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_iterations INTEGER NOT NULL CHECK (password_iterations >= 100000),
    recovery_hash TEXT,
    recovery_salt TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
"""


_MIGRATION_3_TO_4_SQL = """
ALTER TABLE products ADD COLUMN unit_cost_rupiah INTEGER NOT NULL DEFAULT 0
    CHECK (unit_cost_rupiah >= 0);
ALTER TABLE sale_items ADD COLUMN unit_cost_rupiah INTEGER NOT NULL DEFAULT 0
    CHECK (unit_cost_rupiah >= 0);
ALTER TABLE sales ADD COLUMN discount_rupiah INTEGER NOT NULL DEFAULT 0
    CHECK (discount_rupiah >= 0);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL CHECK (length(trim(category)) BETWEEN 1 AND 80),
    description TEXT NOT NULL CHECK (length(trim(description)) BETWEEN 1 AND 200),
    amount_rupiah INTEGER NOT NULL CHECK (amount_rupiah > 0),
    expense_date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    is_voided INTEGER NOT NULL DEFAULT 0 CHECK (is_voided IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE RESTRICT,
    refund_rupiah INTEGER NOT NULL CHECK (refund_rupiah >= 0),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS return_items (
    id INTEGER PRIMARY KEY,
    return_id INTEGER NOT NULL REFERENCES returns(id) ON DELETE RESTRICT,
    sale_item_id INTEGER NOT NULL REFERENCES sale_items(id) ON DELETE RESTRICT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    refund_rupiah INTEGER NOT NULL CHECK (refund_rupiah >= 0)
);
CREATE INDEX IF NOT EXISTS idx_returns_sale_id ON returns(sale_id);
CREATE INDEX IF NOT EXISTS idx_return_items_sale_item_id ON return_items(sale_item_id);
"""


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the schema and apply every required migration in order."""
    try:
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise DatabaseError(
                "The database was created by a newer KasirKita version. "
                "Opening it with this version is blocked to protect the data."
            )

        if current_version == 0:
            _execute_script_atomically(
                connection,
                _SCHEMA_SQL + "\nPRAGMA user_version = 1;",
            )
            current_version = 1

        if current_version == 1:
            _execute_script_atomically(
                connection,
                _MIGRATION_1_TO_2_SQL + "\nPRAGMA user_version = 2;",
            )
            current_version = 2

        if current_version == 2:
            _execute_script_atomically(
                connection,
                _MIGRATION_2_TO_3_SQL + "\nPRAGMA user_version = 3;",
            )
            current_version = 3

        if current_version == 3:
            _execute_script_atomically(
                connection,
                _MIGRATION_3_TO_4_SQL + "\nPRAGMA user_version = 4;",
            )
            current_version = 4

        if current_version != SCHEMA_VERSION:
            raise DatabaseError(
                "No migration path exists for database schema version "
                + str(current_version)
                + "."
            )
    except DatabaseError:
        raise
    except sqlite3.Error as exc:
        raise DatabaseError("The KasirKita database schema could not be initialized.") from exc
