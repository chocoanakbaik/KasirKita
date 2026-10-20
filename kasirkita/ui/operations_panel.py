"""Small operational workspace for product costs, expenses, returns, and profit."""
import csv
from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from kasirkita.services.operations import (
    CostPriceService, ExpenseService, OperationError, ProfitService, ReturnService,
)


def _rupiah(value):
    return "Rp " + format(int(value), ",").replace(",", ".")


def _parse_money(value):
    text = str(value).strip()
    if text and text.isdigit():
        return int(text)
    if text and all(part.isdigit() for part in text.split(".")) and all(len(part) == 3 for part in text.split(".")[1:]):
        return int(text.replace(".", ""))
    raise OperationError("Masukkan nominal rupiah bulat, misalnya 25000 atau 25.000.")


class OperationsPanel(ttk.Frame):
    def __init__(self, parent, connection):
        super().__init__(parent, padding=8)
        self.costs = CostPriceService(connection)
        self.expenses = ExpenseService(connection)
        self.returns = ReturnService(connection)
        self.profits = ProfitService(connection)
        self._build()

    def _build(self):
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)
        self.cost_tab = ttk.Frame(tabs, padding=10)
        self.expense_tab = ttk.Frame(tabs, padding=10)
        self.return_tab = ttk.Frame(tabs, padding=10)
        self.profit_tab = ttk.Frame(tabs, padding=10)
        tabs.add(self.cost_tab, text="Harga Modal & Stok")
        tabs.add(self.expense_tab, text="Pengeluaran")
        tabs.add(self.return_tab, text="Retur")
        tabs.add(self.profit_tab, text="Laba")
        self._build_costs()
        self._build_expenses()
        self._build_returns()
        self._build_profit()

    def _tree(self, parent, columns):
        tree = ttk.Treeview(parent, columns=tuple(x[0] for x in columns), show="headings", selectmode="browse")
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        return tree

    def _build_costs(self):
        self.cost_tab.rowconfigure(1, weight=1)
        self.cost_tab.columnconfigure(0, weight=1)
        bar = ttk.Frame(self.cost_tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.cost_search = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.cost_search, width=30)
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _e: self.refresh_costs())
        ttk.Button(bar, text="Cari", command=self.refresh_costs).pack(side="left", padx=5)
        ttk.Button(bar, text="Atur harga modal", command=self.set_cost).pack(side="right")
        self.cost_tree = self._tree(self.cost_tab, (
            ("sku", "SKU", 110), ("name", "Produk", 240), ("price", "Harga jual", 120),
            ("cost", "Harga modal", 120), ("stock", "Stok", 70),
        ))
        self.cost_tree.grid(row=1, column=0, sticky="nsew")
        ttk.Button(self.cost_tab, text="Ekspor daftar stok menipis", command=self.export_low_stock).grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.refresh_costs()

    def refresh_costs(self):
        self.cost_tree.delete(*self.cost_tree.get_children())
        for row in self.costs.list_products(self.cost_search.get()):
            self.cost_tree.insert("", "end", iid=str(row["id"]), values=(
                row["sku"], row["name"], _rupiah(row["unit_price_rupiah"]),
                _rupiah(row["unit_cost_rupiah"]), row["stock_quantity"],
            ))

    def set_cost(self):
        selected = self.cost_tree.selection()
        if not selected:
            messagebox.showinfo("Pilih produk", "Pilih produk yang ingin diubah harga modalnya.", parent=self)
            return
        product_id = int(selected[0])
        product = next((p for p in self.costs.list_products() if p["id"] == product_id), None)
        if not product:
            return
        value = simpledialog.askstring("Harga modal", "Harga modal per unit (rupiah):", initialvalue=str(product["unit_cost_rupiah"]), parent=self)
        if value is None:
            return
        try:
            self.costs.set_cost(product_id, _parse_money(value))
        except OperationError as exc:
            messagebox.showerror("Harga modal tidak valid", str(exc), parent=self)
            return
        self.refresh_costs()

    def export_low_stock(self):
        threshold = simpledialog.askinteger("Stok menipis", "Tandai stok pada atau di bawah jumlah:", initialvalue=5, minvalue=0, maxvalue=1000000, parent=self)
        if threshold is None:
            return
        rows = self.costs.low_stock(threshold)
        path = filedialog.asksaveasfilename(parent=self, title="Ekspor stok menipis", defaultextension=".csv", initialfile="stok-menipis.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["ID", "SKU", "Nama produk", "Stok"])
                writer.writerows([[r["id"], r["sku"], r["name"], r["stock_quantity"]] for r in rows])
        except OSError as exc:
            messagebox.showerror("Ekspor gagal", str(exc), parent=self)
            return
        messagebox.showinfo("Ekspor selesai", "Daftar stok menipis disimpan.", parent=self)

    def _build_expenses(self):
        self.expense_tab.rowconfigure(0, weight=1)
        self.expense_tab.columnconfigure(0, weight=1)
        self.expense_tree = self._tree(self.expense_tab, (
            ("date", "Tanggal", 100), ("category", "Kategori", 140),
            ("description", "Deskripsi", 260), ("amount", "Nominal", 130),
        ))
        self.expense_tree.grid(row=0, column=0, sticky="nsew")
        bar = ttk.Frame(self.expense_tab)
        bar.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(bar, text="Tambah pengeluaran", command=self.add_expense).pack(side="left")
        ttk.Button(bar, text="Batalkan catatan", command=self.void_expense).pack(side="left", padx=6)
        ttk.Button(bar, text="Ekspor CSV", command=self.export_expenses).pack(side="right")
        self.refresh_expenses()

    def refresh_expenses(self):
        self.expense_tree.delete(*self.expense_tree.get_children())
        for row in self.expenses.list():
            self.expense_tree.insert("", "end", iid=str(row["id"]), values=(
                row["expense_date"], row["category"], row["description"], _rupiah(row["amount_rupiah"]),
            ))

    def add_expense(self):
        dialog = tk.Toplevel(self)
        dialog.title("Tambah pengeluaran")
        dialog.transient(self.winfo_toplevel())
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        fields = []
        defaults = [("Kategori", "Operasional"), ("Deskripsi", ""), ("Nominal rupiah", ""), ("Tanggal YYYY-MM-DD", date.today().isoformat()), ("Catatan", "")]
        for row, (label, default) in enumerate(defaults):
            ttk.Label(frame, text=label).grid(row=row * 2, column=0, sticky="w")
            entry = ttk.Entry(frame, width=38)
            entry.insert(0, default)
            entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(2, 6))
            fields.append(entry)
        frame.columnconfigure(0, weight=1)
        dialog.grab_set()

        def submit():
            try:
                self.expenses.add(fields[0].get(), fields[1].get(), _parse_money(fields[2].get()), fields[3].get(), fields[4].get())
            except OperationError as exc:
                messagebox.showerror("Pengeluaran tidak disimpan", str(exc), parent=dialog)
                return
            dialog.destroy()
            self.refresh_expenses()

        ttk.Button(frame, text="Simpan", command=submit).grid(row=10, column=0, sticky="e")

    def void_expense(self):
        selected = self.expense_tree.selection()
        if not selected:
            messagebox.showinfo("Pilih pengeluaran", "Pilih catatan yang ingin dibatalkan.", parent=self)
            return
        if not messagebox.askyesno("Konfirmasi", "Batalkan catatan pengeluaran ini?", parent=self):
            return
        try:
            self.expenses.void(int(selected[0]))
        except OperationError as exc:
            messagebox.showerror("Tidak dapat membatalkan", str(exc), parent=self)
            return
        self.refresh_expenses()

    def export_expenses(self):
        rows = self.expenses.list(include_voided=True)
        path = filedialog.asksaveasfilename(parent=self, title="Ekspor pengeluaran", defaultextension=".csv", initialfile="pengeluaran.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["Tanggal", "Kategori", "Deskripsi", "Nominal", "Status", "Catatan"])
                for row in rows:
                    writer.writerow([row["expense_date"], row["category"], row["description"], row["amount_rupiah"], "Dibatalkan" if row["is_voided"] else "Aktif", row["note"]])
        except OSError as exc:
            messagebox.showerror("Ekspor gagal", str(exc), parent=self)
            return
        messagebox.showinfo("Ekspor selesai", "Catatan pengeluaran disimpan.", parent=self)

    def _build_returns(self):
        self.return_tab.columnconfigure(0, weight=1)
        self.return_tab.rowconfigure(1, weight=1)
        self.return_tab.rowconfigure(3, weight=1)
        top = ttk.Frame(self.return_tab)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(top, text="Nomor struk").pack(side="left")
        self.return_search = tk.StringVar()
        ttk.Entry(top, textvariable=self.return_search, width=28).pack(side="left", padx=6)
        ttk.Button(top, text="Cari transaksi", command=self.refresh_return_sales).pack(side="left")
        self.return_sales = self._tree(self.return_tab, (("receipt", "Struk", 230), ("date", "Tanggal", 180), ("total", "Total", 130)))
        self.return_sales.grid(row=1, column=0, sticky="nsew")
        self.return_sales.bind("<<TreeviewSelect>>", lambda _e: self.refresh_return_lines())
        ttk.Label(self.return_tab, text="Item transaksi yang dipilih").grid(row=2, column=0, sticky="w", pady=(8, 4))
        self.return_lines = self._tree(self.return_tab, (("product", "Produk", 250), ("sold", "Terjual", 80), ("returned", "Diretur", 80), ("remaining", "Sisa retur", 90), ("price", "Harga", 120)))
        self.return_lines.grid(row=3, column=0, sticky="nsew")
        bottom = ttk.Frame(self.return_tab)
        bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(bottom, text="Jumlah yang diretur").pack(side="left")
        self.return_qty = tk.StringVar(value="1")
        ttk.Entry(bottom, textvariable=self.return_qty, width=7).pack(side="left", padx=6)
        ttk.Button(bottom, text="Proses retur & kembalikan stok", command=self.process_return).pack(side="left")
        self.refresh_return_sales()

    def refresh_return_sales(self):
        self.return_sales.delete(*self.return_sales.get_children())
        for row in self.returns.list_sales(self.return_search.get()):
            self.return_sales.insert("", "end", iid=str(row["id"]), values=(row["receipt_number"], row["created_at"], _rupiah(row["total_rupiah"])))
        self.refresh_return_lines()

    def refresh_return_lines(self):
        self.return_lines.delete(*self.return_lines.get_children())
        selected = self.return_sales.selection()
        if not selected:
            return
        for row in self.returns.sale_lines(int(selected[0])):
            self.return_lines.insert("", "end", iid=str(row["sale_item_id"]), values=(
                row["product_name_snapshot"], row["quantity"], row["returned_quantity"],
                int(row["quantity"]) - int(row["returned_quantity"]), _rupiah(row["unit_price_rupiah"]),
            ))

    def process_return(self):
        sale = self.return_sales.selection()
        line = self.return_lines.selection()
        if not sale or not line:
            messagebox.showinfo("Pilih item", "Pilih transaksi dan item yang akan diretur.", parent=self)
            return
        try:
            quantity = int(self.return_qty.get().strip())
            result = self.returns.record(int(sale[0]), [{"sale_item_id": int(line[0]), "quantity": quantity}], "Retur dicatat dari layar operasional")
        except (ValueError, OperationError) as exc:
            messagebox.showerror("Retur gagal", str(exc), parent=self)
            return
        messagebox.showinfo("Retur dicatat", "Stok dikembalikan. Nilai barang: {}.".format(_rupiah(result["refund_rupiah"])), parent=self)
        self.refresh_return_lines()
        self.refresh_costs()

    def _build_profit(self):
        bar = ttk.Frame(self.profit_tab)
        bar.pack(fill="x", pady=(0, 10))
        self.profit_start = tk.StringVar(value=date.today().isoformat())
        self.profit_end = tk.StringVar(value=date.today().isoformat())
        ttk.Label(bar, text="Dari").pack(side="left")
        ttk.Entry(bar, textvariable=self.profit_start, width=12).pack(side="left", padx=5)
        ttk.Label(bar, text="Sampai").pack(side="left")
        ttk.Entry(bar, textvariable=self.profit_end, width=12).pack(side="left", padx=5)
        ttk.Button(bar, text="Hitung laba", command=self.refresh_profit).pack(side="left", padx=5)
        self.profit_text = tk.StringVar(value="Pilih rentang tanggal lalu hitung laba.")
        ttk.Label(self.profit_tab, textvariable=self.profit_text, justify="left", font=("Segoe UI", 12)).pack(anchor="w", pady=12)

    def refresh_profit(self):
        try:
            result = self.profits.summarize(self.profit_start.get().strip(), self.profit_end.get().strip())
        except OperationError as exc:
            messagebox.showerror("Rentang tanggal tidak valid", str(exc), parent=self)
            return
        self.profit_text.set(
            "Pendapatan barang: {}\nHarga modal barang terjual: {}\nLaba kotor: {}\nPengeluaran operasional: {}\nLaba setelah pengeluaran: {}".format(
                _rupiah(result["revenue_rupiah"]), _rupiah(result["cost_of_goods_rupiah"]),
                _rupiah(result["gross_profit_rupiah"]), _rupiah(result["expenses_rupiah"]),
                _rupiah(result["net_profit_rupiah"]),
            )
        )


__all__ = ["OperationsPanel"]
