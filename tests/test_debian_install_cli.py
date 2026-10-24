import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "tx"


class RetiredGuestInstallCLITests(unittest.TestCase):
    def test_guest_install_routes_are_rejected_before_package_probes(self):
        env = {
            **os.environ,
            "TERMUX_VERSION": "fixture",
            "PREFIX": "/tmp/ternuxx-no-guest-install",
            "HOME": "/tmp/ternuxx-no-guest-install-home",
        }
        for guest in ("debian", "proot"):
            with self.subTest(guest=guest):
                result = subprocess.run(
                    ["bash", str(CLI), "install", guest, "preview"],
                    env=env, capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("Unknown install option", result.stderr)
                self.assertNotIn("proot_setup_present", result.stderr)


if __name__ == "__main__":
    unittest.main()
