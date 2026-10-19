"""Read-only sales history and receipt-detail queries."""
from __future__ import annotations

import sqlite3
from typing import List, Optional


class SalesHistoryValidationError(ValueError):
    """Raised when pagination or search arguments are invalid."""


class SalesHistoryService:
    """Query persisted sales without recomputing historical transaction totals."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_sales(
        self,
        search: object = "",
        limit: object = 100,
        offset: object = 0,
    ) -> List[dict]:
        if not isinstance(search, str):
            raise SalesHistoryValidationError("Pencarian riwayat harus berupa teks.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise SalesHistoryValidationError("Batas hasil harus antara 1 sampai 500.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise SalesHistoryValidationError("Posisi halaman tidak valid.")

        conditions = []
        parameters = []
        search_text = search.strip()
        if search_text:
            conditions.append("instr(lower(receipt_number), lower(?)) > 0")
            parameters.append(search_text)
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        parameters.extend((limit, offset))
        rows = self._connection.execute(
            """
            SELECT id, receipt_number, status, subtotal_rupiah, tax_rupiah,
                   total_rupiah, tax_enabled, tax_rate_basis_points, tax_mode, tax_label, created_at
            FROM sales
            """
            + where_clause
            + " ORDER BY id DESC LIMIT ? OFFSET ?",
            tuple(parameters),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "receipt_number": str(row["receipt_number"]),
                "status": str(row["status"]),
                "subtotal_rupiah": int(row["subtotal_rupiah"]),
                "tax_rupiah": int(row["tax_rupiah"]),
                "total_rupiah": int(row["total_rupiah"]),
                "tax_enabled": bool(row["tax_enabled"]),
                "tax_rate_basis_points": int(row["tax_rate_basis_points"]),
                "tax_mode": str(row["tax_mode"]),
                "tax_label": str(row["tax_label"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def get_sale_detail(self, sale_id: object) -> Optional[dict]:
        if isinstance(sale_id, bool) or not isinstance(sale_id, int) or sale_id <= 0:
            raise SalesHistoryValidationError("ID transaksi tidak valid.")

        row = self._connection.execute(
            """
            SELECT id, receipt_number, status, subtotal_rupiah, tax_rupiah,
                   total_rupiah, tax_enabled, tax_rate_basis_points, tax_mode, tax_label, created_at
            FROM sales
            WHERE id = ?
            """,
            (sale_id,),
        ).fetchone()
        if row is None:
            return None

        lines = self._connection.execute(
            """
            SELECT sku_snapshot, product_name_snapshot, quantity,
                   unit_price_rupiah, line_total_rupiah
            FROM sale_items
            WHERE sale_id = ?
            ORDER BY id
            """,
            (sale_id,),
        ).fetchall()
        payments = self._connection.execute(
            """
            SELECT method, amount_rupiah, created_at
            FROM payments
            WHERE sale_id = ?
            ORDER BY id
            """,
            (sale_id,),
        ).fetchall()

        return {
            "id": int(row["id"]),
            "receipt_number": str(row["receipt_number"]),
            "status": str(row["status"]),
            "subtotal_rupiah": int(row["subtotal_rupiah"]),
            "tax_rupiah": int(row["tax_rupiah"]),
            "total_rupiah": int(row["total_rupiah"]),
            "tax_enabled": bool(row["tax_enabled"]),
            "tax_rate_basis_points": int(row["tax_rate_basis_points"]),
            "tax_mode": str(row["tax_mode"]),
            "tax_label": str(row["tax_label"]),
            "created_at": str(row["created_at"]),
            "items": [
                {
                    "sku": str(line["sku_snapshot"]),
                    "name": str(line["product_name_snapshot"]),
                    "quantity": int(line["quantity"]),
                    "unit_price_rupiah": int(line["unit_price_rupiah"]),
                    "line_total_rupiah": int(line["line_total_rupiah"]),
                }
                for line in lines
            ],
            "payments": [
                {
                    "method": str(payment["method"]),
                    "amount_rupiah": int(payment["amount_rupiah"]),
                    "created_at": str(payment["created_at"]),
                }
                for payment in payments
            ],
        }


__all__ = ["SalesHistoryService", "SalesHistoryValidationError"]
