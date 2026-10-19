"""CSV export for the date-scoped sales report."""
from __future__ import annotations

import csv
import os
from pathlib import Path
import tempfile
from typing import Mapping


class SalesReportExportError(RuntimeError):
    """Raised when a report cannot be exported safely."""


def export_sales_report_csv(report: Mapping[str, object], destination: object) -> Path:
    """Write a validated report as an Excel-friendly UTF-8 CSV file.

    The file is written to a temporary file in the destination directory and
    atomically replaced into place only after the CSV writer closes cleanly.
    """
    required = (
        "start_date",
        "end_date",
        "sales_count",
        "total_rupiah",
        "tax_rupiah",
        "items_sold",
        "average_sale_rupiah",
        "daily",
    )
    if not isinstance(report, Mapping) or any(key not in report for key in required):
        raise SalesReportExportError("Data laporan tidak lengkap.")

    start_date = report["start_date"]
    end_date = report["end_date"]
    if not isinstance(start_date, str) or not isinstance(end_date, str):
        raise SalesReportExportError("Tanggal laporan tidak valid.")

    integer_fields = (
        "sales_count",
        "total_rupiah",
        "tax_rupiah",
        "items_sold",
        "average_sale_rupiah",
    )
    values = {}
    for field in integer_fields:
        value = report[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SalesReportExportError("Nilai laporan tidak valid: " + field + ".")
        values[field] = value

    daily = report["daily"]
    if not isinstance(daily, (list, tuple)):
        raise SalesReportExportError("Rincian harian laporan tidak valid.")
    validated_daily = []
    for item in daily:
        if not isinstance(item, Mapping):
            raise SalesReportExportError("Baris laporan harian tidak valid.")
        day = item.get("date")
        count = item.get("sales_count")
        total = item.get("total_rupiah")
        if not isinstance(day, str):
            raise SalesReportExportError("Tanggal pada laporan harian tidak valid.")
        if (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            or isinstance(total, bool) or not isinstance(total, int) or total < 0
        ):
            raise SalesReportExportError("Angka pada laporan harian tidak valid.")
        validated_daily.append((day, count, total))

    if not isinstance(destination, (str, os.PathLike)):
        raise SalesReportExportError("Lokasi file tujuan tidak valid.")
    destination_text = os.fspath(destination)
    if not destination_text.strip():
        raise SalesReportExportError("Lokasi file tujuan belum ditentukan.")
    target = Path(destination_text).expanduser()
    parent = target.parent
    temporary_path = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".kasirkita-report-",
            suffix=".tmp",
            dir=str(parent),
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Laporan penjualan KasirKita"])
            writer.writerow(["Tanggal awal", start_date])
            writer.writerow(["Tanggal akhir", end_date])
            writer.writerow([])
            writer.writerow(["Ringkasan", "Nilai"])
            writer.writerow(["Jumlah transaksi", values["sales_count"]])
            writer.writerow(["Total penjualan (rupiah)", values["total_rupiah"]])
            writer.writerow(["Total pajak tercatat (rupiah)", values["tax_rupiah"]])
            writer.writerow(["Unit terjual", values["items_sold"]])
            writer.writerow(["Rata-rata transaksi (rupiah)", values["average_sale_rupiah"]])
            writer.writerow([])
            writer.writerow(["Tanggal lokal", "Jumlah transaksi", "Total penjualan (rupiah)"])
            writer.writerows(validated_daily)
        os.replace(str(temporary_path), str(target))
        temporary_path = None
        return target
    except (OSError, csv.Error, TypeError, ValueError) as exc:
        raise SalesReportExportError("File laporan CSV gagal disimpan.") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


__all__ = ["SalesReportExportError", "export_sales_report_csv"]
