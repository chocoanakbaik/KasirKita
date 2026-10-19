"""Deterministic sales summaries derived from persisted completed sales."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
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

        # Date inputs represent the computer's local calendar. Convert local
        # midnight boundaries to UTC because database timestamps are stored in UTC.
        # Keep millisecond precision consistent with SQLite strftime('%f') values.
        start_utc = datetime.combine(start, time.min).astimezone(timezone.utc)
        end_utc = datetime.combine(end + timedelta(days=1), time.min).astimezone(timezone.utc)

        def _utc_bound(value: datetime) -> str:
            return value.strftime("%Y-%m-%dT%H:%M:%S.") + format(
                value.microsecond // 1000, "03d"
            ) + "Z"

        start_bound = _utc_bound(start_utc)
        end_bound = _utc_bound(end_utc)
        sale_rows = self._connection.execute(
            """
            SELECT id, total_rupiah, tax_rupiah, created_at
            FROM sales
            WHERE status = 'completed' AND created_at >= ? AND created_at < ?
            ORDER BY created_at, id
            """,
            (start_bound, end_bound),
        ).fetchall()

        daily_data = {}
        total_revenue = 0
        total_tax = 0
        for row in sale_rows:
            timestamp = str(row["created_at"])
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            local_date = parsed_timestamp.astimezone().date().isoformat()
            day = daily_data.setdefault(local_date, {"sales_count": 0, "total_rupiah": 0})
            day["sales_count"] += 1
            day["total_rupiah"] += int(row["total_rupiah"])
            total_revenue += int(row["total_rupiah"])
            total_tax += int(row["tax_rupiah"])

        item_rows = self._connection.execute(
            """
            SELECT si.quantity
            FROM sale_items AS si
            INNER JOIN sales AS s ON s.id = si.sale_id
            WHERE s.status = 'completed' AND s.created_at >= ? AND s.created_at < ?
            """,
            (start_bound, end_bound),
        ).fetchall()
        items_sold = sum(int(row["quantity"]) for row in item_rows)
        count = len(sale_rows)
        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "sales_count": count,
            "total_rupiah": total_revenue,
            "tax_rupiah": total_tax,
            "items_sold": items_sold,
            "average_sale_rupiah": total_revenue // count if count else 0,
            "daily": [
                {
                    "date": day,
                    "sales_count": values["sales_count"],
                    "total_rupiah": values["total_rupiah"],
                }
                for day, values in sorted(daily_data.items())
            ],
        }


__all__ = ["SalesReportService", "SalesReportValidationError"]
