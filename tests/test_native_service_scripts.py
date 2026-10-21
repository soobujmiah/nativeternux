"""Host fixtures for the Termux runit and boot entry points."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOT_SCRIPT = ROOT / "scripts/termux-boot/00-ternuxx-services"
SERVICE_SCRIPT = ROOT / "scripts/termux-services/ternuxx-sshd/run"


def executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o700)


class NativeServiceScriptTests(unittest.TestCase):
    def test_boot_entry_starts_only_supervisor_and_reports_native_readiness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-script-") as temp:
            root = Path(temp)
            prefix = root / "prefix"
            home = root / "home"
            state = home / ".local/share/ternuxx"
            events = root / "events.log"
            executable(prefix / "etc/profile.d/start-services.sh", f"echo supervisor-started >> '{events}'\n")
            executable(prefix / "bin/sv", f"#!/bin/sh\necho \"$*\" >> '{events}'\necho 'run: ternuxx-sshd: (pid 123) 5s'\n")
            env = {**os.environ, "PREFIX": str(prefix), "HOME": str(home),
                   "TERMUX_VERSION": "fixture", "TERNUXX_STATE_DIR": str(state),
                   "PATH": f"{prefix / 'bin'}:{os.environ['PATH']}"}
            result = subprocess.run(["bash", str(BOOT_SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            log = (state / "continuity/boot-logs/ternuxx-services.log").read_text()
            self.assertIn("result=ready; provider=native_termux; proot_dependency=false", log)
            self.assertIn("supervisor-started", events.read_text())
            self.assertIn("status ternuxx-sshd", events.read_text())
            self.assertNotIn("proot", events.read_text().lower())
            self.assertEqual((state / "continuity/boot-logs/ternuxx-services.log").stat().st_mode & 0o777, 0o600)

    def test_boot_entry_uses_canonical_state_default_without_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-default-state-") as temp:
            root = Path(temp)
            prefix = root / "prefix"
            home = root / "home"
            state = home / ".local/share/ternuxx"
            events = root / "events.log"
            executable(prefix / "etc/profile.d/start-services.sh", f"echo supervisor-started >> '{events}'\n")
            executable(prefix / "bin/sv", f"#!/bin/sh\necho \"$*\" >> '{events}'\necho 'run: ternuxx-sshd: (pid 123) 5s'\n")
            env = {**os.environ, "PREFIX": str(prefix), "HOME": str(home),
                   "TERMUX_VERSION": "fixture", "PATH": f"{prefix / 'bin'}:{os.environ['PATH']}"}
            result = subprocess.run(["bash", str(BOOT_SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            log = state / "continuity/boot-logs/ternuxx-services.log"
            self.assertTrue(log.is_file())
            self.assertIn("result=ready; provider=native_termux; proot_dependency=false", log.read_text())

    def test_recovery_boot_source_uses_only_canonical_install_and_state_paths(self) -> None:
        source = (ROOT / "scripts/termux-boot/ternuxx-recovery").read_text(encoding="utf-8")
        self.assertIn('STATE_DIR="${TERNUXX_STATE_DIR:-$HOME/.local/share/ternuxx}"', source)
        self.assertIn('RECOVERY_MODULE="$PREFIX/lib/ternuxx/reboot_recovery.py"', source)

    def test_service_wrapper_owns_and_releases_its_persistent_lease(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-runit-script-") as temp:
            root = Path(temp)
            prefix = root / "prefix"
            home = root / "home"
            state = home / ".local/share/ternuxx"
            config = home / ".config/ternuxx/sshd_recovery.conf"
            config.parent.mkdir(parents=True)
            config.write_text("fixture\n")
            events = root / "events.log"
            executable(prefix / "bin/tx", f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{events}'\nprintf 'state=%s\\n' \"${{TERNUXX_STATE_DIR:-}}\" >> '{events}'\n")
            executable(prefix / "bin/sshd", f"#!/bin/sh\nif [ \"$1\" = -t ]; then exit 0; fi\necho daemon-started >> '{events}'\nexec sleep 60\n")
            (prefix / "bin/bash").symlink_to(shutil.which("bash"))
            env = {**os.environ, "PREFIX": str(prefix), "HOME": str(home),
                   "TERMUX_VERSION": "fixture", "TERNUXX_STATE_DIR": str(state)}
            proc = subprocess.Popen(["bash", str(SERVICE_SCRIPT)], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and (not events.exists() or "daemon-started" not in events.read_text()):
                    if proc.poll() is not None:
                        self.fail(f"service exited early: {proc.communicate()}")
                    time.sleep(0.05)
                self.assertTrue(events.exists())
                self.assertIn("wakelock acquire native.sshd --persistent", events.read_text())
                self.assertIn(f"state={state}", events.read_text())
                self.assertIn("daemon-started", events.read_text())
                service_log = (state / "log/sshd-runit.log").read_text()
                self.assertIn("wrapper-started-at=", service_log)
                self.assertIn("wakelock-acquire=ok-at-", service_log)
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
                proc.communicate(timeout=1)
                self.assertIn("wakelock release native.sshd --persistent", events.read_text())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
