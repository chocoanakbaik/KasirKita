"""Local operating expenses, product costs, and stock-restoring sales returns."""
from __future__ import annotations

from datetime import date
import sqlite3
from typing import Dict, List

from kasirkita.infrastructure.database import transaction


class OperationError(ValueError):
    """Raised when an operational record is invalid."""


class CostPriceService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_products(self, query: str = "") -> List[dict]:
        if not isinstance(query, str) or len(query) > 100:
            raise OperationError("Pencarian produk tidak valid.")
        pattern = "%" + query.strip() + "%"
        rows = self.connection.execute(
            "SELECT id, sku, name, unit_price_rupiah, unit_cost_rupiah, stock_quantity, is_active "
            "FROM products WHERE name LIKE ? OR sku LIKE ? ORDER BY name COLLATE NOCASE",
            (pattern, pattern),
        ).fetchall()
        return [dict(row) for row in rows]

    def set_cost(self, product_id: object, unit_cost_rupiah: object) -> None:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            raise OperationError("Produk tidak valid.")
        if isinstance(unit_cost_rupiah, bool) or not isinstance(unit_cost_rupiah, int) or not 0 <= unit_cost_rupiah <= 9_000_000_000_000_000:
            raise OperationError("Harga modal harus berupa rupiah bulat nol atau lebih.")
        with transaction(self.connection):
            cursor = self.connection.execute(
                "UPDATE products SET unit_cost_rupiah = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (unit_cost_rupiah, product_id),
            )
            if cursor.rowcount != 1:
                raise OperationError("Produk tidak ditemukan.")

    def low_stock(self, threshold: int = 5) -> List[dict]:
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 1_000_000:
            raise OperationError("Batas stok tidak valid.")
        rows = self.connection.execute(
            "SELECT id, sku, name, stock_quantity FROM products "
            "WHERE is_active = 1 AND stock_quantity <= ? ORDER BY stock_quantity, name COLLATE NOCASE",
            (threshold,),
        ).fetchall()
        return [dict(row) for row in rows]


class ExpenseService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def add(self, category: object, description: object, amount_rupiah: object,
            expense_date: object, note: object = "") -> Dict[str, object]:
        category = self._text(category, "Kategori", 80)
        description = self._text(description, "Deskripsi", 200)
        note = self._text(note, "Catatan", 500, True)
        if isinstance(amount_rupiah, bool) or not isinstance(amount_rupiah, int) or amount_rupiah <= 0 or amount_rupiah > 9_000_000_000_000_000:
            raise OperationError("Nominal pengeluaran harus berupa rupiah bulat lebih dari nol.")
        if not isinstance(expense_date, str):
            raise OperationError("Tanggal pengeluaran tidak valid.")
        try:
            date.fromisoformat(expense_date)
        except ValueError as exc:
            raise OperationError("Tanggal gunakan format YYYY-MM-DD.") from exc
        with transaction(self.connection):
            cursor = self.connection.execute(
                "INSERT INTO expenses (category, description, amount_rupiah, expense_date, note) VALUES (?, ?, ?, ?, ?)",
                (category, description, amount_rupiah, expense_date, note),
            )
        row = self.connection.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list(self, start_date: str = "", end_date: str = "", include_voided: bool = False) -> List[dict]:
        conditions, params = [], []
        for label, value, operator in (("expense_date", start_date, ">="), ("expense_date", end_date, "<=")):
            if value:
                try:
                    date.fromisoformat(value)
                except (TypeError, ValueError) as exc:
                    raise OperationError("Tanggal gunakan format YYYY-MM-DD.") from exc
                conditions.append(label + " " + operator + " ?")
                params.append(value)
        if not include_voided:
            conditions.append("is_voided = 0")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self.connection.execute(
            "SELECT id, category, description, amount_rupiah, expense_date, note, is_voided, created_at "
            "FROM expenses" + where + " ORDER BY expense_date DESC, id DESC",
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]

    def void(self, expense_id: object) -> None:
        if isinstance(expense_id, bool) or not isinstance(expense_id, int) or expense_id <= 0:
            raise OperationError("Data pengeluaran tidak valid.")
        with transaction(self.connection):
            cursor = self.connection.execute(
                "UPDATE expenses SET is_voided = 1 WHERE id = ? AND is_voided = 0",
                (expense_id,),
            )
            if cursor.rowcount != 1:
                raise OperationError("Pengeluaran tidak ditemukan atau sudah dibatalkan.")

    @staticmethod
    def _text(value: object, label: str, limit: int, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise OperationError(label + " harus berupa teks.")
        cleaned = " ".join(value.strip().split())
        if not cleaned and not allow_empty:
            raise OperationError(label + " wajib diisi.")
        if len(cleaned) > limit:
            raise OperationError(label + " terlalu panjang.")
        return cleaned


class ReturnService:
    """Record returned sale lines and restore stock atomically."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_sales(self, query: str = "") -> List[dict]:
        if not isinstance(query, str) or len(query) > 100:
            raise OperationError("Pencarian transaksi tidak valid.")
        rows = self.connection.execute(
            "SELECT id, receipt_number, total_rupiah, created_at FROM sales "
            "WHERE status = 'completed' AND instr(lower(receipt_number), lower(?)) > 0 "
            "ORDER BY id DESC LIMIT 100",
            (query.strip(),),
        ).fetchall()
        return [dict(row) for row in rows]

    def sale_lines(self, sale_id: object) -> List[dict]:
        sale_id = self._id(sale_id)
        rows = self.connection.execute(
            "SELECT si.id AS sale_item_id, si.product_id, si.sku_snapshot, si.product_name_snapshot, "
            "si.quantity, si.unit_price_rupiah, "
            "COALESCE((SELECT SUM(ri.quantity) FROM return_items ri WHERE ri.sale_item_id = si.id), 0) AS returned_quantity "
            "FROM sale_items si JOIN sales s ON s.id = si.sale_id "
            "WHERE s.id = ? AND s.status = 'completed' ORDER BY si.id",
            (sale_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def record(self, sale_id: object, items: list, note: str = "") -> Dict[str, object]:
        sale_id = self._id(sale_id)
        if not isinstance(items, list) or not items or len(items) > 200:
            raise OperationError("Pilih setidaknya satu item retur.")
        if not isinstance(note, str) or len(note.strip()) > 300:
            raise OperationError("Catatan retur maksimal 300 karakter.")
        with transaction(self.connection):
            sale = self.connection.execute(
                "SELECT id, subtotal_rupiah, tax_rupiah, total_rupiah, tax_mode, discount_rupiah, status FROM sales WHERE id = ?",
                (sale_id,),
            ).fetchone()
            if sale is None or sale["status"] != "completed":
                raise OperationError("Transaksi tidak ditemukan atau tidak dapat diretur.")
            gross_row = self.connection.execute("SELECT COALESCE(SUM(line_total_rupiah), 0) AS total FROM sale_items WHERE sale_id = ?", (sale_id,)).fetchone()
            gross_sale = int(gross_row["total"])
            refund = 0
            normalized = []
            for item in items:
                if not isinstance(item, dict):
                    raise OperationError("Item retur tidak valid.")
                item_id = self._id(item.get("sale_item_id"))
                quantity = item.get("quantity")
                if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                    raise OperationError("Jumlah retur harus berupa bilangan bulat positif.")
                line = self.connection.execute(
                    "SELECT si.id, si.product_id, si.quantity, si.unit_price_rupiah, "
                    "COALESCE((SELECT SUM(ri.quantity) FROM return_items ri WHERE ri.sale_item_id = si.id), 0) AS returned "
                    "FROM sale_items si WHERE si.id = ? AND si.sale_id = ?",
                    (item_id, sale_id),
                ).fetchone()
                if line is None or quantity > int(line["quantity"]) - int(line["returned"]):
                    raise OperationError("Jumlah retur melebihi jumlah item yang belum diretur.")
                line_gross = int(line["unit_price_rupiah"]) * quantity
                discount_share = ((int(sale["discount_rupiah"]) * line_gross + gross_sale // 2) // gross_sale) if gross_sale else 0
                discounted_line = max(0, line_gross - discount_share)
                if sale["tax_mode"] == "inclusive":
                    line_refund = discounted_line
                else:
                    tax_share = ((int(sale["tax_rupiah"]) * discounted_line + int(sale["subtotal_rupiah"]) // 2) // int(sale["subtotal_rupiah"])) if int(sale["subtotal_rupiah"]) else 0
                    line_refund = discounted_line + tax_share
                normalized.append((item_id, int(line["product_id"]), quantity, line_refund))
                refund += line_refund
            if refund > int(sale["total_rupiah"]):
                raise OperationError("Nilai pengembalian melebihi total transaksi.")
            cursor = self.connection.execute(
                "INSERT INTO returns (sale_id, refund_rupiah, note) VALUES (?, ?, ?)",
                (sale_id, refund, note.strip()),
            )
            return_id = int(cursor.lastrowid)
            for item_id, product_id, quantity, line_refund in normalized:
                self.connection.execute(
                    "INSERT INTO return_items (return_id, sale_item_id, product_id, quantity, refund_rupiah) VALUES (?, ?, ?, ?, ?)",
                    (return_id, item_id, product_id, quantity, line_refund),
                )
                self.connection.execute(
                    "UPDATE products SET stock_quantity = stock_quantity + ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                    (quantity, product_id),
                )
                self.connection.execute(
                    "INSERT INTO stock_movements (product_id, sale_id, movement_type, quantity_delta, note) VALUES (?, ?, 'adjustment_in', ?, ?)",
                    (product_id, sale_id, quantity, "Retur transaksi " + str(sale_id)),
                )
        return {"id": return_id, "sale_id": sale_id, "refund_rupiah": refund, "note": note.strip()}

    @staticmethod
    def _id(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise OperationError("ID transaksi/item tidak valid.")
        return value


class ProfitService:
    """Calculate realized gross profit and operating expenses for a date range."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def summarize(self, start_date: str, end_date: str) -> Dict[str, int]:
        for value in (start_date, end_date):
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise OperationError("Tanggal gunakan format YYYY-MM-DD.") from exc
        if start_date > end_date:
            raise OperationError("Tanggal awal tidak boleh setelah tanggal akhir.")
        rows = self.connection.execute(
            "SELECT si.id, si.unit_price_rupiah, si.unit_cost_rupiah, si.quantity, "
            "s.discount_rupiah, "
            "(SELECT COALESCE(SUM(si2.line_total_rupiah), 0) FROM sale_items si2 WHERE si2.sale_id = s.id) AS gross_sale, "
            "COALESCE((SELECT SUM(ri.quantity) FROM return_items ri JOIN returns r ON r.id = ri.return_id "
            "JOIN sales rs ON rs.id = r.sale_id WHERE ri.sale_item_id = si.id "
            "AND substr(rs.created_at, 1, 10) BETWEEN ? AND ?), 0) AS returned "
            "FROM sale_items si JOIN sales s ON s.id = si.sale_id "
            "WHERE s.status = 'completed' AND substr(s.created_at, 1, 10) BETWEEN ? AND ?",
            (start_date, end_date, start_date, end_date),
        ).fetchall()
        revenue = 0
        cost = 0
        for row in rows:
            sold = int(row["quantity"]) - int(row["returned"])
            line_revenue = int(row["unit_price_rupiah"]) * sold
            gross_sale = int(row["gross_sale"])
            discount_share = ((int(row["discount_rupiah"]) * line_revenue + gross_sale // 2) // gross_sale) if gross_sale else 0
            revenue += max(0, line_revenue - discount_share)
            cost += int(row["unit_cost_rupiah"]) * sold
        expense_row = self.connection.execute(
            "SELECT COALESCE(SUM(amount_rupiah), 0) AS total FROM expenses "
            "WHERE is_voided = 0 AND expense_date BETWEEN ? AND ?",
            (start_date, end_date),
        ).fetchone()
        gross_profit = revenue - cost
        expenses = int(expense_row["total"])
        return {
            "revenue_rupiah": revenue,
            "cost_of_goods_rupiah": cost,
            "gross_profit_rupiah": gross_profit,
            "expenses_rupiah": expenses,
            "net_profit_rupiah": gross_profit - expenses,
        }


__all__ = ["CostPriceService", "ExpenseService", "OperationError", "ProfitService", "ReturnService"]
