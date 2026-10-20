from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProotGuiRoutingTests(unittest.TestCase):
    def test_status_labels_the_state_as_recorded_not_live_health(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-proot-status-") as temp:
            home = Path(temp)
            state = home / ".local/share/ternuxx/proot-display0"
            state.mkdir(parents=True)
            (state / "session.json").write_text('{"status":"running","display":":0","android_user":0}', encoding="utf-8")
            env = {**os.environ, "HOME": str(home), "PREFIX": str(home / "prefix"),
                   "TMPDIR": str(home / "tmp")}
            result = subprocess.run(["bash", str(ROOT / "scripts/proot-gui0.sh"), "status"],
                                    capture_output=True, text=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Recorded Ternuxx PRoot GUI state=running", result.stdout)
            self.assertIn("live process identity unverified", result.stdout)

    def test_full_desktop_start_refuses_separate_display_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-shared-gui-") as temp:
            home = Path(temp)
            env = {**os.environ, "HOME": str(home), "PREFIX": str(home / "prefix"),
                   "TMPDIR": str(home / "tmp")}
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/proot-gui0.sh"), "start"],
                capture_output=True, text=True, env=env, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Separate PRoot display :0 startup is disabled", result.stderr)
            self.assertFalse((home / ".local/share/ternuxx/proot-display0").exists())


if __name__ == "__main__":
    unittest.main()
