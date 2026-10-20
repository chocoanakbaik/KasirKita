"""Attach new local-account features without coupling them to the legacy POS widgets."""
import tkinter as tk
from tkinter import messagebox, ttk

from kasirkita.services.accounts import AccountService
from kasirkita.services.contacts import ContactService
from kasirkita.ui.contacts_panel import ContactsPanel
from kasirkita.ui.employee_management import EmployeeManagementDialog


def attach_post_login_features(main_window, root, contacts, accounts, session, on_logout):
    """Add contacts and role-aware account controls after the existing POS UI loads."""
    tab = ttk.Frame(main_window.tabs, padding=8)
    main_window.tabs.add(tab, text="Pelanggan & Supplier")
    ContactsPanel(tab, contacts).pack(fill="both", expand=True)

    bar = ttk.Frame(root, padding=(10, 5))
    bar.pack(side="bottom", fill="x")
    role_label = "Pemilik" if session.get("role") == "owner" else "Pegawai"
    ttk.Label(bar, text="Login: {} ({})".format(session.get("display_name", ""), role_label)).pack(side="left")

    if session.get("role") == "owner":
        ttk.Button(
            bar, text="Akun Pegawai",
            command=lambda: EmployeeManagementDialog(root, accounts, session)
        ).pack(side="right", padx=(0, 8))
    ttk.Button(bar, text="Keluar", command=on_logout).pack(side="right")


__all__ = ["attach_post_login_features"]
