"""Compact customer/supplier maintenance panel."""
import tkinter as tk
from tkinter import messagebox, ttk

from kasirkita.services.contacts import ContactService, ContactValidationError


class ContactEditor(tk.Toplevel):
    def __init__(self, parent, title, record=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        record = record or {}
        self.fields = {}
        for row, (key, label) in enumerate((
            ("name", "Nama *"), ("phone", "Nomor telepon"), ("email", "Email"),
            ("address", "Alamat"), ("note", "Catatan"),
        )):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(frame, width=38)
            entry.insert(0, str(record.get(key, "")))
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            self.fields[key] = entry
        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Simpan", command=self.submit).pack(side="right", padx=(0, 8))
        self.fields["name"].focus_set()
        self.grab_set()

    def submit(self):
        self.result = {key: entry.get() for key, entry in self.fields.items()}
        if not self.result["name"].strip():
            messagebox.showerror("Data belum lengkap", "Nama wajib diisi.", parent=self)
            return
        self.destroy()


class ContactsPanel(ttk.Frame):
    def __init__(self, parent, service: ContactService):
        super().__init__(parent, padding=10)
        self.service = service
        self.tables = {}
        self.search_vars = {}
        self._build()

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        for kind, title in (("customers", "Pelanggan"), ("suppliers", "Supplier")):
            tab = ttk.Frame(notebook, padding=10)
            tab.rowconfigure(1, weight=1)
            tab.columnconfigure(0, weight=1)
            notebook.add(tab, text=title)
            toolbar = ttk.Frame(tab)
            toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            search = tk.StringVar()
            self.search_vars[kind] = search
            entry = ttk.Entry(toolbar, textvariable=search, width=28)
            entry.pack(side="left")
            entry.bind("<KeyRelease>", lambda _e, k=kind: self.refresh(k))
            ttk.Button(toolbar, text="Cari", command=lambda k=kind: self.refresh(k)).pack(side="left", padx=5)
            ttk.Button(toolbar, text="Tambah", command=lambda k=kind: self.add(k)).pack(side="right")
            ttk.Button(toolbar, text="Edit", command=lambda k=kind: self.edit(k)).pack(side="right", padx=5)
            ttk.Button(toolbar, text="Aktif/nonaktif", command=lambda k=kind: self.toggle(k)).pack(side="right", padx=5)
            tree = ttk.Treeview(tab, columns=("name", "phone", "email", "address"), show="headings", selectmode="browse")
            for key, label, width in (("name", "Nama", 220), ("phone", "Telepon", 130), ("email", "Email", 180), ("address", "Alamat", 260)):
                tree.heading(key, text=label)
                tree.column(key, width=width, anchor="w")
            tree.grid(row=1, column=0, sticky="nsew")
            scroll = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
            scroll.grid(row=1, column=1, sticky="ns")
            tree.configure(yscrollcommand=scroll.set)
            self.tables[kind] = tree
            self.refresh(kind)

    def _selected(self, kind):
        tree = self.tables[kind]
        selected = tree.selection()
        return int(selected[0]) if selected else None

    def _service_list(self, kind, query="", include_inactive=False):
        method = self.service.list_customers if kind == "customers" else self.service.list_suppliers
        return method(query, include_inactive)

    def refresh(self, kind):
        tree = self.tables[kind]
        tree.delete(*tree.get_children())
        for row in self._service_list(kind, self.search_vars[kind].get()):
            tree.insert("", "end", iid=str(row["id"]), values=(row["name"], row["phone"], row["email"], row["address"]))

    def add(self, kind):
        editor = ContactEditor(self, "Tambah " + ("pelanggan" if kind == "customers" else "supplier"))
        self.wait_window(editor)
        if not editor.result:
            return
        try:
            method = self.service.add_customer if kind == "customers" else self.service.add_supplier
            method(**editor.result)
        except ContactValidationError as exc:
            messagebox.showerror("Data tidak valid", str(exc), parent=self)
            return
        self.refresh(kind)

    def edit(self, kind):
        record_id = self._selected(kind)
        if record_id is None:
            messagebox.showinfo("Pilih data", "Pilih satu data untuk diedit.", parent=self)
            return
        rows = self._service_list(kind, "", True)
        record = next((row for row in rows if row["id"] == record_id), None)
        if not record:
            return
        editor = ContactEditor(self, "Edit data", record)
        self.wait_window(editor)
        if not editor.result:
            return
        try:
            method = self.service.update_customer if kind == "customers" else self.service.update_supplier
            method(record_id, **editor.result)
        except ContactValidationError as exc:
            messagebox.showerror("Data tidak valid", str(exc), parent=self)
            return
        self.refresh(kind)

    def toggle(self, kind):
        record_id = self._selected(kind)
        if record_id is None:
            messagebox.showinfo("Pilih data", "Pilih satu data untuk diaktifkan atau dinonaktifkan.", parent=self)
            return
        rows = self._service_list(kind, "", True)
        record = next((row for row in rows if row["id"] == record_id), None)
        if not record:
            return
        active = not bool(record["is_active"])
        if not messagebox.askyesno("Konfirmasi", "Ubah status data ini?", parent=self):
            return
        method = self.service.set_customer_active if kind == "customers" else self.service.set_supplier_active
        try:
            method(record_id, active)
        except ContactValidationError as exc:
            messagebox.showerror("Tidak dapat mengubah status", str(exc), parent=self)
            return
        self.refresh(kind)


__all__ = ["ContactsPanel"]
