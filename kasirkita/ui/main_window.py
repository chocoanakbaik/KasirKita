"""Tkinter desktop interface for the initial KasirKita workflow."""
from __future__ import annotations

import logging
import re
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Dict, Optional

from kasirkita.infrastructure.backup import BackupError, DatabaseBackupService
from kasirkita.infrastructure.product_repository import (
    DuplicateSKUError,
    ProductNotFoundError,
)
from kasirkita.services.checkout import CheckoutError, CheckoutService
from kasirkita.services.product_catalog import ProductCatalog, ProductValidationError
from kasirkita.services.sales_history import SalesHistoryService, SalesHistoryValidationError
from kasirkita.services.sales_report import SalesReportService, SalesReportValidationError
from kasirkita.services.stock import StockAdjustmentError, StockService

logger = logging.getLogger("kasirkita.ui")


def format_rupiah(value: int) -> str:
    """Format a non-negative integer rupiah amount for Indonesian users."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Rupiah amount must be a non-negative integer.")
    return "Rp " + format(value, ",").replace(",", ".")


def parse_rupiah_input(value: str) -> int:
    """Parse whole rupiah input; accepts digits with optional dot group separators."""
    if not isinstance(value, str):
        raise ValueError("Masukkan nominal dalam angka rupiah.")
    cleaned = value.strip()
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)", cleaned):
        raise ValueError("Nominal harus berupa angka bulat. Contoh: 25000 atau 25.000.")
    amount = int(cleaned.replace(".", ""))
    if amount > 9_000_000_000_000_000:
        raise ValueError("Nominal melebihi batas yang didukung.")
    return amount


class ProductDialog(tk.Toplevel):
    """Modal form for creating or editing a catalogue product."""

    def __init__(self, parent, title: str, product: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._product = product

        frame = ttk.Frame(self, padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        defaults = {
            "sku": product["sku"] if product else "",
            "name": product["name"] if product else "",
            "price": str(product["unit_price_rupiah"]) if product else "",
            "stock": str(product["stock_quantity"]) if product else "0",
        }
        self._entries = {}
        fields = [
            ("SKU", "sku"),
            ("Nama produk", "name"),
            ("Harga (rupiah)", "price"),
        ]
        if product is None:
            fields.append(("Stok awal (unit)", "stock"))

        for row, (label_text, key) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(
                row=row, column=0, sticky="w", padx=(0, 14), pady=7
            )
            entry = ttk.Entry(frame, width=34)
            entry.insert(0, defaults[key])
            entry.grid(row=row, column=1, sticky="ew", pady=7)
            self._entries[key] = entry

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Simpan", command=self._submit).pack(
            side="right", padx=(0, 8)
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._submit())
        self.grab_set()
        self._entries["sku"].focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _submit(self) -> None:
        sku = self._entries["sku"].get()
        name = self._entries["name"].get()
        try:
            price = parse_rupiah_input(self._entries["price"].get())
            stock_text = self._entries["stock"].get().strip() if "stock" in self._entries else None
            if stock_text is not None and not stock_text.isdigit():
                raise ValueError("Stok awal harus berupa bilangan bulat nol atau lebih.")
            stock = int(stock_text) if stock_text is not None else None
            if stock is not None and stock > 2_147_483_647:
                raise ValueError("Stok awal melebihi batas yang didukung.")
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("Input tidak valid", str(exc), parent=self)
            return

        self.result = {"sku": sku, "name": name, "price": price, "stock": stock}
        self.destroy()


class StockAdjustmentDialog(tk.Toplevel):
    """Modal form for an audited stock increase or decrease."""

    def __init__(self, parent, product: dict) -> None:
        super().__init__(parent)
        self.title("Penyesuaian stok")
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._product = product

        frame = ttk.Frame(self, padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text=product["name"], style="Subheader.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(frame, text="Stok saat ini").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(frame, text=str(product["stock_quantity"]) + " unit").grid(
            row=1, column=1, sticky="w", pady=5
        )
        ttk.Label(frame, text="Jenis perubahan").grid(row=2, column=0, sticky="w", pady=5)
        self.mode_var = tk.StringVar(value="in")
        self.mode = ttk.Combobox(
            frame,
            textvariable=self.mode_var,
            values=("in", "out"),
            state="readonly",
            width=28,
        )
        self.mode.grid(row=2, column=1, sticky="ew", pady=5)
        self.mode.set("in")
        ttk.Label(frame, text="Jumlah unit").grid(row=3, column=0, sticky="w", pady=5)
        self.quantity_entry = ttk.Entry(frame, width=32)
        self.quantity_entry.grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="Alasan").grid(row=4, column=0, sticky="w", pady=5)
        self.note_entry = ttk.Entry(frame, width=32)
        self.note_entry.grid(row=4, column=1, sticky="ew", pady=5)
        ttk.Label(
            frame,
            text="Gunakan alasan yang jelas; setiap perubahan dicatat dalam riwayat stok.",
            wraplength=340,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(5, 10))
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Simpan", command=self._submit).pack(
            side="right", padx=(0, 8)
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._submit())
        self.grab_set()
        self.quantity_entry.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _submit(self) -> None:
        quantity_text = self.quantity_entry.get().strip()
        if not quantity_text.isdigit():
            messagebox.showerror(
                "Jumlah tidak valid",
                "Jumlah harus berupa bilangan bulat positif.",
                parent=self,
            )
            return
        quantity = int(quantity_text)
        if quantity <= 0 or quantity > 2_147_483_647:
            messagebox.showerror(
                "Jumlah tidak valid",
                "Jumlah harus lebih besar dari nol dan dalam batas yang didukung.",
                parent=self,
            )
            return
        delta = quantity if self.mode_var.get() == "in" else -quantity
        self.result = {"delta": delta, "note": self.note_entry.get()}
        self.destroy()


class MainWindow:
    """Own the desktop widgets and connect them to application services."""

    def __init__(
        self,
        root: tk.Tk,
        catalog: ProductCatalog,
        checkout: CheckoutService,
        sales_history: SalesHistoryService,
        backup_service: DatabaseBackupService,
        stock_service: StockService,
        sales_report: SalesReportService,
    ) -> None:
        self.root = root
        self.catalog = catalog
        self.checkout_service = checkout
        self.sales_history = sales_history
        self.backup_service = backup_service
        self.stock_service = stock_service
        self.sales_report = sales_report
        self.cart: Dict[int, int] = {}
        self._product_rows: Dict[int, dict] = {}
        self._sales_rows: Dict[int, dict] = {}

        self.root.title("KasirKita Desktop")
        self.root.geometry("1120x720")
        self.root.minsize(900, 600)
        self._configure_style()
        self._build_ui()
        self.refresh_products()
        self.refresh_cashier_products()
        self.refresh_cart()
        self.refresh_sales()
        self.refresh_report()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", foreground="#17212b")
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subheader.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(10, 6))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=16)
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="KasirKita", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="DESKTOP • LOKAL", font=("Segoe UI", 9, "bold")).pack(
            side="right", padx=4
        )

        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        self.cashier_tab = ttk.Frame(self.tabs, padding=12)
        self.products_tab = ttk.Frame(self.tabs, padding=12)
        self.history_tab = ttk.Frame(self.tabs, padding=12)
        self.report_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.cashier_tab, text="Kasir")
        self.tabs.add(self.products_tab, text="Produk")
        self.tabs.add(self.history_tab, text="Riwayat transaksi")
        self.tabs.add(self.report_tab, text="Laporan")
        self._build_cashier_tab()
        self._build_products_tab()
        self._build_history_tab()
        self._build_report_tab()

    def _build_cashier_tab(self) -> None:
        self.cashier_tab.columnconfigure(0, weight=3)
        self.cashier_tab.columnconfigure(1, weight=2)
        self.cashier_tab.rowconfigure(1, weight=1)

        ttk.Label(self.cashier_tab, text="Pilih produk", style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(self.cashier_tab, text="Keranjang", style="Subheader.TLabel").grid(
            row=0, column=1, sticky="w", padx=(14, 0), pady=(0, 8)
        )

        product_frame = ttk.Frame(self.cashier_tab)
        product_frame.grid(row=1, column=0, sticky="nsew")
        product_frame.rowconfigure(1, weight=1)
        product_frame.columnconfigure(0, weight=1)
        search_frame = ttk.Frame(product_frame)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(0, weight=1)
        self.cashier_search = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.cashier_search)
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_cashier_products())
        ttk.Button(search_frame, text="Cari", command=self.refresh_cashier_products).grid(
            row=0, column=1, padx=(6, 0)
        )

        self.cashier_product_tree = ttk.Treeview(
            product_frame,
            columns=("sku", "name", "price", "stock"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in [
            ("sku", "SKU", 100),
            ("name", "Nama produk", 210),
            ("price", "Harga", 110),
            ("stock", "Stok", 65),
        ]:
            self.cashier_product_tree.heading(key, text=label)
            self.cashier_product_tree.column(key, width=width, anchor="w")
        self.cashier_product_tree.grid(row=1, column=0, sticky="nsew")
        product_scroll = ttk.Scrollbar(
            product_frame, orient="vertical", command=self.cashier_product_tree.yview
        )
        product_scroll.grid(row=1, column=1, sticky="ns")
        self.cashier_product_tree.configure(yscrollcommand=product_scroll.set)
        self.cashier_product_tree.bind("<Double-1>", lambda _event: self.add_selected_to_cart())

        add_frame = ttk.Frame(product_frame)
        add_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(add_frame, text="Jumlah").pack(side="left")
        self.quantity_var = tk.StringVar(value="1")
        ttk.Entry(add_frame, textvariable=self.quantity_var, width=8).pack(
            side="left", padx=8
        )
        ttk.Button(add_frame, text="Tambah ke keranjang", command=self.add_selected_to_cart).pack(
            side="left"
        )

        cart_frame = ttk.Frame(self.cashier_tab)
        cart_frame.grid(row=1, column=1, sticky="nsew", padx=(14, 0))
        cart_frame.rowconfigure(0, weight=1)
        cart_frame.columnconfigure(0, weight=1)
        self.cart_tree = ttk.Treeview(
            cart_frame,
            columns=("name", "qty", "price", "total"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in [
            ("name", "Produk", 150),
            ("qty", "Qty", 42),
            ("price", "Harga", 90),
            ("total", "Subtotal", 100),
        ]:
            self.cart_tree.heading(key, text=label)
            self.cart_tree.column(key, width=width, anchor="w")
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        cart_scroll = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        cart_scroll.grid(row=0, column=1, sticky="ns")
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)

        cart_actions = ttk.Frame(cart_frame)
        cart_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        ttk.Button(cart_actions, text="Hapus item", command=self.remove_selected_cart_item).pack(
            side="left"
        )
        ttk.Button(cart_actions, text="Kosongkan", command=self.clear_cart).pack(
            side="left", padx=6
        )

        totals = ttk.Frame(cart_frame)
        totals.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(totals, text="Total transaksi", style="Subheader.TLabel").pack(anchor="w")
        self.total_var = tk.StringVar(value=format_rupiah(0))
        ttk.Label(totals, textvariable=self.total_var, font=("Segoe UI", 20, "bold")).pack(
            anchor="w", pady=(2, 10)
        )
        ttk.Label(totals, text="Uang diterima (tunai)").pack(anchor="w")
        self.received_var = tk.StringVar()
        ttk.Entry(totals, textvariable=self.received_var).pack(fill="x", pady=(3, 8))
        ttk.Button(totals, text="PROSES PEMBAYARAN", command=self.process_checkout).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Label(
            totals,
            text="Pajak belum diterapkan pada versi awal ini.",
            wraplength=280,
            foreground="#596777",
        ).pack(anchor="w")

    def _build_products_tab(self) -> None:
        self.products_tab.rowconfigure(2, weight=1)
        self.products_tab.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(self.products_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Katalog produk", style="Subheader.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Tambah produk", command=self.add_product).pack(side="right")
        ttk.Button(toolbar, text="Aktifkan / nonaktifkan", command=self.toggle_selected_product).pack(
            side="right", padx=8
        )
        ttk.Button(toolbar, text="Edit detail", command=self.edit_selected_product).pack(
            side="right", padx=8
        )
        ttk.Button(toolbar, text="Penyesuaian stok", command=self.adjust_selected_stock).pack(
            side="right", padx=8
        )

        self.product_search = tk.StringVar()
        search = ttk.Frame(self.products_tab)
        search.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search.columnconfigure(0, weight=1)
        entry = ttk.Entry(search, textvariable=self.product_search)
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda _event: self.refresh_products())
        ttk.Button(search, text="Cari", command=self.refresh_products).grid(
            row=0, column=1, padx=(6, 0)
        )

        self.product_tree = ttk.Treeview(
            self.products_tab,
            columns=("sku", "name", "price", "stock", "status"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in [
            ("sku", "SKU", 130),
            ("name", "Nama produk", 320),
            ("price", "Harga", 140),
            ("stock", "Stok", 100),
            ("status", "Status", 100),
        ]:
            self.product_tree.heading(key, text=label)
            self.product_tree.column(key, width=width, anchor="w")
        self.product_tree.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.products_tab, orient="vertical", command=self.product_tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.product_tree.configure(yscrollcommand=scroll.set)

    def _build_history_tab(self) -> None:
        self.history_tab.rowconfigure(1, weight=1)
        self.history_tab.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(self.history_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Riwayat transaksi", style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        self.history_search = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.history_search)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<Return>", lambda _event: self.refresh_sales())
        ttk.Button(toolbar, text="Muat ulang", command=self.refresh_sales).grid(
            row=0, column=2, padx=(6, 0)
        )
        ttk.Button(toolbar, text="Lihat detail", command=self.view_selected_sale).grid(
            row=0, column=3, padx=(6, 0)
        )

        self.sales_tree = ttk.Treeview(
            self.history_tab,
            columns=("receipt", "date", "status", "total"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in [
            ("receipt", "Nomor struk", 240),
            ("date", "Waktu (UTC)", 230),
            ("status", "Status", 120),
            ("total", "Total", 150),
        ]:
            self.sales_tree.heading(key, text=label)
            self.sales_tree.column(key, width=width, anchor="w")
        self.sales_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.history_tab, orient="vertical", command=self.sales_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.sales_tree.configure(yscrollcommand=scroll.set)
        self.sales_tree.bind("<Double-1>", lambda _event: self.view_selected_sale())

        backup_actions = ttk.Frame(self.history_tab)
        backup_actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(backup_actions, text="Buat backup", command=self.create_backup).pack(
            side="left"
        )
        ttk.Button(backup_actions, text="Pulihkan backup", command=self.restore_backup).pack(
            side="left", padx=(8, 0)
        )

    def _build_report_tab(self) -> None:
        self.report_tab.rowconfigure(2, weight=1)
        self.report_tab.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(self.report_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        today = date.today().isoformat()
        ttk.Label(toolbar, text="Dari (tanggal lokal)").pack(side="left")
        self.report_start_var = tk.StringVar(value=today)
        ttk.Entry(toolbar, textvariable=self.report_start_var, width=13).pack(
            side="left", padx=(6, 12)
        )
        ttk.Label(toolbar, text="Sampai").pack(side="left")
        self.report_end_var = tk.StringVar(value=today)
        ttk.Entry(toolbar, textvariable=self.report_end_var, width=13).pack(
            side="left", padx=6
        )
        ttk.Button(toolbar, text="Buat laporan", command=self.refresh_report).pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(
            toolbar,
            text="Tanggal mengikuti zona waktu komputer.",
            foreground="#596777",
        ).pack(side="right")

        summary = ttk.Frame(self.report_tab)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            summary.columnconfigure(column, weight=1)
        self.report_sales_var = tk.StringVar(value="0")
        self.report_revenue_var = tk.StringVar(value=format_rupiah(0))
        self.report_items_var = tk.StringVar(value="0")
        self.report_average_var = tk.StringVar(value=format_rupiah(0))
        for column, title_text, variable in [
            (0, "Jumlah transaksi", self.report_sales_var),
            (1, "Total penjualan", self.report_revenue_var),
            (2, "Unit terjual", self.report_items_var),
            (3, "Rata-rata transaksi", self.report_average_var),
        ]:
            card = ttk.LabelFrame(summary, text=title_text, padding=10)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            ttk.Label(card, textvariable=variable, font=("Segoe UI", 13, "bold")).pack(
                anchor="w"
            )

        self.report_tree = ttk.Treeview(
            self.report_tab,
            columns=("date", "count", "total"),
            show="headings",
        )
        for key, label, width in [
            ("date", "Tanggal lokal", 180),
            ("count", "Transaksi", 120),
            ("total", "Total penjualan", 180),
        ]:
            self.report_tree.heading(key, text=label)
            self.report_tree.column(key, width=width, anchor="w")
        self.report_tree.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.report_tab, orient="vertical", command=self.report_tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.report_tree.configure(yscrollcommand=scroll.set)

    def refresh_report(self) -> None:
        try:
            report = self.sales_report.summarize(
                self.report_start_var.get().strip(),
                self.report_end_var.get().strip(),
            )
            self.report_sales_var.set(str(report["sales_count"]))
            self.report_revenue_var.set(format_rupiah(report["total_rupiah"]))
            self.report_items_var.set(str(report["items_sold"]))
            self.report_average_var.set(format_rupiah(report["average_sale_rupiah"]))
            self.report_tree.delete(*self.report_tree.get_children())
            for item in report["daily"]:
                self.report_tree.insert(
                    "",
                    "end",
                    values=(
                        item["date"],
                        item["sales_count"],
                        format_rupiah(item["total_rupiah"]),
                    ),
                )
        except SalesReportValidationError as exc:
            messagebox.showerror("Rentang tanggal tidak valid", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to build sales report")
            messagebox.showerror("Kesalahan", "Laporan penjualan gagal dibuat.", parent=self.root)

    def create_backup(self) -> None:
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Simpan backup KasirKita",
            defaultextension=".sqlite3",
            filetypes=[("Database SQLite", "*.sqlite3"), ("Semua file", "*.*")],
        )
        if not destination:
            return
        try:
            path = self.backup_service.create_backup(destination)
            messagebox.showinfo(
                "Backup berhasil",
                "Backup database berhasil dibuat:\n" + str(path),
                parent=self.root,
            )
        except BackupError as exc:
            messagebox.showerror("Backup gagal", str(exc), parent=self.root)
        except Exception:
            logger.exception("Unexpected backup failure")
            messagebox.showerror("Backup gagal", "Backup tidak dapat diselesaikan.", parent=self.root)

    def restore_backup(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Pilih file backup KasirKita",
            filetypes=[("Database SQLite", "*.sqlite3 *.db"), ("Semua file", "*.*")],
        )
        if not source:
            return
        if not messagebox.askyesno(
            "Konfirmasi pemulihan",
            "Pemulihan akan mengganti data KasirKita saat ini dengan isi backup. "
            "Lanjutkan hanya jika file backup benar dan buat backup data saat ini terlebih dahulu.",
            parent=self.root,
        ):
            return
        safety_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Simpan backup data saat ini sebelum pemulihan",
            defaultextension=".sqlite3",
            initialfile="kasirkita-sebelum-restore.sqlite3",
            filetypes=[("Database SQLite", "*.sqlite3"), ("Semua file", "*.*")],
        )
        if not safety_path:
            messagebox.showinfo(
                "Pemulihan dibatalkan",
                "Pilih lokasi backup data saat ini agar pemulihan dapat dilanjutkan dengan aman.",
                parent=self.root,
            )
            return
        try:
            source_path = Path(source).expanduser().resolve()
            safety_backup_path = Path(safety_path).expanduser().resolve()
            if source_path == safety_backup_path:
                raise BackupError("File backup sumber dan backup pengaman harus berbeda.")
            self.backup_service.create_backup(safety_path)
            self.backup_service.restore_backup(source)
            self.cart.clear()
            self.received_var.set("")
            self.refresh_cart()
            self.refresh_products()
            self.refresh_cashier_products()
            self.refresh_sales()
            messagebox.showinfo(
                "Pemulihan berhasil",
                "Database berhasil dipulihkan. Backup data sebelum pemulihan tersimpan di:\n"
                + safety_path,
                parent=self.root,
            )
        except BackupError as exc:
            messagebox.showerror("Pemulihan gagal", str(exc), parent=self.root)
        except Exception:
            logger.exception("Unexpected restore failure")
            messagebox.showerror(
                "Pemulihan gagal",
                "Pemulihan tidak dapat diselesaikan. Jangan hapus file backup atau database.",
                parent=self.root,
            )

    def refresh_sales(self) -> None:
        try:
            sales = self.sales_history.list_sales(
                search=self.history_search.get(), limit=500, offset=0
            )
            self._sales_rows = {item["id"]: item for item in sales}
            self.sales_tree.delete(*self.sales_tree.get_children())
            for sale in sales:
                self.sales_tree.insert(
                    "",
                    "end",
                    iid=str(sale["id"]),
                    values=(
                        sale["receipt_number"],
                        sale["created_at"],
                        "Selesai" if sale["status"] == "completed" else "Dibatalkan",
                        format_rupiah(sale["total_rupiah"]),
                    ),
                )
        except Exception:
            logger.exception("Failed to refresh sales history")
            messagebox.showerror("Kesalahan", "Riwayat transaksi gagal dimuat.", parent=self.root)

    def view_selected_sale(self) -> None:
        selection = self.sales_tree.selection()
        if not selection:
            messagebox.showinfo("Pilih transaksi", "Pilih transaksi terlebih dahulu.", parent=self.root)
            return
        try:
            sale = self.sales_history.get_sale_detail(int(selection[0]))
            if sale is None:
                messagebox.showerror(
                    "Transaksi tidak ditemukan",
                    "Transaksi tidak ditemukan. Muat ulang riwayat transaksi.",
                    parent=self.root,
                )
                self.refresh_sales()
                return
        except SalesHistoryValidationError as exc:
            messagebox.showerror("ID transaksi tidak valid", str(exc), parent=self.root)
            return
        except Exception:
            logger.exception("Failed to load sale detail")
            messagebox.showerror("Kesalahan", "Detail transaksi gagal dimuat.", parent=self.root)
            return

        window = tk.Toplevel(self.root)
        window.title("Detail " + sale["receipt_number"])
        window.geometry("760x460")
        window.minsize(620, 360)
        window.transient(self.root)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=sale["receipt_number"], style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text="Waktu UTC: " + sale["created_at"] + "   •   Status: " + sale["status"],
        ).pack(anchor="w", pady=(4, 12))
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        lines = ttk.Treeview(
            table_frame,
            columns=("sku", "name", "qty", "price", "subtotal"),
            show="headings",
        )
        for key, label, width in [
            ("sku", "SKU", 90),
            ("name", "Produk", 210),
            ("qty", "Qty", 50),
            ("price", "Harga", 110),
            ("subtotal", "Subtotal", 120),
        ]:
            lines.heading(key, text=label)
            lines.column(key, width=width, anchor="w")
        lines.grid(row=0, column=0, sticky="nsew")
        line_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=lines.yview)
        line_scroll.grid(row=0, column=1, sticky="ns")
        lines.configure(yscrollcommand=line_scroll.set)
        for line in sale["items"]:
            lines.insert(
                "",
                "end",
                values=(
                    line["sku"],
                    line["name"],
                    line["quantity"],
                    format_rupiah(line["unit_price_rupiah"]),
                    format_rupiah(line["line_total_rupiah"]),
                ),
            )

        payment_text = ", ".join(
            payment["method"] + ": " + format_rupiah(payment["amount_rupiah"])
            for payment in sale["payments"]
        ) or "Tidak ada catatan pembayaran (total transaksi Rp 0)."
        ttk.Label(frame, text="Pembayaran: " + payment_text, wraplength=700).pack(
            anchor="w", pady=(10, 4)
        )
        ttk.Label(
            frame,
            text="Subtotal: " + format_rupiah(sale["subtotal_rupiah"])
            + "  |  Pajak: " + format_rupiah(sale["tax_rupiah"])
            + "  |  Total: " + format_rupiah(sale["total_rupiah"]),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="e", pady=(2, 0))
        ttk.Button(frame, text="Tutup", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def refresh_products(self) -> None:
        try:
            products = self.catalog.list_products(
                self.product_search.get(), include_inactive=True
            )
            self._product_rows = {item["id"]: item for item in products}
            self.product_tree.delete(*self.product_tree.get_children())
            for item in products:
                self.product_tree.insert(
                    "",
                    "end",
                    iid=str(item["id"]),
                    values=(
                        item["sku"],
                        item["name"],
                        format_rupiah(item["unit_price_rupiah"]),
                        item["stock_quantity"],
                        "Aktif" if item["is_active"] else "Nonaktif",
                    ),
                )
        except Exception:
            logger.exception("Failed to refresh product catalogue")
            messagebox.showerror("Kesalahan", "Katalog produk gagal dimuat.", parent=self.root)

    def refresh_cashier_products(self) -> None:
        try:
            products = self.catalog.list_products(self.cashier_search.get())
            self.cashier_product_tree.delete(*self.cashier_product_tree.get_children())
            for item in products:
                self.cashier_product_tree.insert(
                    "",
                    "end",
                    iid=str(item["id"]),
                    values=(
                        item["sku"],
                        item["name"],
                        format_rupiah(item["unit_price_rupiah"]),
                        item["stock_quantity"],
                    ),
                )
        except Exception:
            logger.exception("Failed to refresh cashier product list")
            messagebox.showerror("Kesalahan", "Daftar produk kasir gagal dimuat.", parent=self.root)

    def add_product(self) -> None:
        dialog = ProductDialog(self.root, "Tambah produk")
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.catalog.create_product(
                dialog.result["sku"],
                dialog.result["name"],
                dialog.result["price"],
                dialog.result["stock"],
            )
            self.refresh_products()
            self.refresh_cashier_products()
            self.refresh_sales()
        except (ProductValidationError, DuplicateSKUError) as exc:
            messagebox.showerror("Produk tidak dapat disimpan", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to create product")
            messagebox.showerror("Kesalahan", "Produk gagal disimpan.", parent=self.root)

    def _selected_product(self) -> Optional[dict]:
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showinfo("Pilih produk", "Pilih produk terlebih dahulu.", parent=self.root)
            return None
        return self._product_rows.get(int(selection[0]))

    def edit_selected_product(self) -> None:
        product = self._selected_product()
        if product is None:
            return
        dialog = ProductDialog(self.root, "Edit detail produk", product)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.catalog.update_product(
                product["id"],
                dialog.result["sku"],
                dialog.result["name"],
                dialog.result["price"],
            )
            self.refresh_products()
            self.refresh_cashier_products()
        except (ProductValidationError, DuplicateSKUError, ProductNotFoundError) as exc:
            messagebox.showerror("Produk tidak dapat diperbarui", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to update product")
            messagebox.showerror("Kesalahan", "Perubahan produk gagal disimpan.", parent=self.root)

    def adjust_selected_stock(self) -> None:
        product = self._selected_product()
        if product is None:
            return
        dialog = StockAdjustmentDialog(self.root, product)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            updated_product = self.stock_service.adjust_stock(
                product["id"], dialog.result["delta"], dialog.result["note"]
            )
            self.refresh_products()
            self.refresh_cashier_products()
            direction = "ditambah" if dialog.result["delta"] > 0 else "dikurangi"
            messagebox.showinfo(
                "Stok diperbarui",
                "Stok " + updated_product["name"] + " berhasil " + direction
                + ". Stok sekarang: " + str(updated_product["stock_quantity"]) + " unit.",
                parent=self.root,
            )
        except (StockAdjustmentError, ProductNotFoundError) as exc:
            messagebox.showerror("Penyesuaian stok gagal", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to adjust product stock")
            messagebox.showerror("Kesalahan", "Penyesuaian stok gagal disimpan.", parent=self.root)

    def toggle_selected_product(self) -> None:
        product = self._selected_product()
        if product is None:
            return
        new_status = not product["is_active"]
        action = "mengaktifkan" if new_status else "menonaktifkan"
        if not messagebox.askyesno(
            "Konfirmasi",
            "Yakin ingin " + action + " produk " + product["name"] + "?",
            parent=self.root,
        ):
            return
        try:
            self.catalog.set_product_active(product["id"], new_status)
            self.refresh_products()
            self.refresh_cashier_products()
        except (ProductValidationError, ProductNotFoundError) as exc:
            messagebox.showerror("Produk tidak dapat diperbarui", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to change product active state")
            messagebox.showerror("Kesalahan", "Status produk gagal diubah.", parent=self.root)

    def add_selected_to_cart(self) -> None:
        selection = self.cashier_product_tree.selection()
        if not selection:
            messagebox.showinfo("Pilih produk", "Pilih produk yang ingin ditambahkan.", parent=self.root)
            return
        try:
            quantity_text = self.quantity_var.get().strip()
            if not quantity_text.isdigit():
                raise ValueError("Jumlah harus berupa bilangan bulat positif.")
            quantity = int(quantity_text)
            if quantity <= 0 or quantity > 2_147_483_647:
                raise ValueError("Jumlah harus lebih besar dari nol dan dalam batas yang didukung.")
            product_id = int(selection[0])
            product = self.catalog.get_product(product_id)
            if not product["is_active"]:
                raise ValueError("Produk sudah nonaktif.")
            new_quantity = self.cart.get(product_id, 0) + quantity
            if new_quantity > product["stock_quantity"]:
                raise ValueError("Jumlah di keranjang melebihi stok yang tersedia.")
            self.cart[product_id] = new_quantity
            self.refresh_cart()
        except (ValueError, ProductValidationError, ProductNotFoundError) as exc:
            messagebox.showerror("Jumlah tidak valid", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to add product to cart")
            messagebox.showerror("Kesalahan", "Produk gagal ditambahkan ke keranjang.", parent=self.root)

    def remove_selected_cart_item(self) -> None:
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showinfo("Pilih item", "Pilih item keranjang yang akan dihapus.", parent=self.root)
            return
        self.cart.pop(int(selection[0]), None)
        self.refresh_cart()

    def clear_cart(self) -> None:
        if not self.cart:
            return
        if messagebox.askyesno("Kosongkan keranjang", "Hapus semua item dari keranjang?", parent=self.root):
            self.cart.clear()
            self.refresh_cart()

    def refresh_cart(self) -> None:
        self.cart_tree.delete(*self.cart_tree.get_children())
        total = 0
        for product_id, quantity in self.cart.items():
            try:
                product = self.catalog.get_product(product_id)
            except ProductNotFoundError:
                continue
            line_total = product["unit_price_rupiah"] * quantity
            total += line_total
            self.cart_tree.insert(
                "",
                "end",
                iid=str(product_id),
                values=(
                    product["name"],
                    quantity,
                    format_rupiah(product["unit_price_rupiah"]),
                    format_rupiah(line_total),
                ),
            )
        self.total_var.set(format_rupiah(total))

    def process_checkout(self) -> None:
        if not self.cart:
            messagebox.showinfo("Keranjang kosong", "Tambahkan produk sebelum memproses pembayaran.", parent=self.root)
            return
        try:
            received = parse_rupiah_input(self.received_var.get())
        except ValueError as exc:
            messagebox.showerror("Nominal tidak valid", str(exc), parent=self.root)
            return

        if not messagebox.askyesno(
            "Konfirmasi pembayaran",
            "Proses transaksi dengan total " + self.total_var.get() + "?",
            parent=self.root,
        ):
            return

        items = [
            {"product_id": product_id, "quantity": quantity}
            for product_id, quantity in self.cart.items()
        ]
        try:
            result = self.checkout_service.checkout(items, received)
            messagebox.showinfo(
                "Transaksi berhasil",
                "Transaksi " + result["receipt_number"] + " berhasil.\n"
                + "Total: " + format_rupiah(result["total_rupiah"]) + "\n"
                + "Kembalian: " + format_rupiah(result["change_rupiah"]),
                parent=self.root,
            )
            self.cart.clear()
            self.received_var.set("")
            self.refresh_cart()
            self.refresh_products()
            self.refresh_cashier_products()
            self.refresh_sales()
        except CheckoutError as exc:
            messagebox.showerror("Transaksi tidak dapat diproses", str(exc), parent=self.root)
        except Exception:
            logger.exception("Unexpected checkout failure")
            messagebox.showerror(
                "Kesalahan transaksi",
                "Transaksi tidak dapat dipastikan selesai. Periksa riwayat transaksi sebelum mencoba lagi.",
                parent=self.root,
            )
            self.refresh_products()
            self.refresh_cashier_products()
