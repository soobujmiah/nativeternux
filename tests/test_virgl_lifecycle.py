"""Native fixture tests for the identity-checked VirGL service."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import virgl_lifecycle  # noqa: E402


SERVER = """#!/usr/bin/env python3
import os, socket, sys
path=sys.argv[sys.argv.index('--socket-path')+1]
server=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(path)
os.chmod(path, 0o600)
server.listen(8)
while True:
    conn, _ = server.accept()
    conn.close()
"""


class VirglLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-virgl-")
        root = Path(self.temp.name)
        self.prefix = root / "prefix"
        self.home = root / "home"
        self.state = self.home / ".local/share/ternuxx"
        self.server = self.prefix / "bin/virgl_test_server_android"
        self.server.parent.mkdir(parents=True)
        self.home.mkdir()
        self.server.write_text(SERVER, encoding="utf-8")
        self.server.chmod(0o700)
        self.native = patch.object(virgl_lifecycle, "_require_native", return_value=None)
        self.native.start()
        self.env = patch.dict(os.environ, {
            "PREFIX": str(self.prefix), "HOME": str(self.home),
            "TERNUXX_STATE_DIR": str(self.state), "TERMUX_VERSION": "fixture",
        })
        self.env.start()
        self.paths = virgl_lifecycle._paths(":1")
        self.pids: set[int] = set()
        self.children: list[subprocess.Popen] = []
        self.original_popen = virgl_lifecycle.subprocess.Popen
        self.popen_patch = patch.object(
            virgl_lifecycle.subprocess, "Popen", side_effect=self._capture_child
        )
        self.popen_patch.start()
        # Patch _proc to return consistent UID in environments where
        # os.getuid() differs from /proc (e.g., proot virtualizes UID to 0)
        self._original_proc = virgl_lifecycle._proc
        def _patched_proc(pid):
            result = self._original_proc(pid)
            if result is not None:
                result["uid"] = os.getuid()
            return result
        self.proc_patch = patch.object(virgl_lifecycle, "_proc", side_effect=_patched_proc)
        self.proc_patch.start()

    def _capture_child(self, *args, **kwargs):
        child = self.original_popen(*args, **kwargs)
        self.children.append(child)
        return child

    def tearDown(self) -> None:
        for child in self.children:
            if child.poll() is None:
                try:
                    child.terminate()
                except ProcessLookupError:
                    pass
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)
        self.popen_patch.stop()
        self.proc_patch.stop()
        self.env.stop()
        self.native.stop()
        self.temp.cleanup()

    def start_server(self):
        result = virgl_lifecycle.start(":1")
        record = virgl_lifecycle._record_read(self.paths["record"])
        self.assertIsNotNone(record)
        self.pids.add(record["pid"])
        return result, record

    def test_start_status_and_stop_only_the_owned_idle_server(self):
        result, record = self.start_server()
        self.assertEqual((result["owner"], result["state"], result["changed"]),
                         ("ternuxx", "running", True))
        self.assertEqual(virgl_lifecycle.status(":1")["identity"], "matched")
        self.assertEqual(virgl_lifecycle.start(":1")["changed"], False)
        self.assertEqual(Path(record["socket"]).stat().st_mode & 0o777, 0o600)
        with patch.object(virgl_lifecycle, "_matches_lsof", return_value=True):
            stopped = virgl_lifecycle.stop(":1")
        self.assertEqual((stopped["state"], stopped["changed"]), ("stopped", True))
        self.assertFalse(Path(record["socket"]).exists())

    def test_status_reports_verified_idle_active_and_unknown_client_visibility(self):
        _, record = self.start_server()
        with patch.object(virgl_lifecycle, "_lsof_socket_users", return_value={record["pid"]}):
            idle = virgl_lifecycle.status(":1")
        self.assertEqual(idle["client_visibility"], "verified_idle")
        self.assertEqual(idle["client_pids"], [])
        self.assertTrue(idle["stop_allowed"])
        with patch.object(virgl_lifecycle, "_lsof_socket_users",
                          return_value={record["pid"], 4567}):
            active = virgl_lifecycle.status(":1")
        self.assertEqual(active["client_visibility"], "active_clients")
        self.assertEqual(active["client_pids"], [4567])
        self.assertFalse(active["stop_allowed"])
        with patch.object(virgl_lifecycle, "_lsof_socket_users",
                          side_effect=virgl_lifecycle.VirglError("Native process visibility is incomplete")):
            unknown = virgl_lifecycle.status(":1")
        self.assertEqual(unknown["client_visibility"], "unknown")
        self.assertIsNone(unknown["client_pids"])
        self.assertFalse(unknown["stop_allowed"])
        self.assertIn("incomplete", unknown["stop_block_reason"])

    def test_cli_status_is_human_readable_by_default_and_json_when_requested(self):
        snapshot = {"owner": "ternuxx", "state": "running", "display": ":1",
                    "identity": "matched", "client_visibility": "unknown",
                    "client_pids": None, "stop_allowed": False,
                    "stop_block_reason": "cannot map socket owners", "read_only": True}
        with patch.object(virgl_lifecycle, "status", return_value=snapshot):
            human = StringIO()
            with redirect_stdout(human):
                self.assertEqual(virgl_lifecycle.main(["status", "--display", ":1"]), 0)
            self.assertIn("VirGL on :1: Running", human.getvalue())
            self.assertIn("Clients: unknown", human.getvalue())
            self.assertIn("Safe to stop: no", human.getvalue())
            machine = StringIO()
            with redirect_stdout(machine):
                self.assertEqual(virgl_lifecycle.main(["status", "--json", "--display", ":1"]), 0)
            self.assertEqual(json.loads(machine.getvalue())["client_visibility"], "unknown")

    def test_stop_refuses_when_android_lsof_cannot_map_socket_or_has_incomplete_visibility(self):
        # rc=1 with empty stdout and NO socket-specific stderr = no consumers = idle (returns empty set)
        result = subprocess.CompletedProcess(["lsof"], 1, "", "")
        with patch.object(virgl_lifecycle.shutil, "which", return_value="/bin/lsof"), \
             patch.object(virgl_lifecycle.subprocess, "run", return_value=result):
            pids = virgl_lifecycle._lsof_socket_users(self.paths)
        self.assertEqual(pids, set())
        # rc=1 with empty stdout and socket-specific error = cannot map
        sock_err = subprocess.CompletedProcess(["lsof"], 1, "",
                                               "lsof: status error on /tmp/test.sock: No such file\n")
        paths_with_sock = {**self.paths, "socket": Path("/tmp/test.sock")}
        with patch.object(virgl_lifecycle.shutil, "which", return_value="/bin/lsof"), \
             patch.object(virgl_lifecycle.subprocess, "run", return_value=sock_err):
            with self.assertRaisesRegex(virgl_lifecycle.VirglError, "could not map this Unix socket"):
                virgl_lifecycle._lsof_socket_users(paths_with_sock)
        # rc=0 with socket-specific warning = visibility incomplete
        warning = subprocess.CompletedProcess(["lsof"], 0, "1234\n",
                                             "lsof: WARNING: permission denied on /tmp/test.sock\n")
        with patch.object(virgl_lifecycle.shutil, "which", return_value="/bin/lsof"), \
             patch.object(virgl_lifecycle.subprocess, "run", return_value=warning):
            with self.assertRaisesRegex(virgl_lifecycle.VirglError, "visibility is incomplete"):
                virgl_lifecycle._lsof_socket_users(paths_with_sock)

    def test_stop_refuses_unknown_or_active_clients_and_preserves_server(self):
        _, record = self.start_server()
        with patch.object(virgl_lifecycle, "_matches_lsof",
                          side_effect=virgl_lifecycle.VirglError("active or unverified clients")):
            with self.assertRaisesRegex(virgl_lifecycle.VirglError, "clients"):
                virgl_lifecycle.stop(":1")
        self.assertEqual(virgl_lifecycle.status(":1")["state"], "running")
        self.assertTrue(Path(record["socket"]).exists())
        with patch.object(virgl_lifecycle, "_matches_lsof", return_value=True):
            virgl_lifecycle.stop(":1")

    def test_start_timeout_stops_only_the_exact_child_and_leaves_no_socket(self):
        self.server.write_text("#!/usr/bin/env python3\nimport time\nwhile True: time.sleep(1)\n", encoding="utf-8")
        self.server.chmod(0o700)
        with patch.object(virgl_lifecycle, "START_TIMEOUT", 0.15):
            with self.assertRaisesRegex(virgl_lifecycle.VirglError, "owned process was stopped"):
                virgl_lifecycle.start(":1")
        record = virgl_lifecycle._record_read(self.paths["record"])
        self.assertEqual(record["status"], "failed")
        self.assertIsNone(virgl_lifecycle._proc(record["pid"]))
        self.assertFalse(Path(record["socket"]).exists())

    def test_unknown_socket_is_never_removed_or_adopted(self):
        runtime = self.paths["runtime"]
        runtime.mkdir(parents=True, mode=0o700)
        socket_path = self.paths["socket"]
        socket_path.write_text("owner data", encoding="utf-8")
        with self.assertRaisesRegex(virgl_lifecycle.VirglError, "without a matching"):
            virgl_lifecycle.start(":1")
        self.assertEqual(socket_path.read_text(encoding="utf-8"), "owner data")

    def test_stale_record_reconciles_only_its_recorded_socket(self):
        _, record = self.start_server()
        os.kill(record["pid"], signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and virgl_lifecycle._proc(record["pid"]) is not None:
            time.sleep(0.05)
        self.assertIsNone(virgl_lifecycle._proc(record["pid"]))
        restarted, fresh = self.start_server()
        self.assertTrue(restarted["changed"])
        self.assertNotEqual(record["socket_inode"], 0)
        self.assertEqual(fresh["status"], "running")
        with patch.object(virgl_lifecycle, "_matches_lsof", return_value=True):
            virgl_lifecycle.stop(":1")

    def test_mismatched_record_display_cannot_manage_live_server(self):
        _, record = self.start_server()
        record["display"] = ":2"
        virgl_lifecycle._record_write(self.paths["record"], record)
        self.assertEqual(virgl_lifecycle.status(":1")["state"], "unsafe")
        with self.assertRaisesRegex(virgl_lifecycle.VirglError, "process identity is ambiguous"):
            virgl_lifecycle.stop(":1")
        self.assertIsNotNone(virgl_lifecycle._proc(record["pid"]))
        record["display"] = ":1"
        virgl_lifecycle._record_write(self.paths["record"], record)
        with patch.object(virgl_lifecycle, "_matches_lsof", return_value=True):
            virgl_lifecycle.stop(":1")

    def test_private_record_symlink_and_bad_display_fail_closed(self):
        with self.assertRaises(virgl_lifecycle.VirglError):
            virgl_lifecycle._paths(":1;touch")
        self.state.mkdir(parents=True, mode=0o700)
        gpu = self.state / "gpu"
        gpu.mkdir(mode=0o700)
        target = gpu / "target"
        target.write_text("{}", encoding="utf-8")
        record = gpu / "virgl-1.json"
        record.symlink_to(target)
        with self.assertRaises(virgl_lifecycle.VirglError):
            virgl_lifecycle.status(":1")


if __name__ == "__main__":
    unittest.main()
