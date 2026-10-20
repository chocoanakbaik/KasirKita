"""Lightweight, dependency-free startup splash for KasirKita."""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

logger = logging.getLogger("kasirkita.ui.splash")


class SplashScreen(tk.Toplevel):
    """Show a short branded startup screen without blocking the Tk event loop."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(background="#111827")
        width, height = 500, 270
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        outer = tk.Frame(self, background="#111827", padx=30, pady=26)
        outer.pack(fill="both", expand=True)
        self._logo = None
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "brand" / "kasirkita-logo.png"
        try:
            from PIL import Image, ImageTk
            if logo_path.is_file():
                with Image.open(logo_path) as source:
                    source.thumbnail((250, 62))
                    self._logo = ImageTk.PhotoImage(source.copy())
                tk.Label(outer, image=self._logo, background="#111827").pack(pady=(0, 8))
        except (ImportError, OSError, ValueError):
            logger.debug("KasirKita splash logo unavailable; using text branding.", exc_info=True)

        tk.Label(
            outer,
            text="KasirKita",
            font=("Segoe UI", 25, "bold"),
            foreground="#ffffff",
            background="#111827",
        ).pack()
        tk.Label(
            outer,
            text="BY THE CHOCO CORPORATION",
            font=("Segoe UI", 9, "bold"),
            foreground="#F59E0B",
            background="#111827",
        ).pack(pady=(4, 2))
        tk.Label(
            outer,
            text="KASIR DESKTOP  •  OFFLINE-FIRST",
            font=("Segoe UI", 9, "bold"),
            foreground="#22D3EE",
            background="#111827",
        ).pack(pady=(5, 18))
        self.status = tk.StringVar(value="Menyiapkan ruang kerja...")
        tk.Label(
            outer,
            textvariable=self.status,
            font=("Segoe UI", 9),
            foreground="#CBD5E1",
            background="#111827",
        ).pack()
        progress = ttk.Progressbar(outer, mode="indeterminate", length=300)
        progress.pack(pady=(12, 0))
        progress.start(12)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.transient(parent)
        self.lift()
