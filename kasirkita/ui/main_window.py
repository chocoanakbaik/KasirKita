"""Tkinter desktop interface for the initial KasirKita workflow."""
from __future__ import annotations

import csv
import logging
import re
import tkinter as tk
import webbrowser
from datetime import date
from decimal import Decimal, InvalidOperation
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
from kasirkita.services.report_export import SalesReportExportError, export_sales_report_csv
from kasirkita.services.tax_settings import TaxSettingsError, TaxSettingsService
from kasirkita.services.onboarding import OnboardingService
from kasirkita.services.stock import StockAdjustmentError, StockService

logger = logging.getLogger("kasirkita.ui")

CHOCO_AI_URL = "https://choco-ai-platform.netlify.app/"


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


def parse_tax_rate_basis_points(value: str) -> int:
    """Parse a percentage with at most two decimal places into basis points."""
    if not isinstance(value, str):
        raise ValueError("Tarif pajak harus berupa persentase.")
    cleaned = value.strip().replace(",", ".")
    if not re.fullmatch(r"(?:[0-9]{1,3})(?:\.[0-9]{1,2})?", cleaned):
        raise ValueError("Tarif gunakan angka 0 sampai 100, maksimal dua angka desimal.")
    try:
        rate = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Tarif pajak tidak valid.") from exc
    if rate < 0 or rate > 100:
        raise ValueError("Tarif pajak harus antara 0% dan 100%.")
    return int(rate * 100)


def format_tax_rate(rate_basis_points: int) -> str:
    whole, fraction = divmod(rate_basis_points, 100)
    if fraction == 0:
        return str(whole) + "%"
    return (str(whole) + "," + format(fraction, "02d").rstrip("0")) + "%"


class ProductDialog(tk.Toplevel):
    """Modal form for creating or editing a catalogue product."""

    def __init__(self, parent, title: str, product: Optional[dict] = None, code_generator=None) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._product = product
        self._code_generator = code_generator

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
            if key == "sku" and product is None and code_generator is not None:
                ttk.Button(
                    frame, text="Buat kode otomatis",
                    command=self._generate_code,
                ).grid(row=row, column=2, padx=(8, 0), pady=7)

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

    def _generate_code(self) -> None:
        if self._code_generator is None:
            return
        try:
            code = self._code_generator()
            self._entries["sku"].delete(0, "end")
            self._entries["sku"].insert(0, code)
        except Exception:
            messagebox.showerror("Kode gagal dibuat", "Kode internal tidak dapat dibuat. Coba lagi.", parent=self)

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
        tax_settings: TaxSettingsService,
        onboarding: OnboardingService,
    ) -> None:
        self.root = root
        self.catalog = catalog
        self.checkout_service = checkout
        self.sales_history = sales_history
        self.backup_service = backup_service
        self.stock_service = stock_service
        self.sales_report = sales_report
        self.tax_settings = tax_settings
        self.onboarding = onboarding
        self.cart: Dict[int, int] = {}
        self._product_rows: Dict[int, dict] = {}
        self._sales_rows: Dict[int, dict] = {}
        self._brand_logo = None

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
        self.load_tax_settings()
        self.root.after(1500, self._show_first_run_tutorial)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", foreground="#17212b")
        style.configure("TLabelframe", background="#f4f6f8")
        style.configure("TLabelframe.Label", background="#f4f6f8", foreground="#334155")
        style.configure("Header.TFrame", background="#172033")
        style.configure(
            "Header.TLabel",
            background="#172033",
            foreground="#ffffff",
            font=("Segoe UI", 19, "bold"),
        )
        style.configure(
            "HeaderMeta.TLabel",
            background="#172033",
            foreground="#67e8f9",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure("Subheader.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(10, 7), font=("Segoe UI", 9))
        style.configure(
            "Accent.TButton",
            background="#2563eb",
            foreground="#ffffff",
            padding=(12, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", "#1e40af"), ("active", "#1d4ed8")],
            foreground=[("disabled", "#94a3b8")],
        )
        style.configure(
            "TNotebook",
            background="#f4f6f8",
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            padding=(15, 9),
            background="#e2e8f0",
            foreground="#334155",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff"), ("active", "#dbeafe")],
            foreground=[("selected", "#1d4ed8")],
        )
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Segoe UI", 10),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#17212b",
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#1e3a8a")],
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#e8eef6",
            foreground="#1e293b",
            padding=(8, 7),
        )

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=16)
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell, style="Header.TFrame", padding=(14, 12))
        header.pack(fill="x", pady=(0, 12))
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.pack(side="left")
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "brand"
        try:
            from PIL import Image, ImageTk
            candidates = sorted(
                path for path in logo_path.iterdir()
                if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg")
            )
            if candidates:
                with Image.open(candidates[0]) as source_image:
                    source_image.thumbnail((40, 40))
                    self._brand_logo = ImageTk.PhotoImage(source_image.copy())
                ttk.Label(brand, image=self._brand_logo, style="Header.TLabel").pack(
                    side="left", padx=(0, 10)
                )
        except (ImportError, OSError, ValueError):
            logger.info("Brand logo unavailable; continuing with text branding.")
        ttk.Label(brand, text="KasirKita", style="Header.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="DESKTOP  •  LOKAL",
            style="HeaderMeta.TLabel",
        ).pack(side="right", padx=4)

        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        self.cashier_tab = ttk.Frame(self.tabs, padding=12)
        self.products_tab = ttk.Frame(self.tabs, padding=12)
        self.history_tab = ttk.Frame(self.tabs, padding=12)
        self.report_tab = ttk.Frame(self.tabs, padding=12)
        self.settings_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.cashier_tab, text="Kasir")
        self.tabs.add(self.products_tab, text="Produk")
        self.tabs.add(self.history_tab, text="Riwayat transaksi")
        self.tabs.add(self.report_tab, text="Laporan")
        self.tabs.add(self.settings_tab, text="Pengaturan")
        self._build_cashier_tab()
        self._build_products_tab()
        self._build_history_tab()
        self._build_report_tab()
        self._build_settings_tab()

        footer = ttk.Frame(shell, padding=(2, 9, 2, 0))
        footer.pack(fill="x", side="bottom")
        ttk.Label(
            footer,
            text="KasirKita bisa saja melakukan kesalahan.",
            foreground="#64748b",
        ).pack(side="left")
        ttk.Button(footer, text="Panduan / Tutorial", command=self.open_tutorial).pack(side="right", padx=(8, 0))
        self.support_link = tk.Label(
            footer,
            text="Klik di sini untuk melaporkan",
            foreground="#2563eb",
            background="#f4f6f8",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
        )
        self.support_link.pack(side="left", padx=(4, 0))
        self.support_link.bind("<Button-1>", self.open_support_page)
        self.support_link.bind("<Return>", self.open_support_page)
        self.support_link.configure(takefocus=True)
        self.support_link.bind("<Enter>", lambda _event: self.support_link.configure(foreground="#1d4ed8"))
        self.support_link.bind("<Leave>", lambda _event: self.support_link.configure(foreground="#2563eb"))

    def _show_first_run_tutorial(self) -> None:
        """Show onboarding only when no completed/skipped state exists locally."""
        try:
            if not self.onboarding.has_seen_tutorial() and self.root.winfo_exists():
                self.open_tutorial(first_run=True)
        except Exception:
            logger.exception("Unable to check first-run tutorial state")
            # Keep the main application usable even if onboarding state cannot be read.

    def open_tutorial(self, first_run: bool = False) -> None:
        """Open a lightweight offline, step-by-step introduction to the POS."""
        pages = [
            ("Selamat datang di KasirKita",
             "KasirKita berjalan secara lokal di komputer ini. Data transaksi dan produk disimpan di database lokal; koneksi internet tidak diperlukan untuk kegiatan kasir."),
            ("1. Siapkan katalog Produk",
             "Buka tab Produk, pilih Tambah produk, lalu isi SKU/kode unik, nama, harga dalam rupiah, dan stok awal. Periksa harga dan stok sebelum mulai melayani pembeli."),
            ("2. Catat stok dengan benar",
             "Gunakan Penyesuaian stok untuk mencatat barang masuk atau keluar. Isi alasan yang jelas agar perubahan stok dapat ditelusuri. Jangan menghapus atau mengubah database secara manual."),
            ("3. Lakukan transaksi",
             "Di tab Kasir, cari lalu pilih produk, tentukan jumlah, dan tambahkan ke keranjang. Periksa subtotal dan total, masukkan uang tunai yang diterima, lalu konfirmasi pembayaran. Stok berkurang saat transaksi berhasil disimpan."),
            ("4. Periksa riwayat dan laporan",
             "Riwayat transaksi menampilkan transaksi yang tersimpan dan detail struk. Laporan merangkum penjualan pada tanggal yang dipilih dan dapat diekspor. Cocokkan laporan dengan catatan kas usaha."),
            ("5. Pajak, backup, dan keamanan data",
             "Pajak tidak aktif secara default. Aktifkan hanya setelah label dan tarif diverifikasi untuk usaha Anda. Buat backup rutin ke lokasi berbeda dan simpan file backup dengan aman. Pemulihan backup mengganti data aktif."),
            ("Selesai — mulai dengan data yang benar",
             "Sebelum dipakai untuk transaksi sungguhan, masukkan katalog yang benar, cek harga dan stok, lalu lakukan pengujian transaksi. KasirKita adalah alat bantu pencatatan, bukan pengganti pemeriksaan akuntansi atau kewajiban pajak."),
        ]
        window = tk.Toplevel(self.root)
        window.title("Panduan KasirKita")
        window.geometry("620x360")
        window.minsize(520, 320)
        window.transient(self.root)
        window.grab_set()
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(22, 18, 22, 8))
        header.grid(row=0, column=0, sticky="ew")
        title_var = tk.StringVar()
        progress_var = tk.StringVar()
        ttk.Label(header, textvariable=title_var, style="Subheader.TLabel").pack(anchor="w")
        ttk.Label(header, textvariable=progress_var, foreground="#64748b").pack(anchor="w", pady=(5, 0))
        body = ttk.Frame(window, padding=(22, 8, 22, 14))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        body_text = tk.Text(body, wrap="word", height=7, width=60, relief="flat",
                            background="#ffffff", foreground="#17212b",
                            font=("Segoe UI", 11), padx=12, pady=12)
        body_text.grid(row=0, column=0, sticky="nsew")
        body_text.configure(state="disabled")
        actions = ttk.Frame(window, padding=(22, 0, 22, 18))
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        index = [0]

        def render_page() -> None:
            title, text = pages[index[0]]
            title_var.set(title)
            progress_var.set("Langkah " + str(index[0] + 1) + " dari " + str(len(pages)))
            body_text.configure(state="normal")
            body_text.delete("1.0", "end")
            body_text.insert("1.0", text)
            body_text.configure(state="disabled")
            back_button.configure(state="normal" if index[0] else "disabled")
            next_button.configure(text="Selesai" if index[0] == len(pages) - 1 else "Lanjut")
            skip_button.configure(state="normal" if index[0] < len(pages) - 1 else "disabled")

        def close_as_skipped() -> None:
            try:
                self.onboarding.mark_skipped()
            except Exception:
                logger.exception("Could not persist skipped tutorial state")
            window.destroy()

        def go_next() -> None:
            if index[0] < len(pages) - 1:
                index[0] += 1
                render_page()
                return
            try:
                self.onboarding.mark_completed()
            except Exception:
                logger.exception("Could not persist completed tutorial state")
                messagebox.showwarning(
                    "Panduan belum tersimpan",
                    "Panduan selesai, tetapi statusnya tidak bisa disimpan. Panduan mungkin muncul lagi saat aplikasi dibuka.",
                    parent=window,
                )
            window.destroy()

        def go_back() -> None:
            if index[0] > 0:
                index[0] -= 1
                render_page()

        ttk.Button(actions, text="Lewati", command=close_as_skipped).grid(row=0, column=1, sticky="e")
        back_button = ttk.Button(actions, text="Kembali", command=go_back)
        back_button.grid(row=0, column=2, padx=(8, 0))
        next_button = ttk.Button(actions, text="Lanjut", style="Accent.TButton", command=go_next)
        next_button.grid(row=0, column=3, padx=(8, 0))
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.bind("<Escape>", lambda _event: window.destroy())
        render_page()

    def open_support_page(self, _event=None) -> None:
        """Open the official Choco AI support platform in the default browser."""
        try:
            webbrowser.open(CHOCO_AI_URL, new=2)
        except Exception:
            logger.exception("Unable to open the support page")
            messagebox.showerror(
                "Bantuan tidak dapat dibuka",
                "Halaman bantuan tidak dapat dibuka otomatis. Buka alamat berikut di browser:\n"
                + CHOCO_AI_URL,
                parent=self.root,
            )

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
        product_frame.rowconfigure(3, weight=1)
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
        barcode_frame = ttk.Frame(product_frame)
        barcode_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(barcode_frame, text="Barcode / SKU").pack(side="left")
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(barcode_frame, textvariable=self.barcode_var)
        self.barcode_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.barcode_entry.bind("<Return>", self.scan_barcode_to_cart)
        ttk.Button(barcode_frame, text="Cari & tambah", command=self.scan_barcode_to_cart).pack(side="left")
        ttk.Label(
            product_frame,
            text="Scanner USB mode keyboard dapat langsung mengirim kode ke kolom ini. Tanpa scanner, ketik SKU lalu tekan Enter.",
            foreground="#596777",
            wraplength=470,
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

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
        self.cashier_product_tree.grid(row=3, column=0, sticky="nsew")
        product_scroll = ttk.Scrollbar(
            product_frame, orient="vertical", command=self.cashier_product_tree.yview
        )
        product_scroll.grid(row=3, column=1, sticky="ns")
        self.cashier_product_tree.configure(yscrollcommand=product_scroll.set)
        self.cashier_product_tree.bind("<Double-1>", lambda _event: self.add_selected_to_cart())

        add_frame = ttk.Frame(product_frame)
        add_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
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
        self.subtotal_var = tk.StringVar(value=format_rupiah(0))
        self.tax_label_var = tk.StringVar(value="Pajak (nonaktif)")
        self.tax_var = tk.StringVar(value=format_rupiah(0))
        self.total_var = tk.StringVar(value=format_rupiah(0))
        ttk.Label(totals, text="Subtotal").pack(anchor="w")
        ttk.Label(totals, textvariable=self.subtotal_var).pack(anchor="w", pady=(1, 5))
        ttk.Label(totals, textvariable=self.tax_label_var).pack(anchor="w")
        ttk.Label(totals, textvariable=self.tax_var).pack(anchor="w", pady=(1, 5))
        ttk.Label(totals, text="Total transaksi", style="Subheader.TLabel").pack(anchor="w")
        ttk.Label(totals, textvariable=self.total_var, font=("Segoe UI", 20, "bold")).pack(
            anchor="w", pady=(2, 10)
        )
        ttk.Label(totals, text="Uang diterima (tunai)").pack(anchor="w")
        self.received_var = tk.StringVar()
        ttk.Entry(totals, textvariable=self.received_var).pack(fill="x", pady=(3, 8))
        ttk.Button(
            totals,
            text="PROSES PEMBAYARAN",
            command=self.process_checkout,
            style="Accent.TButton",
        ).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Label(
            totals,
            text="Tarif pajak mengikuti pengaturan usaha; periksa status pajak dan ketentuan yang berlaku.",
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
        ttk.Button(toolbar, text="Ekspor katalog CSV", command=self.export_products_csv).pack(side="right", padx=8)
        ttk.Button(toolbar, text="Buat label barcode SVG", command=self.export_selected_barcode_svg).pack(side="right", padx=8)
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
        ttk.Button(toolbar, text="Ekspor CSV", command=self.export_report_csv).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(toolbar, text="Ekspor Excel", command=self.export_report_xlsx).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(toolbar, text="Ekspor PDF", command=self.export_report_pdf).pack(
            side="left", padx=(6, 0)
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

    def export_products_csv(self) -> None:
        """Export the current product catalogue view to a spreadsheet-friendly CSV."""
        try:
            products = self.catalog.list_products(
                self.product_search.get(), include_inactive=True
            )
        except Exception:
            logger.exception("Failed to prepare product catalogue for export")
            messagebox.showerror(
                "Ekspor gagal",
                "Katalog produk tidak dapat disiapkan untuk ekspor.",
                parent=self.root,
            )
            return

        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Ekspor katalog produk",
            defaultextension=".csv",
            filetypes=[("CSV UTF-8", "*.csv"), ("Semua file", "*.*")],
            initialfile="katalog-produk.csv",
        )
        if not destination:
            return
        try:
            path = Path(destination).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream, delimiter=";", lineterminator="\n")
                writer.writerow(
                    ["SKU", "Nama produk", "Harga (rupiah)", "Stok", "Status"]
                )
                for product in products:
                    writer.writerow([
                        product["sku"],
                        product["name"],
                        product["unit_price_rupiah"],
                        product["stock_quantity"],
                        "Aktif" if product["is_active"] else "Nonaktif",
                    ])
            messagebox.showinfo(
                "Ekspor berhasil",
                "Katalog produk berhasil disimpan ke:\n" + str(path),
                parent=self.root,
            )
        except (OSError, csv.Error, ValueError):
            logger.exception("Failed to write product catalogue CSV")
            messagebox.showerror(
                "Ekspor gagal",
                "File katalog tidak dapat disimpan. Periksa izin folder dan ruang disk.",
                parent=self.root,
            )

    def export_report_csv(self) -> None:
        """Export the currently selected date range as an Excel-friendly CSV."""
        try:
            report = self.sales_report.summarize(
                self.report_start_var.get().strip(),
                self.report_end_var.get().strip(),
            )
        except SalesReportValidationError as exc:
            messagebox.showerror("Rentang tanggal tidak valid", str(exc), parent=self.root)
            return
        except Exception:
            logger.exception("Failed to prepare sales report for export")
            messagebox.showerror("Ekspor gagal", "Laporan penjualan tidak dapat disiapkan.", parent=self.root)
            return

        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Ekspor laporan penjualan",
            defaultextension=".csv",
            filetypes=[("CSV UTF-8", "*.csv"), ("Semua file", "*.*")],
            initialfile="laporan-penjualan-"
            + report["start_date"]
            + "-hingga-"
            + report["end_date"]
            + ".csv",
        )
        if not destination:
            return
        try:
            path = export_sales_report_csv(report, destination)
            messagebox.showinfo(
                "Ekspor berhasil",
                "Laporan CSV berhasil disimpan:\\n" + str(path),
                parent=self.root,
            )
        except SalesReportExportError as exc:
            messagebox.showerror("Ekspor gagal", str(exc), parent=self.root)
        except Exception:
            logger.exception("Unexpected sales report export failure")
            messagebox.showerror("Ekspor gagal", "File laporan tidak dapat disimpan.", parent=self.root)

    def _export_report_document(self, kind: str) -> None:
        try:
            report = self.sales_report.summarize(
                self.report_start_var.get().strip(), self.report_end_var.get().strip()
            )
        except SalesReportValidationError as exc:
            messagebox.showerror("Rentang tanggal tidak valid", str(exc), parent=self.root)
            return
        extension = ".xlsx" if kind == "xlsx" else ".pdf"
        title = "Ekspor laporan Excel" if kind == "xlsx" else "Ekspor laporan PDF"
        destination = filedialog.asksaveasfilename(
            parent=self.root, title=title, defaultextension=extension,
            filetypes=[(extension.upper() + " file", "*" + extension), ("Semua file", "*.*")],
            initialfile="laporan-penjualan-" + report["start_date"] + "-hingga-" + report["end_date"] + extension,
        )
        if not destination:
            return
        try:
            from kasirkita.services.document_export import (
                DocumentExportError, export_sales_report_pdf, export_sales_report_xlsx,
            )
            path = export_sales_report_xlsx(report, destination) if kind == "xlsx" else export_sales_report_pdf(report, destination)
            messagebox.showinfo("Ekspor berhasil", "Laporan berhasil disimpan:\n" + str(path), parent=self.root)
        except Exception as exc:
            logger.exception("Report document export failed")
            messagebox.showerror("Ekspor gagal", str(exc) if isinstance(exc, DocumentExportError) else "File laporan tidak dapat disimpan.", parent=self.root)

    def export_report_xlsx(self) -> None:
        self._export_report_document("xlsx")

    def export_report_pdf(self) -> None:
        self._export_report_document("pdf")

    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)
        frame = ttk.LabelFrame(self.settings_tab, text="Pajak penjualan / PPN", padding=18)
        frame.grid(row=0, column=0, sticky="nw")
        frame.columnconfigure(1, weight=1)
        self.tax_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Aktifkan pajak untuk transaksi baru",
            variable=self.tax_enabled_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Label pajak").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 16))
        self.tax_label_entry = ttk.Entry(frame, width=32)
        self.tax_label_entry.insert(0, "PPN")
        self.tax_label_entry.grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Label(frame, text="Tarif (%)").grid(row=2, column=0, sticky="w", pady=6)
        self.tax_rate_entry = ttk.Entry(frame, width=32)
        self.tax_rate_entry.insert(0, "0")
        self.tax_rate_entry.grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Label(frame, text="Cara memasukkan harga").grid(
            row=3, column=0, sticky="w", pady=6
        )
        self.tax_mode_var = tk.StringVar(value="exclusive")
        self.tax_mode_combo = ttk.Combobox(
            frame,
            textvariable=self.tax_mode_var,
            values=("Belum termasuk pajak", "Sudah termasuk pajak"),
            state="readonly",
            width=29,
        )
        self.tax_mode_combo.grid(row=3, column=1, sticky="ew", pady=6)
        self.tax_mode_combo.set("Belum termasuk pajak")
        ttk.Button(
            frame,
            text="Simpan pengaturan pajak",
            command=self.save_tax_settings,
            style="Accent.TButton",
        ).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(12, 8)
        )
        ttk.Label(
            frame,
            text=(
                "Pajak nonaktif secara default. Tarif tidak diisi otomatis. "
                "Masukkan tarif yang sesuai dengan status usaha dan aturan yang berlaku. "
                "Pengaturan ini adalah alat hitung, bukan sertifikasi kepatuhan pajak."
            ),
            wraplength=520,
            foreground="#596777",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def load_tax_settings(self) -> None:
        try:
            config = self.tax_settings.get_config()
            self.tax_enabled_var.set(config["enabled"])
            self.tax_rate_entry.delete(0, "end")
            self.tax_rate_entry.insert(0, format_tax_rate(config["rate_basis_points"]).replace("%", ""))
            self.tax_label_entry.delete(0, "end")
            self.tax_label_entry.insert(0, config["label"])
            self.tax_mode_combo.set(
                "Sudah termasuk pajak" if config["mode"] == "inclusive"
                else "Belum termasuk pajak"
            )
        except TaxSettingsError:
            logger.exception("Stored tax settings are invalid")
            messagebox.showerror(
                "Pengaturan pajak tidak valid",
                "Pengaturan pajak tersimpan tidak valid. Pajak tidak boleh digunakan sampai diperbaiki.",
                parent=self.root,
            )

    def save_tax_settings(self) -> None:
        try:
            rate = parse_tax_rate_basis_points(self.tax_rate_entry.get())
            mode = "inclusive" if self.tax_mode_combo.get() == "Sudah termasuk pajak" else "exclusive"
            config = self.tax_settings.save_config(
                self.tax_enabled_var.get(),
                rate,
                mode,
                self.tax_label_entry.get(),
            )
            self.refresh_cart()
            messagebox.showinfo(
                "Pengaturan tersimpan",
                "Pengaturan pajak untuk transaksi baru berhasil disimpan. "
                "Transaksi lama tetap menggunakan catatan pajak saat transaksi dibuat.",
                parent=self.root,
            )
        except (ValueError, TaxSettingsError) as exc:
            messagebox.showerror("Pengaturan tidak valid", str(exc), parent=self.root)
        except Exception:
            logger.exception("Failed to save tax settings")
            messagebox.showerror("Kesalahan", "Pengaturan pajak gagal disimpan.", parent=self.root)

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
        tax_description = (
            sale["tax_label"] + " " + format_tax_rate(sale["tax_rate_basis_points"])
            + (" (termasuk harga)" if sale["tax_mode"] == "inclusive" else " (di luar harga)")
            if sale["tax_enabled"] else "Pajak nonaktif"
        )
        ttk.Label(
            frame,
            text="Subtotal: " + format_rupiah(sale["subtotal_rupiah"])
            + "  |  " + tax_description + ": " + format_rupiah(sale["tax_rupiah"])
            + "  |  Total: " + format_rupiah(sale["total_rupiah"]),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="e", pady=(2, 0))
        def save_receipt_text() -> None:
            """Export the persisted receipt snapshot to a UTF-8 text file."""
            suggested = sale["receipt_number"].replace("/", "-") + ".txt"
            destination = filedialog.asksaveasfilename(
                parent=window,
                title="Simpan struk transaksi",
                defaultextension=".txt",
                initialfile=suggested,
                filetypes=(("Struk teks UTF-8", "*.txt"), ("Semua file", "*.*")),
            )
            if not destination:
                return
            receipt_lines = [
                "KASIRKITA",
                "=" * 36,
                "Nomor struk : " + str(sale["receipt_number"]),
                "Waktu (UTC) : " + str(sale["created_at"]),
                "Status      : " + str(sale["status"]),
                "-" * 36,
            ]
            for item in sale["items"]:
                receipt_lines.extend([
                    str(item["name"]),
                    "  " + str(item["quantity"]) + " x " + format_rupiah(item["unit_price_rupiah"]),
                    "  Subtotal: " + format_rupiah(item["line_total_rupiah"]),
                ])
            receipt_lines.extend([
                "-" * 36,
                "Subtotal: " + format_rupiah(sale["subtotal_rupiah"]),
                tax_description + ": " + format_rupiah(sale["tax_rupiah"]),
                "TOTAL: " + format_rupiah(sale["total_rupiah"]),
                "Pembayaran: " + payment_text,
                "",
                "Struk dibuat dari data transaksi yang tersimpan.",
                "KasirKita dapat melakukan kesalahan; periksa kembali data transaksi.",
            ])
            try:
                with open(destination, "w", encoding="utf-8", newline="\n") as receipt_file:
                    receipt_file.write("\n".join(receipt_lines) + "\n")
            except OSError:
                logger.exception("Failed to export receipt")
                messagebox.showerror(
                    "Struk gagal disimpan",
                    "File struk tidak dapat disimpan. Periksa izin folder dan ruang disk.",
                    parent=window,
                )
                return
            messagebox.showinfo(
                "Struk disimpan",
                "Struk berhasil disimpan sebagai file teks.",
                parent=window,
            )

        def save_receipt_pdf() -> None:
            """Export the persisted receipt snapshot as a standalone PDF."""
            destination = filedialog.asksaveasfilename(
                parent=window, title="Simpan struk PDF", defaultextension=".pdf",
                initialfile=sale["receipt_number"].replace("/", "-") + ".pdf",
                filetypes=(("Dokumen PDF", "*.pdf"), ("Semua file", "*.*")),
            )
            if not destination:
                return
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import mm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                target = Path(destination).expanduser()
                target.parent.mkdir(parents=True, exist_ok=True)
                styles = getSampleStyleSheet()
                story = [
                    Paragraph("KasirKita — Struk Transaksi", styles["Title"]),
                    Paragraph("Nomor: " + str(sale["receipt_number"]), styles["Normal"]),
                    Paragraph("Waktu UTC: " + str(sale["created_at"]), styles["Normal"]),
                    Paragraph("Status: " + str(sale["status"]), styles["Normal"]),
                    Spacer(1, 6 * mm),
                ]
                rows = [["Produk", "Qty", "Harga", "Subtotal"]]
                for item in sale["items"]:
                    rows.append([
                        str(item["name"])[:100], str(item["quantity"]),
                        format_rupiah(item["unit_price_rupiah"]),
                        format_rupiah(item["line_total_rupiah"]),
                    ])
                story.append(Table(rows, repeatRows=1, colWidths=[75*mm, 15*mm, 35*mm, 35*mm],
                    style=TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12304A")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCD5DE")),
                        ("PADDING", (0, 0), (-1, -1), 5),
                    ])))
                story.extend([
                    Spacer(1, 5 * mm),
                    Paragraph("Subtotal: " + format_rupiah(sale["subtotal_rupiah"]), styles["Normal"]),
                    Paragraph(tax_description + ": " + format_rupiah(sale["tax_rupiah"]), styles["Normal"]),
                    Paragraph("<b>TOTAL: " + format_rupiah(sale["total_rupiah"]) + "</b>", styles["Heading2"]),
                    Paragraph("Pembayaran: " + payment_text, styles["Normal"]),
                    Spacer(1, 4 * mm),
                    Paragraph("Struk dibuat dari data transaksi tersimpan. Periksa kembali data transaksi.", styles["Italic"]),
                ])
                SimpleDocTemplate(str(target), pagesize=A4, rightMargin=15*mm,
                    leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm).build(story)
                messagebox.showinfo("Struk disimpan", "Struk PDF berhasil disimpan:\\n" + str(target), parent=window)
            except Exception:
                logger.exception("Failed to export receipt PDF")
                messagebox.showerror("Struk gagal disimpan", "PDF struk tidak dapat dibuat. Periksa izin folder dan dependensi.", parent=window)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", anchor="e", pady=(10, 0))
        ttk.Button(actions, text="Simpan struk TXT", command=save_receipt_text).pack(side="left")
        ttk.Button(actions, text="Simpan struk PDF", command=save_receipt_pdf).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Tutup", command=window.destroy).pack(side="right")

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
        dialog = ProductDialog(self.root, "Tambah produk", code_generator=self.next_internal_code)
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

    def export_selected_barcode_svg(self) -> None:
        """Save a printable vector barcode for the selected product SKU."""
        product = self._selected_product()
        if product is None:
            return
        destination = filedialog.asksaveasfilename(
            parent=self.root, title="Simpan label barcode SVG",
            defaultextension=".svg",
            initialfile=str(product["sku"]).replace("/", "-") + "-barcode.svg",
            filetypes=[("Barcode SVG", "*.svg"), ("Semua file", "*.*")],
        )
        if not destination:
            return
        try:
            import barcode
            from barcode.writer import SVGWriter
            code = barcode.get("code128", product["sku"], writer=SVGWriter())
            target = Path(destination).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            generated = code.render(writer_options={
                "module_width": 0.25, "module_height": 15.0,
                "quiet_zone": 3.0, "font_size": 10, "text_distance": 3.0,
                "write_text": True,
            })
            target.write_bytes(generated)
            messagebox.showinfo(
                "Label barcode disimpan",
                "Barcode Code 128 untuk SKU " + str(product["sku"]) +
                " berhasil disimpan sebagai SVG. File dapat dicetak atau dibuka di editor vektor.",
                parent=self.root,
            )
        except ImportError:
            messagebox.showerror(
                "Dependensi tidak tersedia",
                "Pembuatan barcode memerlukan paket python-barcode dari build KasirKita.",
                parent=self.root,
            )
        except Exception:
            logger.exception("Barcode SVG export failed")
            messagebox.showerror("Label gagal dibuat", "Label barcode tidak dapat disimpan.", parent=self.root)

    def next_internal_code(self) -> str:
        """Return the first unused store-local SKU code."""
        from kasirkita.services.barcode import make_internal_code
        products = self.catalog.list_products("", include_inactive=True)
        used = {str(product["sku"]).upper() for product in products}
        sequence = 1
        while sequence <= 2_147_483_647:
            candidate = make_internal_code(sequence)
            if candidate not in used:
                return candidate
            sequence += 1
        raise RuntimeError("Tidak ada nomor kode internal yang tersedia.")

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

    def scan_barcode_to_cart(self, _event=None) -> None:
        """Handle keyboard-emulating USB scanner input or a manually typed SKU."""
        from kasirkita.services.barcode import BarcodeValidationError, normalize_barcode
        code = self.barcode_var.get()
        try:
            code = normalize_barcode(code)
            matches = self.catalog.list_products(code, include_inactive=False)
            product = next((item for item in matches if item["sku"] == code), None)
            if product is None:
                messagebox.showwarning(
                    "Kode tidak ditemukan",
                    "Belum ada produk aktif dengan SKU/barcode tersebut. Tambahkan produk terlebih dahulu atau periksa kodenya.",
                    parent=self.root,
                )
                self.barcode_entry.focus_set()
                self.barcode_entry.selection_range(0, "end")
                return
            quantity_text = self.quantity_var.get().strip()
            if not quantity_text.isdigit() or int(quantity_text) <= 0:
                raise ValueError("Jumlah harus berupa bilangan bulat positif.")
            quantity = int(quantity_text)
            if quantity > 2_147_483_647:
                raise ValueError("Jumlah melebihi batas yang didukung.")
            new_quantity = self.cart.get(product["id"], 0) + quantity
            if new_quantity > product["stock_quantity"]:
                raise ValueError("Jumlah di keranjang melebihi stok yang tersedia.")
            self.cart[product["id"]] = new_quantity
            self.barcode_var.set("")
            self.refresh_cart()
            self.barcode_entry.focus_set()
        except (BarcodeValidationError, ValueError, ProductValidationError) as exc:
            messagebox.showerror("Kode / jumlah tidak valid", str(exc), parent=self.root)
        except Exception:
            logger.exception("Barcode lookup failed")
            messagebox.showerror("Kesalahan", "Produk tidak dapat dicari dari kode tersebut.", parent=self.root)

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
        cart_items = [
            {"product_id": product_id, "quantity": quantity}
            for product_id, quantity in self.cart.items()
        ]
        for product_id, quantity in self.cart.items():
            try:
                product = self.catalog.get_product(product_id)
            except ProductNotFoundError:
                continue
            line_total = product["unit_price_rupiah"] * quantity
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
        try:
            preview = self.checkout_service.preview(cart_items) if cart_items else {
                "subtotal_rupiah": 0,
                "tax_rupiah": 0,
                "total_rupiah": 0,
                "tax_enabled": False,
                "tax_rate_basis_points": 0,
                "tax_mode": "exclusive",
                "tax_label": "Pajak",
            }
            self.subtotal_var.set(format_rupiah(preview["subtotal_rupiah"]))
            self.tax_var.set(format_rupiah(preview["tax_rupiah"]))
            if preview["tax_enabled"]:
                mode_text = (
                    "termasuk harga" if preview["tax_mode"] == "inclusive"
                    else "di luar harga"
                )
                self.tax_label_var.set(
                    preview["tax_label"] + " " + format_tax_rate(preview["tax_rate_basis_points"])
                    + " (" + mode_text + ")"
                )
            else:
                self.tax_label_var.set("Pajak (nonaktif)")
            self.total_var.set(format_rupiah(preview["total_rupiah"]))
        except CheckoutError:
            self.subtotal_var.set("-")
            self.tax_label_var.set("Periksa keranjang")
            self.tax_var.set("-")
            self.total_var.set("Periksa keranjang")

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
            tax_description = (
                result["tax_label"] + " " + format_tax_rate(result["tax_rate_basis_points"])
                if result["tax_enabled"] else "Pajak nonaktif"
            )
            messagebox.showinfo(
                "Transaksi berhasil",
                "Transaksi " + result["receipt_number"] + " berhasil.\n"
                + "Subtotal: " + format_rupiah(result["subtotal_rupiah"]) + "\n"
                + tax_description + ": " + format_rupiah(result["tax_rupiah"]) + "\n"
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
