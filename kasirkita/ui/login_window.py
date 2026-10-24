"""Local role-specific login and owner bootstrap screens."""
import tkinter as tk
from tkinter import messagebox, ttk

from kasirkita.services.accounts import AccountService, AuthenticationError


class LoginWindow:
    def __init__(self, root, accounts, on_authenticated):
        self.root, self.accounts, self.on_authenticated = root, accounts, on_authenticated
        self.window = tk.Toplevel(root)
        self.window.title("Masuk ke KasirKita")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self.window.bind("<Escape>", lambda _e: self.home())
        self.render_home()
        self.window.update_idletasks()
        width, height = 430, 390
        x = max(0, (self.window.winfo_screenwidth() - width) // 2)
        y = max(0, (self.window.winfo_screenheight() - height) // 2)
        self.window.geometry("{}x{}+{}+{}".format(width, height, x, y))
        self.window.minsize(400, 340)
        self.window.transient(root)
        self.window.grab_set()
        self.window.lift()

    def clear(self):
        for child in self.window.winfo_children():
            child.destroy()
        frame = ttk.Frame(self.window, padding=26)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="KasirKita", font=("Segoe UI", 22, "bold")).grid(row=0, column=0, sticky="w")
        return frame

    def heading(self, frame, title, subtitle):
        ttk.Label(frame, text=title, font=("Segoe UI", 13, "bold")).grid(row=1, column=0, sticky="w", pady=(14, 3))
        ttk.Label(frame, text=subtitle, wraplength=350).grid(row=2, column=0, sticky="w", pady=(0, 16))

    def render_home(self):
        frame = self.clear()
        self.heading(frame, "Masuk", "Pilih jenis akun untuk melanjutkan.")
        ttk.Button(frame, text="Login sebagai Pemilik", command=lambda: self.login_form("owner")).grid(row=3, column=0, sticky="ew", pady=5, ipady=5)
        ttk.Button(frame, text="Login sebagai Pegawai", command=lambda: self.login_form("employee")).grid(row=4, column=0, sticky="ew", pady=5, ipady=5)
        if not self.accounts.owner_exists():
            ttk.Button(frame, text="Daftar", command=self.register_form).grid(row=5, column=0, sticky="ew", pady=(14, 4), ipady=4)
        else:
            ttk.Label(frame, text="Akun dan data disimpan lokal di komputer ini.", foreground="#64748b").grid(row=5, column=0, sticky="w", pady=(16, 0))

    def login_form(self, role):
        frame = self.clear()
        title = "Login sebagai Pemilik" if role == "owner" else "Login sebagai Pegawai"
        self.heading(frame, title, "Masukkan ID login 4–32 karakter dan kata sandi.")
        ttk.Label(frame, text="ID login").grid(row=3, column=0, sticky="w")
        login_id = ttk.Entry(frame)
        login_id.grid(row=4, column=0, sticky="ew", pady=(3, 10))
        ttk.Label(frame, text="Kata sandi").grid(row=5, column=0, sticky="w")
        password = ttk.Entry(frame, show="*")
        password.grid(row=6, column=0, sticky="ew", pady=(3, 12))
        actions = ttk.Frame(frame)
        actions.grid(row=7, column=0, sticky="ew")
        ttk.Button(actions, text="Kembali", command=self.home).pack(side="left")
        ttk.Button(actions, text="Masuk", command=lambda: self.submit_login(role, login_id.get(), password.get())).pack(side="right")
        if role == "owner":
            ttk.Button(frame, text="Lupa kata sandi", command=self.recover).grid(row=8, column=0, sticky="w", pady=(12, 0))
        self.window.bind("<Return>", lambda _e: self.submit_login(role, login_id.get(), password.get()))
        login_id.focus_set()

    def submit_login(self, role, login_id, password):
        try:
            session = self.accounts.authenticate(login_id, password, role)
        except AuthenticationError as exc:
            messagebox.showerror("Login gagal", str(exc), parent=self.window)
            return
        self.window.grab_release()
        self.window.destroy()
        self.on_authenticated(session)

    def register_form(self):
        frame = self.clear()
        self.heading(frame, "Daftar pemilik", "Hanya tersedia sebelum akun pemilik pertama dibuat.")
        entries = []
        for row, label, secret in (
            (3, "Nama pemilik", False),
            (5, "ID login (4–32 karakter)", False),
            (7, "Kata sandi (minimal 10 karakter)", True),
            (9, "Ulangi kata sandi", True),
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(frame, show="*" if secret else "")
            entry.grid(row=row + 1, column=0, sticky="ew", pady=(2, 6))
            entries.append(entry)
        actions = ttk.Frame(frame)
        actions.grid(row=11, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(actions, text="Kembali", command=self.home).pack(side="left")
        ttk.Button(actions, text="Buat akun", command=lambda: self.submit_registration(entries)).pack(side="right")
        entries[0].focus_set()

    def submit_registration(self, entries):
        name, login_id, password, confirm = [entry.get() for entry in entries]
        if password != confirm:
            messagebox.showerror("Pendaftaran gagal", "Kedua kata sandi tidak sama.", parent=self.window)
            return
        try:
            account = self.accounts.register_first_owner(name, login_id, password)
        except AuthenticationError as exc:
            messagebox.showerror("Pendaftaran gagal", str(exc), parent=self.window)
            return
        messagebox.showinfo("Simpan kode pemulihan", "Kode pemulihan satu kali untuk akun pemilik:\n\n{}\n\nSimpan di tempat aman di luar komputer. Kode ini tidak akan ditampilkan lagi.".format(account["recovery_code"]), parent=self.window)
        session = {key: account[key] for key in ("id", "display_name", "role")}
        self.window.grab_release()
        self.window.destroy()
        self.on_authenticated(session)

    def recover(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Pemulihan akun pemilik")
        dialog.transient(self.window)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        fields = []
        for row, label, secret in (
            (0, "ID login (4–32 karakter)", False),
            (2, "Kode pemulihan", False),
            (4, "Kata sandi baru", True),
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(frame, show="*" if secret else "")
            entry.grid(row=row + 1, column=0, sticky="ew", pady=(3, 7))
            fields.append(entry)

        def submit():
            try:
                self.accounts.recover_owner_password(fields[0].get(), fields[1].get(), fields[2].get())
            except AuthenticationError as exc:
                messagebox.showerror("Pemulihan gagal", str(exc), parent=dialog)
                return
            messagebox.showinfo("Selesai", "Kata sandi berhasil diatur ulang.", parent=dialog)
            dialog.destroy()
            self.login_form("owner")

        ttk.Button(frame, text="Atur ulang kata sandi", command=submit).grid(row=6, column=0, sticky="e", pady=(8, 0))
        fields[0].focus_set()

    def home(self):
        self.window.unbind("<Return>")
        self.render_home()

    def _close(self):
        self.window.grab_release()
        self.window.destroy()
        self.root.destroy()


__all__ = ["LoginWindow"]
