"""Attach post-login modules and checkout options to the existing POS interface."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from kasirkita.services.accounts import AccountService
from kasirkita.services.contacts import ContactService
from kasirkita.services.operations import OperationError
from kasirkita.ui.contacts_panel import ContactsPanel
from kasirkita.ui.employee_management import EmployeeManagementDialog
from kasirkita.ui.operations_panel import OperationsPanel


def _parse_discount(value):
    cleaned = str(value).strip()
    if cleaned.isdigit():
        return int(cleaned)
    if cleaned and all(part.isdigit() for part in cleaned.split(".")) and all(len(part) == 3 for part in cleaned.split(".")[1:]):
        return int(cleaned.replace(".", ""))
    raise OperationError("Masukkan nominal diskon rupiah bulat.")


class DiscountCheckoutProxy:
    def __init__(self, checkout):
        self.service = checkout
        self.discount_rupiah = 0

    def preview(self, items):
        return self.service.preview(items, discount_rupiah=self.discount_rupiah)

    def checkout_sale(self, items, amount_received_rupiah):
        result = self.service.checkout(items, amount_received_rupiah, discount_rupiah=self.discount_rupiah)
        self.discount_rupiah = 0
        if hasattr(self, "button"):
            self.button.configure(text="Diskon: Rp 0")
        return result

    def checkout(self, items, amount_received_rupiah):
        return self.checkout_sale(items, amount_received_rupiah)


def _walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def attach_post_login_features(main_window, root, contacts, accounts, session, on_logout, connection):
    """Add contact, operations, discount, employee, and logout controls."""
    contacts_tab = ttk.Frame(main_window.tabs, padding=8)
    main_window.tabs.add(contacts_tab, text="Pelanggan & Supplier")
    ContactsPanel(contacts_tab, contacts).pack(fill="both", expand=True)

    operations_tab = ttk.Frame(main_window.tabs, padding=8)
    main_window.tabs.add(operations_tab, text="Operasional")
    OperationsPanel(operations_tab, connection).pack(fill="both", expand=True)

    proxy = DiscountCheckoutProxy(main_window.checkout_service)
    main_window.checkout_service = proxy
    pay_button = next((widget for widget in _walk(main_window.cashier_tab)
                       if isinstance(widget, ttk.Button) and widget.cget("text") == "PROSES PEMBAYARAN"), None)
    if pay_button is not None:
        def set_discount():
            current = proxy.discount_rupiah
            value = simpledialog.askstring(
                "Diskon transaksi", "Nominal diskon rupiah (0 untuk menghapus):",
                initialvalue=str(current), parent=root,
            )
            if value is None:
                return
            try:
                amount = _parse_discount(value)
                items = [{"product_id": pid, "quantity": qty} for pid, qty in main_window.cart.items()]
                if amount:
                    preview = proxy.service.preview(items)
                    if amount > preview["gross_amount_rupiah"]:
                        raise OperationError("Diskon tidak boleh melebihi nilai keranjang.")
                proxy.discount_rupiah = amount
            except (ValueError, OperationError) as exc:
                messagebox.showerror("Diskon tidak valid", str(exc), parent=root)
                return
            discount_button.configure(text="Diskon aktif: {}".format("Rp " + format(amount, ",").replace(",", ".")))
            main_window.refresh_cart()

        discount_button = ttk.Button(pay_button.master, text="Diskon: Rp 0", command=set_discount)
        proxy.button = discount_button
        discount_button.pack(before=pay_button, fill="x", pady=(0, 6))

    bar = ttk.Frame(root, padding=(10, 5))
    bar.pack(side="bottom", fill="x")
    role_label = "Pemilik" if session.get("role") == "owner" else "Pegawai"
    ttk.Label(bar, text="Login: {} ({})".format(session.get("display_name", ""), role_label)).pack(side="left")
    if session.get("role") == "owner":
        ttk.Button(bar, text="Akun Pegawai", command=lambda: EmployeeManagementDialog(root, accounts, session)).pack(side="right", padx=(0, 8))
    ttk.Button(bar, text="Keluar", command=on_logout).pack(side="right")


__all__ = ["attach_post_login_features", "DiscountCheckoutProxy"]
