"""SQLite persistence adapter for the product catalogue."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from kasirkita.infrastructure.database import transaction


class DuplicateSKUError(RuntimeError):
    """Raised when a SKU already exists in the catalogue."""


class ProductNotFoundError(LookupError):
    """Raised when a requested product does not exist."""


class ProductRepository:
    """Persist and retrieve product records using a caller-owned connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @staticmethod
    def _to_product(row: sqlite3.Row) -> dict:
        return {
            "id": int(row["id"]),
            "sku": str(row["sku"]),
            "name": str(row["name"]),
            "unit_price_rupiah": int(row["unit_price_rupiah"]),
            "stock_quantity": int(row["stock_quantity"]),
            "is_active": bool(row["is_active"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def create(
        self,
        sku: str,
        name: str,
        unit_price_rupiah: int,
        stock_quantity: int,
    ) -> dict:
        try:
            with transaction(self._connection):
                cursor = self._connection.execute(
                    """
                    INSERT INTO products (sku, name, unit_price_rupiah, stock_quantity)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sku, name, unit_price_rupiah, stock_quantity),
                )
                product_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            if "products.sku" in str(exc).lower() or "unique constraint failed" in str(exc).lower():
                raise DuplicateSKUError("SKU tersebut sudah digunakan.") from exc
            raise

        product = self.get_by_id(product_id)
        if product is None:
            raise RuntimeError("Product was committed but could not be retrieved.")
        return product

    def get_by_id(self, product_id: int) -> Optional[dict]:
        row = self._connection.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return self._to_product(row) if row is not None else None

    def get_by_sku(self, sku: str) -> Optional[dict]:
        row = self._connection.execute(
            "SELECT * FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        return self._to_product(row) if row is not None else None

    def list_products(
        self,
        search: str = "",
        include_inactive: bool = False,
    ) -> List[dict]:
        conditions = []
        parameters = []
        if not include_inactive:
            conditions.append("is_active = 1")
        search_text = search.strip()
        if search_text:
            conditions.append("(sku LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\')")
            escaped = (
                search_text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = "%" + escaped + "%"
            parameters.extend((pattern, pattern))

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = self._connection.execute(
            "SELECT * FROM products" + where_clause + " ORDER BY name COLLATE NOCASE, id",
            tuple(parameters),
        ).fetchall()
        return [self._to_product(row) for row in rows]

    def update_details(
        self,
        product_id: int,
        sku: str,
        name: str,
        unit_price_rupiah: int,
    ) -> dict:
        try:
            with transaction(self._connection):
                cursor = self._connection.execute(
                    """
                    UPDATE products
                    SET sku = ?, name = ?, unit_price_rupiah = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ?
                    """,
                    (sku, name, unit_price_rupiah, product_id),
                )
                if cursor.rowcount != 1:
                    raise ProductNotFoundError("Produk tidak ditemukan.")
        except sqlite3.IntegrityError as exc:
            if "products.sku" in str(exc).lower() or "unique constraint failed" in str(exc).lower():
                raise DuplicateSKUError("SKU tersebut sudah digunakan.") from exc
            raise

        product = self.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError("Produk tidak ditemukan.")
        return product

    def set_active(self, product_id: int, is_active: bool) -> dict:
        with transaction(self._connection):
            cursor = self._connection.execute(
                """
                UPDATE products
                SET is_active = ?,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ?
                """,
                (1 if is_active else 0, product_id),
            )
            if cursor.rowcount != 1:
                raise ProductNotFoundError("Produk tidak ditemukan.")

        product = self.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError("Produk tidak ditemukan.")
        return product
