"""Tests for safe CSV export of sales summaries."""
import csv
import tempfile
import unittest
from pathlib import Path

from kasirkita.services.report_export import (
    SalesReportExportError,
    export_sales_report_csv,
)


class SalesReportExportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "start_date": "2026-10-10",
            "end_date": "2026-10-11",
            "sales_count": 2,
            "total_rupiah": 12500,
            "tax_rupiah": 0,
            "items_sold": 5,
            "average_sale_rupiah": 6250,
            "daily": [
                {"date": "2026-10-10", "sales_count": 1, "total_rupiah": 5000},
                {"date": "2026-10-11", "sales_count": 1, "total_rupiah": 7500},
            ],
        }

    def test_exports_summary_and_daily_rows_as_excel_friendly_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "laporan.csv"
            result = export_sales_report_csv(self.report, destination)
            self.assertEqual(result, destination)
            raw = destination.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            with destination.open("r", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(rows[0], ["Laporan penjualan KasirKita"])
            self.assertIn(["Jumlah transaksi", "2"], rows)
            self.assertIn(["Total penjualan (rupiah)", "12500"], rows)
            self.assertIn(
                ["Tanggal lokal", "Jumlah transaksi", "Total penjualan (rupiah)"],
                rows,
            )
            self.assertIn(["2026-10-11", "1", "7500"], rows)

    def test_rejects_missing_fields_and_invalid_numbers(self):
        incomplete = dict(self.report)
        del incomplete["tax_rupiah"]
        invalid_number = dict(self.report, total_rupiah=True)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.csv"
            for report in (incomplete, invalid_number):
                with self.subTest(report=report):
                    with self.assertRaises(SalesReportExportError):
                        export_sales_report_csv(report, target)
            self.assertFalse(target.exists())

    def test_rejects_invalid_daily_rows_without_replacing_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.csv"
            target.write_text("existing report", encoding="utf-8")
            invalid = dict(self.report, daily=[{"date": "2026-10-10", "sales_count": -1, "total_rupiah": 1}])
            with self.assertRaises(SalesReportExportError):
                export_sales_report_csv(invalid, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing report")

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "reports" / "report.csv"
            export_sales_report_csv(self.report, target)
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
