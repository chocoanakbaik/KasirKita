"""Owner-only employee account administration."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from kasirkita.services.accounts import AccountService, AuthenticationError


class EmployeeManagementDialog(tk.Toplevel):
    def __init__(self, parent, accounts: AccountService, session):
        super().__init__(parent)
        self.title("Pengelolaan akun pegawai")
        self.geometry("640x420")
        self.minsize(520, 340)
        self.transient(parent)
        self.accounts, self.session = accounts, session
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        frame = ttk.Frame(self, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=("name", "status", "created"), show="headings", selectmode="browse")
        for key, label, width in (("name", "Nama pegawai", 250), ("status", "Status", 100), ("created", "Dibuat", 180)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        actions = ttk.Frame(frame)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Tambah pegawai", command=self.add).pack(side="left")
        ttk.Button(actions, text="Atur ulang kata sandi", command=self.reset_password).pack(side="left", padx=6)
        ttk.Button(actions, text="Aktif/nonaktif", command=self.toggle).pack(side="left")
        ttk.Button(actions, text="Tutup", command=self.destroy).pack(side="right")
        self.refresh()
        self.grab_set()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.accounts.list_employees(self.session):
            self.tree.insert("", "end", iid=str(row["id"]), values=(
                row["display_name"], "Aktif" if row["is_active"] else "Nonaktif", row["created_at"]
            ))

    def selected_id(self):
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def add(self):
        dialog = tk.Toplevel(self)
        dialog.title("Tambah pegawai")
        dialog.transient(self)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        fields = []
        for row, label, secret in (
            (0, "Nama pegawai", False), (2, "ID login (4–32 karakter)", False),
            (4, "Kata sandi sementara (minimal 10 karakter)", True),
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(frame, show="*" if secret else "", width=36)
            entry.grid(row=row + 1, column=0, sticky="ew", pady=(3, 8))
            fields.append(entry)

        def submit():
            try:
                self.accounts.create_employee(self.session, fields[0].get(), fields[1].get(), fields[2].get())
            except AuthenticationError as exc:
                messagebox.showerror("Akun tidak dibuat", str(exc), parent=dialog)
                return
            dialog.destroy()
            self.refresh()

        ttk.Button(frame, text="Buat akun", command=submit).grid(row=6, column=0, sticky="e")
        fields[0].focus_set()

    def reset_password(self):
        employee_id = self.selected_id()
        if employee_id is None:
            messagebox.showinfo("Pilih pegawai", "Pilih akun pegawai terlebih dahulu.", parent=self)
            return
        password = simpledialog.askstring("Atur ulang kata sandi", "Kata sandi baru (minimal 10 karakter):", show="*", parent=self)
        if password is None:
            return
        try:
            self.accounts.reset_employee_password(self.session, employee_id, password)
        except AuthenticationError as exc:
            messagebox.showerror("Gagal", str(exc), parent=self)
            return
        messagebox.showinfo("Selesai", "Kata sandi pegawai berhasil diatur ulang.", parent=self)

    def toggle(self):
        employee_id = self.selected_id()
        if employee_id is None:
            messagebox.showinfo("Pilih pegawai", "Pilih akun pegawai terlebih dahulu.", parent=self)
            return
        row = next((item for item in self.accounts.list_employees(self.session) if item["id"] == employee_id), None)
        if not row:
            return
        active = not bool(row["is_active"])
        if not messagebox.askyesno("Konfirmasi", "Ubah status akun pegawai?", parent=self):
            return
        try:
            self.accounts.set_employee_active(self.session, employee_id, active)
        except AuthenticationError as exc:
            messagebox.showerror("Gagal", str(exc), parent=self)
            return
        self.refresh()


__all__ = ["EmployeeManagementDialog"]
