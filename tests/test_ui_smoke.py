"""Windows desktop smoke test for the initial Tkinter UI."""
import os
import tkinter as tk
import unittest

from kasirkita.infrastructure.backup import DatabaseBackupService
from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.infrastructure.product_repository import ProductRepository
from kasirkita.services.checkout import CheckoutService
from kasirkita.services.product_catalog import ProductCatalog
from kasirkita.services.sales_history import SalesHistoryService
from kasirkita.services.sales_report import SalesReportService
from kasirkita.services.stock import StockService
from kasirkita.services.tax_settings import TaxSettingsService
from kasirkita.services.onboarding import OnboardingService
from kasirkita.ui.main_window import CHOCO_AI_URL, MainWindow


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "A desktop display is required.")
class DesktopUISmokeTests(unittest.TestCase):
    def test_main_window_builds_all_tabs(self):
        connection = connect_database(":memory:")
        initialize_database(connection)
        root = tk.Tk()
        root.withdraw()
        try:
            app = MainWindow(
                root,
                ProductCatalog(ProductRepository(connection)),
                CheckoutService(connection),
                SalesHistoryService(connection),
                DatabaseBackupService(connection),
                StockService(connection),
                SalesReportService(connection),
                TaxSettingsService(connection),
                OnboardingService(connection),
            )
            self.assertEqual(len(app.tabs.tabs()), 5)
            self.assertEqual(app.tabs.tab(app.tabs.tabs()[0], "text"), "Kasir")
            self.assertEqual(app.tabs.tab(app.tabs.tabs()[4], "text"), "Pengaturan")
            self.assertEqual(app.support_link.cget("text"), "Klik di sini untuk melaporkan")
            self.assertEqual(CHOCO_AI_URL, "https://choco-ai-platform.netlify.app/")
            self.assertTrue(app.onboarding is not None)
            root.update_idletasks()
        finally:
            root.destroy()
            connection.close()


if __name__ == "__main__":
    unittest.main()
