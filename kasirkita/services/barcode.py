"""Offline barcode and internal product-code helpers.

The generated internal code is a store-local identifier, not a GS1 GTIN.
Hardware scanners that emulate a keyboard can send the decoded value to the
cashier barcode field; no vendor SDK or network service is required.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Optional


_INTERNAL_PREFIX = "KK-"
_INTERNAL_WIDTH = 6
_MAX_CODE_LENGTH = 64


class BarcodeValidationError(ValueError):
    """Raised when a barcode value is malformed or conflicts with another product."""


def normalize_barcode(value: object) -> str:
    """Normalize a scanned/manual code without losing leading zeroes."""
    if not isinstance(value, str):
        raise BarcodeValidationError("Barcode harus berupa teks.")
    code = value.strip()
    if not code:
        raise BarcodeValidationError("Barcode tidak boleh kosong.")
    if len(code) > _MAX_CODE_LENGTH:
        raise BarcodeValidationError("Barcode maksimal 64 karakter.")
    if any(ord(character) < 32 for character in code):
        raise BarcodeValidationError("Barcode mengandung karakter kontrol yang tidak valid.")
    return code


def make_internal_code(sequence: object) -> str:
    """Create a stable human-readable local code from a positive sequence number."""
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
        raise BarcodeValidationError("Nomor urut kode internal harus bilangan bulat positif.")
    return _INTERNAL_PREFIX + str(sequence).zfill(_INTERNAL_WIDTH)


def find_product_by_code(connection: sqlite3.Connection, value: object) -> Optional[dict]:
    """Find an active product by its exact SKU/internal code or dedicated barcode."""
    code = normalize_barcode(value)
    row = connection.execute(
        """SELECT id, sku, name, unit_price_rupiah, stock_quantity, is_active
           FROM products
           WHERE sku = ? AND is_active = 1
           ORDER BY id LIMIT 1""",
        (code,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": int(row["id"]),
        "sku": str(row["sku"]),
        "barcode": str(row["sku"]),
        "name": str(row["name"]),
        "unit_price_rupiah": int(row["unit_price_rupiah"]),
        "stock_quantity": int(row["stock_quantity"]),
        "is_active": bool(row["is_active"]),
    }


__all__ = [
    "BarcodeValidationError",
    "find_product_by_code",
    "make_internal_code",
    "normalize_barcode",
]
