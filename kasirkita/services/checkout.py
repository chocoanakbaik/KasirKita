"""Atomic checkout use case for cash sales.

Tax is intentionally disabled in this first checkout slice. Tax behavior must be
implemented only after the product requirements define inclusive/exclusive
pricing, rounding, and historical tax snapshots.
"""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Dict, List, Mapping, Sequence
from uuid import uuid4

from kasirkita.infrastructure.database import transaction


MAX_QUANTITY_PER_LINE = 2_147_483_647
MAX_MONEY_RUPIAH = 9_000_000_000_000_000
MAX_CART_LINES = 500


class CheckoutError(RuntimeError):
    """Base class for checkout failures safe to present to the user."""


class InvalidCartError(CheckoutError):
    """Raised when cart contents are missing or invalid."""


class InsufficientStockError(CheckoutError):
    """Raised when a product does not have enough stock."""


class ProductUnavailableError(CheckoutError):
    """Raised when a product is missing or inactive."""


class PaymentError(CheckoutError):
    """Raised when payment input is invalid or insufficient."""


def _positive_integer(value: object, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidCartError(label + " harus berupa bilangan bulat.")
    if value <= 0:
        raise InvalidCartError(label + " harus lebih besar dari nol.")
    if value > maximum:
        raise InvalidCartError(label + " melebihi batas yang didukung.")
    return value


def _money_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PaymentError("Uang yang diterima harus berupa bilangan bulat rupiah.")
    if value < 0:
        raise PaymentError("Uang yang diterima tidak boleh negatif.")
    if value > MAX_MONEY_RUPIAH:
        raise PaymentError("Uang yang diterima melebihi batas yang didukung.")
    return value


class CheckoutService:
    """Finalize a cash sale and stock deductions as one database transaction."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def checkout(
        self,
        items: Sequence[Mapping[str, object]],
        amount_received_rupiah: object,
        payment_method: str = "cash",
    ) -> dict:
        normalized_items = self._normalize_items(items)
        received = _money_integer(amount_received_rupiah)
        if not isinstance(payment_method, str) or payment_method.strip().lower() != "cash":
            raise PaymentError("Metode pembayaran yang tersedia saat ini adalah tunai.")
        method = "cash"

        # A short random suffix makes receipt identifiers safe across restarts.
        receipt_number = (
            "KK-"
            + datetime.now(timezone.utc).strftime("%Y%m%d")
            + "-"
            + uuid4().hex[:12].upper()
        )

        result_lines: List[dict] = []
        subtotal = 0
        change = 0

        with transaction(self._connection):
            for product_id, quantity in normalized_items:
                row = self._connection.execute(
                    """
                    SELECT id, sku, name, unit_price_rupiah, stock_quantity, is_active
                    FROM products
                    WHERE id = ?
                    """,
                    (product_id,),
                ).fetchone()
                if row is None or int(row["is_active"]) != 1:
                    raise ProductUnavailableError(
                        "Produk dengan ID " + str(product_id) + " tidak tersedia."
                    )

                stock = int(row["stock_quantity"])
                if stock < quantity:
                    raise InsufficientStockError(
                        "Stok produk " + str(row["name"]) + " tidak mencukupi."
                    )

                unit_price = int(row["unit_price_rupiah"])
                line_total = unit_price * quantity
                if line_total > MAX_MONEY_RUPIAH:
                    raise InvalidCartError("Nilai salah satu baris transaksi terlalu besar.")
                subtotal += line_total
                if subtotal > MAX_MONEY_RUPIAH:
                    raise InvalidCartError("Total transaksi melebihi batas yang didukung.")

                result_lines.append(
                    {
                        "product_id": int(row["id"]),
                        "sku": str(row["sku"]),
                        "name": str(row["name"]),
                        "quantity": quantity,
                        "unit_price_rupiah": unit_price,
                        "line_total_rupiah": line_total,
                    }
                )

            total = subtotal  # Tax remains off until tax requirements are approved.
            if total > 0 and received < total:
                raise PaymentError("Uang yang diterima belum mencukupi total transaksi.")
            change = received - total if total > 0 else 0

            sale_cursor = self._connection.execute(
                """
                INSERT INTO sales
                    (receipt_number, status, subtotal_rupiah, tax_rupiah, total_rupiah)
                VALUES (?, 'completed', ?, 0, ?)
                """,
                (receipt_number, subtotal, total),
            )
            sale_id = int(sale_cursor.lastrowid)

            for line in result_lines:
                quantity = int(line["quantity"])
                product_id = int(line["product_id"])
                cursor = self._connection.execute(
                    """
                    UPDATE products
                    SET stock_quantity = stock_quantity - ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ? AND is_active = 1 AND stock_quantity >= ?
                    """,
                    (quantity, product_id, quantity),
                )
                if cursor.rowcount != 1:
                    # Defensive concurrency guard; BEGIN IMMEDIATE serializes writers,
                    # while the conditional update protects the invariant itself.
                    raise InsufficientStockError(
                        "Stok berubah selama transaksi. Silakan periksa ulang keranjang."
                    )

                self._connection.execute(
                    """
                    INSERT INTO sale_items (
                        sale_id, product_id, sku_snapshot, product_name_snapshot,
                        quantity, unit_price_rupiah, line_total_rupiah
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        product_id,
                        line["sku"],
                        line["name"],
                        quantity,
                        line["unit_price_rupiah"],
                        line["line_total_rupiah"],
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO stock_movements (
                        product_id, sale_id, movement_type, quantity_delta, note
                    ) VALUES (?, ?, 'sale', ?, ?)
                    """,
                    (
                        product_id,
                        sale_id,
                        -quantity,
                        "Penjualan " + receipt_number,
                    ),
                )

            if total > 0:
                self._connection.execute(
                    """
                    INSERT INTO payments (sale_id, method, amount_rupiah)
                    VALUES (?, ?, ?)
                    """,
                    (sale_id, method, total),
                )

        return {
            "sale_id": sale_id,
            "receipt_number": receipt_number,
            "status": "completed",
            "subtotal_rupiah": subtotal,
            "tax_rupiah": 0,
            "total_rupiah": subtotal,
            "amount_received_rupiah": received,
            "change_rupiah": change,
            "payment_method": method,
            "items": result_lines,
        }

    @staticmethod
    def _normalize_items(
        items: Sequence[Mapping[str, object]],
    ) -> List[tuple[int, int]]:
        if not isinstance(items, (list, tuple)) or not items:
            raise InvalidCartError("Keranjang tidak boleh kosong.")
        if len(items) > MAX_CART_LINES:
            raise InvalidCartError("Jumlah baris keranjang melebihi batas.")

        combined: Dict[int, int] = {}
        for item in items:
            if not isinstance(item, Mapping):
                raise InvalidCartError("Format item keranjang tidak valid.")
            product_id = _positive_integer(
                item.get("product_id"), "ID produk", MAX_QUANTITY_PER_LINE
            )
            quantity = _positive_integer(
                item.get("quantity"), "Kuantitas", MAX_QUANTITY_PER_LINE
            )
            combined[product_id] = combined.get(product_id, 0) + quantity
            if combined[product_id] > MAX_QUANTITY_PER_LINE:
                raise InvalidCartError("Jumlah produk melebihi batas yang didukung.")

        return list(combined.items())


__all__ = [
    "CheckoutError",
    "CheckoutService",
    "InsufficientStockError",
    "InvalidCartError",
    "PaymentError",
    "ProductUnavailableError",
]
