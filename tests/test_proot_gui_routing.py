from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProotGuiRoutingTests(unittest.TestCase):
    def test_status_reports_stopped_when_no_managed_session_exists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-proot-status-") as temp:
            home = Path(temp)
            env = {**os.environ, "HOME": str(home), "PREFIX": str(home / "prefix"),
                   "TMPDIR": str(home / "tmp")}
            result = subprocess.run(["bash", str(ROOT / "scripts/proot-gui0.sh"), "status"],
                                    capture_output=True, text=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Standalone Debian GUI: stopped; target display :0", result.stdout)
            self.assertIn("Nested display :2 socket is absent.", result.stdout)

    def test_nested_route_starts_xfce_session_on_existing_xephyr_server(self) -> None:
        script = (ROOT / "scripts/proot-gui0.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/Xephyr :2 -glamor_gles2 -screen", script)
        self.assertIn("DISPLAY=:2 dbus-launch --exit-with-session xfce4-session &", script)
        self.assertNotIn("DISPLAY=:2 dbus-launch --exit-with-session startxfce4 &", script)

    def test_nested_route_starts_xfce_session_on_existing_xephyr_server(self) -> None:
        script = (ROOT / "scripts/proot-gui0.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/Xephyr :2 -glamor_gles2 -screen", script)
        self.assertIn("DISPLAY=:2 dbus-launch --exit-with-session xfce4-session &", script)
        self.assertNotIn("DISPLAY=:2 dbus-launch --exit-with-session startxfce4 &", script)

    def test_invalid_mode_is_rejected_before_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-shared-gui-") as temp:
            home = Path(temp)
            env = {**os.environ, "HOME": str(home), "PREFIX": str(home / "prefix"),
                   "TMPDIR": str(home / "tmp")}
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/proot-gui0.sh"), "start", "--mode", "unsupported"],
                capture_output=True, text=True, env=env, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--mode must be auto, standalone, or nested", result.stderr)
            self.assertFalse((home / ".local/share/ternuxx").exists())

if __name__ == "__main__":
    unittest.main()
