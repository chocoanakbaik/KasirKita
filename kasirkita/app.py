"""Application startup and local database location."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox

from kasirkita.infrastructure.backup import DatabaseBackupService
from kasirkita.infrastructure.database import DatabaseError, connect_database, initialize_database
from kasirkita.infrastructure.product_repository import ProductRepository
from kasirkita.services.checkout import CheckoutService
from kasirkita.services.product_catalog import ProductCatalog
from kasirkita.services.sales_history import SalesHistoryService
from kasirkita.services.sales_report import SalesReportService
from kasirkita.services.stock import StockService
from kasirkita.services.tax_settings import TaxSettingsService
from kasirkita.services.onboarding import OnboardingService
from kasirkita.ui.main_window import MainWindow
from kasirkita.ui.splash_screen import SplashScreen


def get_data_directory() -> Path:
    """Return a per-user writable directory without storing data beside the executable."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "KasirKita"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "KasirKita"
    return Path.home() / ".local" / "share" / "KasirKita"


def main() -> int:
    data_directory = get_data_directory()
    log_directory = data_directory / "logs"
    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            handlers=[
                logging.FileHandler(
                    str(log_directory / "kasirkita.log"),
                    encoding="utf-8",
                )
            ],
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        database_path = data_directory / "kasirkita.sqlite3"
        connection = connect_database(database_path)
        initialize_database(connection)
    except (OSError, DatabaseError) as exc:
        logging.exception("KasirKita startup failed")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "KasirKita tidak dapat dibuka",
            "Database lokal tidak dapat disiapkan. Periksa izin folder pengguna dan ruang disk.\n\n"
            + str(exc),
            parent=root,
        )
        root.destroy()
        return 1

    try:
        root = tk.Tk()
        catalog = ProductCatalog(ProductRepository(connection))
        checkout = CheckoutService(connection)
        sales_history = SalesHistoryService(connection)
        backup_service = DatabaseBackupService(connection, str(database_path))
        stock_service = StockService(connection)
        sales_report = SalesReportService(connection)
        tax_settings = TaxSettingsService(connection)
        onboarding = OnboardingService(connection)
        MainWindow(root, catalog, checkout, sales_history, backup_service, stock_service, sales_report, tax_settings, onboarding)
        root.withdraw()
        splash = SplashScreen(root)

        def show_main_window() -> None:
            if splash.winfo_exists():
                splash.destroy()
            root.deiconify()
            root.lift()

        root.after(1100, show_main_window)
        root.mainloop()
        return 0
    except Exception:
        logging.exception("KasirKita stopped unexpectedly")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
