"""Exercise native desktop ownership using isolated mock processes on Linux."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DesktopLifecycleFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-desktop-fixture-")
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.tmp = self.base / "tmp"
        (self.tmp / ".X11-unix").mkdir(parents=True)
        self.bin_dir = self.base / "mock-bin"
        self.bin_dir.mkdir()

        self.lib_dir = self.base / "lib"
        shutil.copytree(ROOT / "lib", self.lib_dir)
        supervisor = self.lib_dir / "desktop-supervisor.sh"
        lines = supervisor.read_text(encoding="utf-8").splitlines()
        lines[0] = "#!/usr/bin/env bash"  # Termux shebang is unavailable in Linux CI.
        supervisor.write_text("\n".join(lines) + "\n", encoding="utf-8")
        supervisor.chmod(0o755)

        self._write_executable(
            "termux-x11",
            """#!/usr/bin/env python3
import os, signal, socket, sys, time
display = sys.argv[1].lstrip(':')
path = os.path.join(os.environ['TMPDIR'], '.X11-unix', 'X' + display)
lock_path = os.path.join(os.environ['TMPDIR'], '.X' + display + '-lock')
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.bind(path)
sock.listen(1)
with open(lock_path, 'w', encoding='ascii') as lock:
    lock.write(str(os.getpid()).rjust(10) + '\\n')
def stop(_sig, _frame):
    sock.close()
    # Leave stale server artifacts so the supervisor's owner-checked cleanup
    # path is exercised by the fixture.
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
while True: time.sleep(0.1)
""",
        )
        self._write_executable(
            "dbus-launch",
            """#!/usr/bin/env python3
import os, sys
if len(sys.argv) < 3 or sys.argv[1] != "--exit-with-session":
    raise SystemExit(64)
os.execv(sys.argv[2], sys.argv[2:])
""",
        )
        self._write_executable(
            "xfce4-session",
            """#!/usr/bin/env python3
import time
while True:
    time.sleep(1)
""",
        )

        self.state = self.home / ".local/share/ternuxx-fixture"
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "TMPDIR": str(self.tmp),
                "TERMUX_VERSION": "fixture",
                "PREFIX": "/data/data/com.termux/files/usr",
                "NATIVERNUX_STATE_DIR": str(self.state),
                "NATIVERNUX_LIB_DIR": str(self.lib_dir),
                "PATH": f"{self.bin_dir}{os.pathsep}{os.environ['PATH']}",
            }
        )

    def tearDown(self) -> None:
        # Best-effort, scoped cleanup: ask only this fixture's session manager.
        if (self.state / "session.json").exists():
            subprocess.run(
                ["bash", str(ROOT / "bin/ternuxx"), "stop"],
                env=self.env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            )
        self.temp.cleanup()

    def _write_executable(self, name: str, content: str) -> None:
        path = self.bin_dir / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["bash", str(ROOT / "bin/ternuxx"), *args],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=12,
            check=False,
        )
        if result.returncode != 0:
            log = self.state / "desktop.log"
            if log.exists():
                result.stderr += "\nDESKTOP LOG:\n" + log.read_text(encoding="utf-8")
            state_file = self.state / "session.json"
            if state_file.exists():
                result.stderr += "\nSESSION STATE:\n" + state_file.read_text(encoding="utf-8")
        return result

    def _state(self) -> dict[str, object]:
        return json.loads((self.state / "session.json").read_text(encoding="utf-8"))

    def test_default_start_prefers_native_display_one(self) -> None:
        result = self._run("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._state()["display"], ":1")
        self.assertFalse((self.tmp / ".X0-lock").exists())
        self.assertFalse((self.tmp / ".X11-unix/X0").exists())

    def test_default_display_fallback_skips_proot_display_zero(self) -> None:
        lock_path = self.tmp / ".X1-lock"
        lock_path.write_text("external-owner\n", encoding="ascii")

        result = self._run("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._state()["display"], ":2")
        self.assertEqual(lock_path.read_text(encoding="ascii"), "external-owner\n")
        self.assertFalse((self.tmp / ".X0-lock").exists())
        self.assertFalse((self.tmp / ".X11-unix/X0").exists())

    def test_start_refuses_live_external_display_socket(self) -> None:
        import socket

        socket_path = self.tmp / ".X11-unix/X7"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(socket_path))
        listener.listen(1)
        self.addCleanup(listener.close)

        result = self._run("start", "--display", "7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has a socket or lock", result.stderr)
        self.assertTrue(socket_path.exists())
        self.assertFalse((self.state / "session.json").exists())
        self.assertFalse((self.state / "operations").exists())

    def test_start_refuses_display_lock_without_deleting_it(self) -> None:
        lock_path = self.tmp / ".X7-lock"
        lock_path.write_text("external-owner\n", encoding="ascii")

        result = self._run("start", "--display", "7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has a socket or lock", result.stderr)
        self.assertEqual(lock_path.read_text(encoding="ascii"), "external-owner\n")
        self.assertFalse((self.state / "session.json").exists())
        self.assertFalse((self.state / "operations").exists())

    def test_start_is_idempotent_and_stop_is_scoped(self) -> None:
        start = self._run("start", "--display", ":7")
        self.assertEqual(start.returncode, 0, start.stderr)
        first = self._state()
        self.assertEqual(first["status"], "running")
        self.assertEqual(first["display"], ":7")
        journal = self.state / "operations"
        records = sorted(journal.glob("*.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text())["status"], "complete")

        repeated = self._run("start", "--display", "7")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        second = self._state()
        self.assertEqual(second["supervisor"], first["supervisor"])
        self.assertEqual(second["x11"], first["x11"])
        self.assertEqual(second["desktop"], first["desktop"])
        self.assertEqual(len(list(journal.glob("*.json"))), 1)

        status = self._run("--json", "status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "running")

        stop = self._run("stop")
        self.assertEqual(stop.returncode, 0, stop.stderr)
        self.assertEqual(self._state()["status"], "stopped")
        records = sorted(journal.glob("*.json"))
        self.assertEqual(len(records), 2)
        self.assertEqual({json.loads(item.read_text())["status"] for item in records}, {"complete"})

        repeated_stop = self._run("stop")
        self.assertEqual(repeated_stop.returncode, 0, repeated_stop.stderr)
        self.assertEqual(self._state()["status"], "stopped")
        self.assertFalse((self.tmp / ".X11-unix/X7").exists())
        self.assertFalse((self.tmp / ".X7-lock").exists())
        self.assertEqual(len(list(journal.glob("*.json"))), 3)

    def test_restart_releases_stop_lock_and_is_repeatable(self) -> None:
        first_start = self._run("start", "--display", "7")
        self.assertEqual(first_start.returncode, 0, first_start.stderr)
        before = self._state()

        restarted = self._run("restart", "--display", "7")
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        after = self._state()
        self.assertEqual(after["status"], "running")
        self.assertNotEqual(after["supervisor"]["pid"], before["supervisor"]["pid"])
        self.assertFalse((self.state / ".session.lock").exists())

        repeated = self._run("restart", "--display", "7")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self._state()["status"], "running")
        self.assertFalse((self.state / ".session.lock").exists())

    def test_native_lifecycle_refuses_proot_environment(self) -> None:
        env = self.env.copy()
        env.pop("TERMUX_VERSION", None)
        env.pop("PREFIX", None)
        result = subprocess.run(
            ["bash", str(ROOT / "bin/ternuxx"), "start"],
            env=env,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires the native Termux shell", result.stderr)
        self.assertFalse(self.state.exists())

    def test_checkpoint_cli_is_native_only_and_records_without_proot(self) -> None:
        prepared = self._run("--json", "checkpoint", "prepare", "--test-id", "native-only", "--pending-test", "boot-check")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        result = json.loads(prepared.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"], "continuity.prepare")
        self.assertEqual(result["data"]["state"], "prepared")
        checkpoint_dir = self.state / "continuity/checkpoints"
        checkpoint = next(checkpoint_dir.glob("[0-9a-f]*.json"))
        record = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(record["test_id"], "native-only")
        self.assertFalse(record["task"]["automatic_resume"])
        existing_checkpoints = set(checkpoint_dir.glob("*.json"))

        env = self.env.copy()
        env.pop("TERMUX_VERSION", None)
        blocked = subprocess.run(
            ["bash", str(ROOT / "bin/ternuxx"), "checkpoint", "prepare", "--test-id", "blocked"],
            env=env, text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertEqual(set(checkpoint_dir.glob("*.json")), existing_checkpoints)

    def test_ssh_inspect_cli_emits_safe_json_in_native_context(self) -> None:
        result = self._run("--json", "ssh", "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["operation"], "ssh.inspect")
        report = envelope["data"]
        self.assertEqual(report["component"], "native_ssh_diagnostics")
        self.assertTrue(report["safety"]["read_only"])
        self.assertFalse(report["safety"]["credential_files_read"])
        self.assertEqual(report["checks"]["listener_daemon_correlation"], "unknown")
        self.assertFalse((self.state / "continuity").exists())

    def test_boot_wakelock_and_reboot_status_share_management_contract(self) -> None:
        for command in (("boot", "status"), ("wakelock", "status"), ("reboot", "status")):
            result = self._run("--json", *command)
            self.assertEqual(result.returncode, 0, result.stderr)
            response = json.loads(result.stdout)
            self.assertTrue(response["ok"], response)
            self.assertEqual(response["api_version"], 1)
        self.assertFalse((self.state / "continuity").exists())


if __name__ == "__main__":
    unittest.main()
