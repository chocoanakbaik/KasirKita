"""Release metadata must stay consistent across source and installer."""
import re
import unittest
from pathlib import Path

from kasirkita import __version__


ROOT = Path(__file__).resolve().parents[1]


class VersionConsistencyTests(unittest.TestCase):
    def test_version_uses_semantic_numeric_triplet(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_installer_packages_buyer_guide_not_developer_readme(self):
        installer = (ROOT / "installer" / "KasirKita.iss").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
        self.assertIn('PANDUAN_PENGGUNA.md', installer)
        self.assertNotIn('README.md', installer)
        self.assertIn('Copy-Item docs/PANDUAN_PENGGUNA.md package/PANDUAN_PENGGUNA.md', workflow)
        self.assertNotIn('PANDUAN_PENGGUNA_ALPHA.md', workflow)

    def test_inno_setup_installer_matches_application_version(self):
        installer = (ROOT / "installer" / "KasirKita.iss").read_text(encoding="utf-8")
        match = re.search(r'^#define MyAppVersion "([^"]+)"$', installer, re.MULTILINE)
        self.assertIsNotNone(match, "Installer version define is missing")
        self.assertEqual(match.group(1), __version__)


if __name__ == "__main__":
    unittest.main()
