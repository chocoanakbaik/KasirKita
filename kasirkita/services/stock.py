"""Validated stock-adjustment use case with an audit trail."""
from __future__ import annotations

import sqlite3

from kasirkita.infrastructure.database import transaction
from kasirkita.infrastructure.product_repository import ProductNotFoundError


MAX_STOCK_QUANTITY = 2_147_483_647
MAX_NOTE_LENGTH = 200


class StockAdjustmentError(ValueError):
    """Raised when a requested stock adjustment cannot be applied."""


class InsufficientStockForAdjustmentError(StockAdjustmentError):
    """Raised when a stock reduction would make inventory negative."""


class StockService:
    """Apply manual inventory adjustments and record them atomically."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def adjust_stock(
        self,
        product_id: object,
        quantity_delta: object,
        note: object,
    ) -> dict:
        valid_id = self._validate_id(product_id)
        delta = self._validate_delta(quantity_delta)
        cleaned_note = self._validate_note(note)
        movement_type = "adjustment_in" if delta > 0 else "adjustment_out"

        with transaction(self._connection):
            row = self._connection.execute(
                "SELECT id, stock_quantity FROM products WHERE id = ?",
                (valid_id,),
            ).fetchone()
            if row is None:
                raise ProductNotFoundError("Produk tidak ditemukan.")

            current_stock = int(row["stock_quantity"])
            next_stock = current_stock + delta
            if next_stock < 0:
                raise InsufficientStockForAdjustmentError(
                    "Pengurangan stok melebihi stok yang tersedia."
                )
            if next_stock > MAX_STOCK_QUANTITY:
                raise StockAdjustmentError("Stok hasil penyesuaian melebihi batas yang didukung.")

            cursor = self._connection.execute(
                """
                UPDATE products
                SET stock_quantity = ?,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ? AND stock_quantity = ?
                """,
                (next_stock, valid_id, current_stock),
            )
            if cursor.rowcount != 1:
                raise StockAdjustmentError(
                    "Stok berubah saat penyesuaian. Muat ulang data lalu coba lagi."
                )

            self._connection.execute(
                """
                INSERT INTO stock_movements (
                    product_id, sale_id, movement_type, quantity_delta, note
                ) VALUES (?, NULL, ?, ?, ?)
                """,
                (valid_id, movement_type, delta, cleaned_note),
            )

        result = self._connection.execute(
            "SELECT id, sku, name, unit_price_rupiah, stock_quantity, is_active, created_at, updated_at "
            "FROM products WHERE id = ?",
            (valid_id,),
        ).fetchone()
        if result is None:
            raise ProductNotFoundError("Produk tidak ditemukan setelah penyesuaian.")
        return {
            "id": int(result["id"]),
            "sku": str(result["sku"]),
            "name": str(result["name"]),
            "unit_price_rupiah": int(result["unit_price_rupiah"]),
            "stock_quantity": int(result["stock_quantity"]),
            "is_active": bool(result["is_active"]),
            "created_at": str(result["created_at"]),
            "updated_at": str(result["updated_at"]),
        }

    @staticmethod
    def _validate_id(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise StockAdjustmentError("ID produk tidak valid.")
        return value

    @staticmethod
    def _validate_delta(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise StockAdjustmentError("Perubahan stok harus berupa bilangan bulat.")
        if value == 0:
            raise StockAdjustmentError("Perubahan stok tidak boleh nol.")
        if abs(value) > MAX_STOCK_QUANTITY:
            raise StockAdjustmentError("Perubahan stok melebihi batas yang didukung.")
        return value

    @staticmethod
    def _validate_note(value: object) -> str:
        if not isinstance(value, str):
            raise StockAdjustmentError("Alasan penyesuaian harus berupa teks.")
        cleaned = value.strip()
        if not cleaned:
            raise StockAdjustmentError("Alasan penyesuaian wajib diisi.")
        if len(cleaned) > MAX_NOTE_LENGTH:
            raise StockAdjustmentError(
                "Alasan penyesuaian maksimal " + str(MAX_NOTE_LENGTH) + " karakter."
            )
        return cleaned


__all__ = [
    "InsufficientStockForAdjustmentError",
    "StockAdjustmentError",
    "StockService",
]
