"""Fixtures for the read-only Native Termux display readiness probe."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import native_display_probe as probe  # noqa: E402


class NativeDisplayProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-display-probe-")
        self.root = Path(self.temp.name)
        self.socket_dir = self.root / ".X11-unix"
        self.socket_dir.mkdir(mode=0o700)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_connected_owned_socket_is_ready(self) -> None:
        path = self.socket_dir / "X1"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)
        thread = threading.Thread(target=lambda: server.accept()[0].close(), daemon=True)
        thread.start()
        try:
            self.assertEqual(probe.probe(":1", str(self.root)), (True, "ready"))
        finally:
            server.close()
            thread.join(timeout=1)

    def test_missing_or_refused_socket_is_not_ready(self) -> None:
        ok, reason = probe.probe(":1", str(self.root))
        self.assertFalse(ok)
        self.assertEqual(reason, "local X11 socket is unavailable")
        path = self.socket_dir / "X2"
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(path))
        stale.close()
        ok, reason = probe.probe(":2", str(self.root))
        self.assertFalse(ok)
        self.assertEqual(reason, "local X11 server is not accepting connections")

    def test_nonlocal_or_malformed_display_is_rejected(self) -> None:
        for display in ("", "localhost:1", "host:1", ":1bad", ":11.999"):
            with self.subTest(display=display):
                ok, reason = probe.probe(display, str(self.root))
                self.assertFalse(ok)
                self.assertEqual(reason, "DISPLAY must be a local :N display")

    def test_symlink_socket_directory_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        self.socket_dir.rename(self.root / "saved")
        self.socket_dir.symlink_to(outside, target_is_directory=True)
        ok, reason = probe.probe(":1", str(self.root))
        self.assertFalse(ok)
        self.assertEqual(reason, "local X11 socket directory is unsafe")


if __name__ == "__main__":
    unittest.main()
