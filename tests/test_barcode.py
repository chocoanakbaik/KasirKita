"""Tests for offline barcode helpers."""
import unittest

from kasirkita.services.barcode import (
    BarcodeValidationError, make_internal_code, normalize_barcode,
)


class BarcodeTests(unittest.TestCase):
    def test_internal_codes_are_stable_and_zero_padded(self):
        self.assertEqual(make_internal_code(1), "KK-000001")
        self.assertEqual(make_internal_code(1234567), "KK-1234567")

    def test_rejects_invalid_sequences(self):
        for value in (0, -1, True, "1", None):
            with self.subTest(value=value):
                with self.assertRaises(BarcodeValidationError):
                    make_internal_code(value)

    def test_normalization_preserves_leading_zeroes(self):
        self.assertEqual(normalize_barcode(" 001234567890 "), "001234567890")

    def test_rejects_empty_control_characters_and_long_codes(self):
        for value in ("", "  ", "ABC\n123", "X" * 65, None):
            with self.subTest(value=value):
                with self.assertRaises(BarcodeValidationError):
                    normalize_barcode(value)


if __name__ == "__main__":
    unittest.main()
