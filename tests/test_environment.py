"""Tests for device detection fallbacks and adaptive desktop sizing."""
import unittest
from unittest.mock import Mock

from kasirkita.infrastructure.environment import configure_window_for_device, detect_device


class DeviceDetectionTests(unittest.TestCase):
    def test_detection_returns_expected_non_identifying_fields(self):
        info = detect_device()
        self.assertIn("os_name", info)
        self.assertIn("os_version", info)
        self.assertIn("architecture", info)
        self.assertIn("cpu_count", info)
        self.assertIn("profile", info)
        self.assertIn(info["profile"], ("hemat", "standar"))
        self.assertGreaterEqual(info["cpu_count"], 1)
        self.assertNotIn("username", info)
        self.assertNotIn("serial_number", info)

    def test_low_spec_profile_fits_small_screen(self):
        root = Mock()
        root.winfo_screenwidth.return_value = 1024
        root.winfo_screenheight.return_value = 600
        info = configure_window_for_device(root, {
            "profile": "hemat", "cpu_count": 2, "memory_gb": 4.0
        })
        self.assertEqual(info["profile"], "hemat")
        root.geometry.assert_called_once_with("984x530+20+35")
        root.minsize.assert_called_once_with(860, 530)

    def test_standard_profile_uses_available_screen_size(self):
        root = Mock()
        root.winfo_screenwidth.return_value = 1920
        root.winfo_screenheight.return_value = 1080
        root.tk.call.side_effect = [1.0, None]
        configure_window_for_device(root, {"profile": "standar"})
        root.geometry.assert_called_once_with("1120x720+400+180")


if __name__ == "__main__":
    unittest.main()
