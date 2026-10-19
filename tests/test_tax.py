"""Tests for exact tax calculations and optional tax settings."""
import unittest

from kasirkita.domain.tax import TaxCalculationError, calculate_tax
from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.tax_settings import TaxSettingsError, TaxSettingsService


class TaxCalculationTests(unittest.TestCase):
    def test_tax_disabled_leaves_total_unchanged(self):
        result = calculate_tax(
            10001,
            {"enabled": False, "rate_basis_points": 1100, "mode": "exclusive"},
        )
        self.assertEqual(result, {
            "subtotal_rupiah": 10001,
            "tax_rupiah": 0,
            "total_rupiah": 10001,
        })

    def test_exclusive_tax_uses_integer_half_up_rounding(self):
        result = calculate_tax(
            10001,
            {"enabled": True, "rate_basis_points": 1100, "mode": "exclusive"},
        )
        self.assertEqual(result["subtotal_rupiah"], 10001)
        self.assertEqual(result["tax_rupiah"], 1100)
        self.assertEqual(result["total_rupiah"], 11101)

    def test_inclusive_tax_extracts_tax_from_gross_total(self):
        result = calculate_tax(
            11000,
            {"enabled": True, "rate_basis_points": 1000, "mode": "inclusive"},
        )
        self.assertEqual(result["total_rupiah"], 11000)
        self.assertEqual(result["tax_rupiah"], 1000)
        self.assertEqual(result["subtotal_rupiah"], 10000)

    def test_zero_rate_does_not_change_total(self):
        result = calculate_tax(
            1000,
            {"enabled": True, "rate_basis_points": 0, "mode": "inclusive"},
        )
        self.assertEqual(result["tax_rupiah"], 0)
        self.assertEqual(result["total_rupiah"], 1000)

    def test_invalid_amount_and_configuration_are_rejected(self):
        for amount in [-1, True, 1.5, 9_000_000_000_000_001]:
            with self.subTest(amount=amount):
                with self.assertRaises(TaxCalculationError):
                    calculate_tax(
                        amount,
                        {"enabled": False, "rate_basis_points": 0, "mode": "exclusive"},
                    )
        with self.assertRaises(TaxCalculationError):
            calculate_tax(1000, {"enabled": "yes", "rate_basis_points": 1000, "mode": "exclusive"})


class TaxSettingsTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.settings = TaxSettingsService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_tax_is_disabled_by_default(self):
        config = self.settings.get_config()
        self.assertFalse(config["enabled"])
        self.assertEqual(config["rate_basis_points"], 0)
        self.assertEqual(config["mode"], "exclusive")

    def test_save_and_reload_tax_settings(self):
        saved = self.settings.save_config(True, 1100, "exclusive", "PPN")
        self.assertTrue(saved["enabled"])
        self.assertEqual(saved["rate_basis_points"], 1100)
        self.assertEqual(self.settings.get_config(), saved)

    def test_invalid_settings_are_rejected(self):
        invalid = [
            (True, 0, "exclusive", "PPN"),
            (True, 10001, "exclusive", "PPN"),
            (1, 1100, "exclusive", "PPN"),
            (False, 100, "wrong", "PPN"),
            (False, 100, "exclusive", " " ),
            (False, 100, "exclusive", "X" * 41),
        ]
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(TaxSettingsError):
                    self.settings.save_config(*args)


if __name__ == "__main__":
    unittest.main()
