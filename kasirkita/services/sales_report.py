"""Deterministic sales summaries derived from persisted completed sales."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import sqlite3
from typing import List


class SalesReportValidationError(ValueError):
    """Raised when a report date range is invalid."""


def _parse_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise SalesReportValidationError(field + " harus berformat YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SalesReportValidationError(field + " harus berformat YYYY-MM-DD.") from exc
    if parsed.isoformat() != value:
        raise SalesReportValidationError(field + " harus berformat YYYY-MM-DD.")
    return parsed


class SalesReportService:
    """Read-only reports; all totals come from persisted sale snapshots."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def summarize(self, start_date: object, end_date: object) -> dict:
        start = _parse_date(start_date, "Tanggal awal")
        end = _parse_date(end_date, "Tanggal akhir")
        if end < start:
            raise SalesReportValidationError("Tanggal akhir tidak boleh sebelum tanggal awal.")
        if (end - start).days > 3660:
            raise SalesReportValidationError("Rentang laporan maksimal 10 tahun.")

        start_bound = start.isoformat() + "T00:00:00.000Z"
        end_bound = (end + timedelta(days=1)).isoformat() + "T00:00:00.000Z"
        totals = self._connection.execute(
            """
            SELECT COUNT(*) AS sales_count,
                   COALESCE(SUM(total_rupiah), 0) AS total_rupiah,
                   COALESCE(SUM(tax_rupiah), 0) AS tax_rupiah
            FROM sales
            WHERE status = 'completed' AND created_at >= ? AND created_at < ?
            """,
            (start_bound, end_bound),
        ).fetchone()
        items = self._connection.execute(
            """
            SELECT COALESCE(SUM(si.quantity), 0) AS items_sold
            FROM sale_items AS si
            INNER JOIN sales AS s ON s.id = si.sale_id
            WHERE s.status = 'completed' AND s.created_at >= ? AND s.created_at < ?
            """,
            (start_bound, end_bound),
        ).fetchone()
        daily_rows = self._connection.execute(
            """
            SELECT substr(created_at, 1, 10) AS sale_date,
                   COUNT(*) AS sales_count,
                   COALESCE(SUM(total_rupiah), 0) AS total_rupiah
            FROM sales
            WHERE status = 'completed' AND created_at >= ? AND created_at < ?
            GROUP BY substr(created_at, 1, 10)
            ORDER BY sale_date
            """,
            (start_bound, end_bound),
        ).fetchall()

        count = int(totals["sales_count"])
        revenue = int(totals["total_rupiah"])
        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "sales_count": count,
            "total_rupiah": revenue,
            "tax_rupiah": int(totals["tax_rupiah"]),
            "items_sold": int(items["items_sold"]),
            "average_sale_rupiah": revenue // count if count else 0,
            "daily": [
                {
                    "date": str(row["sale_date"]),
                    "sales_count": int(row["sales_count"]),
                    "total_rupiah": int(row["total_rupiah"]),
                }
                for row in daily_rows
            ],
        }


__all__ = ["SalesReportService", "SalesReportValidationError"]
