"""Pure formatting/input helpers used by the desktop interface."""
import unittest

from kasirkita.ui.main_window import format_rupiah, parse_rupiah_input


class UIHelperTests(unittest.TestCase):
    def test_format_rupiah_uses_indonesian_grouping(self):
        self.assertEqual(format_rupiah(0), "Rp 0")
        self.assertEqual(format_rupiah(25000), "Rp 25.000")
        self.assertEqual(format_rupiah(1_234_567), "Rp 1.234.567")

    def test_format_rejects_invalid_amount_types(self):
        for value in [-1, True, 1.5, "1000", None]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    format_rupiah(value)

    def test_parse_accepts_plain_and_correctly_grouped_integer_amounts(self):
        self.assertEqual(parse_rupiah_input("25000"), 25000)
        self.assertEqual(parse_rupiah_input("25.000"), 25000)
        self.assertEqual(parse_rupiah_input("1.234.567"), 1_234_567)
        self.assertEqual(parse_rupiah_input("  0  "), 0)

    def test_parse_rejects_malformed_or_fractional_amounts(self):
        for value in ["", "-100", "+100", "1.2", "25.00", "1..000", "25,000", "1 000"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_rupiah_input(value)

    def test_parse_rejects_amount_above_supported_limit(self):
        with self.assertRaises(ValueError):
            parse_rupiah_input("9000000000000001")


if __name__ == "__main__":
    unittest.main()
