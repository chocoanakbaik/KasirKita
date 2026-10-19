"""Atomic checkout use case with optional, snapshotted sales tax."""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Dict, List, Mapping, Sequence
from uuid import uuid4

from kasirkita.domain.tax import TaxCalculationError, calculate_tax
from kasirkita.infrastructure.database import transaction
from kasirkita.services.tax_settings import TaxSettingsError, TaxSettingsService


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
    """Preview and finalize cash sales using current prices and tax settings."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._tax_settings = TaxSettingsService(connection)

    def preview(self, items: Sequence[Mapping[str, object]]) -> dict:
        """Return current cart totals without reserving stock or writing data."""
        normalized_items = self._normalize_items(items)
        lines, gross_amount = self._price_cart(normalized_items)
        tax_config = self._read_tax_config()
        totals = self._calculate_totals(gross_amount, tax_config)
        return {
            **totals,
            "gross_amount_rupiah": gross_amount,
            "tax_enabled": tax_config["enabled"],
            "tax_rate_basis_points": tax_config["rate_basis_points"],
            "tax_mode": tax_config["mode"],
            "tax_label": tax_config["label"],
            "items": lines,
        }

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

        receipt_number = (
            "KK-"
            + datetime.now(timezone.utc).strftime("%Y%m%d")
            + "-"
            + uuid4().hex[:12].upper()
        )

        with transaction(self._connection):
            result_lines, gross_amount = self._price_cart(normalized_items)
            tax_config = self._read_tax_config()
            totals = self._calculate_totals(gross_amount, tax_config)
            subtotal = totals["subtotal_rupiah"]
            tax = totals["tax_rupiah"]
            total = totals["total_rupiah"]

            if total > 0 and received < total:
                raise PaymentError("Uang yang diterima belum mencukupi total transaksi.")
            change = received - total

            sale_cursor = self._connection.execute(
                """
                INSERT INTO sales (
                    receipt_number, status, subtotal_rupiah, tax_rupiah, total_rupiah,
                    tax_enabled, tax_rate_basis_points, tax_mode, tax_label
                )
                VALUES (?, 'completed', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_number,
                    subtotal,
                    tax,
                    total,
                    1 if tax_config["enabled"] else 0,
                    tax_config["rate_basis_points"],
                    tax_config["mode"],
                    tax_config["label"],
                ),
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
            "tax_rupiah": tax,
            "total_rupiah": total,
            "tax_enabled": tax_config["enabled"],
            "tax_rate_basis_points": tax_config["rate_basis_points"],
            "tax_mode": tax_config["mode"],
            "tax_label": tax_config["label"],
            "amount_received_rupiah": received,
            "change_rupiah": change,
            "payment_method": method,
            "items": result_lines,
        }

    def _price_cart(self, normalized_items: Sequence[tuple[int, int]]) -> tuple[List[dict], int]:
        lines: List[dict] = []
        gross_amount = 0
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
            if int(row["stock_quantity"]) < quantity:
                raise InsufficientStockError(
                    "Stok produk " + str(row["name"]) + " tidak mencukupi."
                )

            unit_price = int(row["unit_price_rupiah"])
            line_total = unit_price * quantity
            if line_total > MAX_MONEY_RUPIAH:
                raise InvalidCartError("Nilai salah satu baris transaksi terlalu besar.")
            gross_amount += line_total
            if gross_amount > MAX_MONEY_RUPIAH:
                raise InvalidCartError("Total transaksi melebihi batas yang didukung.")

            lines.append(
                {
                    "product_id": int(row["id"]),
                    "sku": str(row["sku"]),
                    "name": str(row["name"]),
                    "quantity": quantity,
                    "unit_price_rupiah": unit_price,
                    "line_total_rupiah": line_total,
                }
            )
        return lines, gross_amount

    def _read_tax_config(self) -> dict:
        try:
            return self._tax_settings.get_config()
        except TaxSettingsError as exc:
            raise CheckoutError(
                "Pengaturan pajak tidak valid. Periksa pengaturan sebelum bertransaksi."
            ) from exc

    @staticmethod
    def _calculate_totals(gross_amount: int, tax_config: dict) -> dict:
        try:
            return calculate_tax(gross_amount, tax_config)
        except TaxCalculationError as exc:
            raise CheckoutError(
                "Total transaksi tidak dapat dihitung dengan pengaturan saat ini."
            ) from exc

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
