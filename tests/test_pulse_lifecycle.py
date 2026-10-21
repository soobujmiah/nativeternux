from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import pulse_lifecycle  # noqa: E402


BASE = """# Native PulseAudio
load-module module-sles-sink
load-module module-native-protocol-tcp listen=127.0.0.1 auth-ip-acl=127.0.0.1 auth-anonymous=1 port=4713
set-default-sink Speaker
"""


class PulseLifecycleTests(unittest.TestCase):
    def test_managed_config_replaces_only_known_loopback_anonymous_listener(self):
        result = pulse_lifecycle.managed_config(BASE, "/native/home/.config/pulse/cookie")
        self.assertIn("load-module module-sles-sink", result)
        self.assertIn("listen=127.0.0.1 port=4713", result)
        self.assertIn("auth-anonymous=0 auth-cookie-enabled=1", result)
        self.assertIn("auth-cookie=/native/home/.config/pulse/cookie", result)
        self.assertNotIn("auth-ip-acl=0.0.0.0", result)
        self.assertNotIn("auth-anonymous=1", result)

    def test_managed_config_removes_unavailable_termux_modules_and_legacy_sink(self):
        source = "\n".join((
            ".ifexists module-console-kit.so",
            "load-module module-console-kit",
            ".endif",
            ".ifexists module-systemd-login.so",
            "load-module module-systemd-login",
            ".endif",
            "load-module module-sles-sink",
            "load-module module-opensles-sink sink_name=Speaker",
            "set-default-sink Speaker",
        ))
        result = pulse_lifecycle.managed_config(source, "/cookie")
        self.assertIn("load-module module-sles-sink", result)
        self.assertNotIn("load-module module-console-kit", result)
        self.assertNotIn("load-module module-systemd-login", result)
        self.assertNotIn("module-opensles-sink", result)
        self.assertNotIn("set-default-sink Speaker", result)
        self.assertIn("auth-anonymous=0 auth-cookie-enabled=1", result)

    def test_managed_config_adds_scoped_listener_when_absent(self):
        result = pulse_lifecycle.managed_config("load-module module-sles-sink\n", "/cookie")
        self.assertEqual(result.count("module-native-protocol-tcp"), 1)
        self.assertIn("listen=127.0.0.1 port=4713", result)

    def test_managed_config_rejects_wildcard_or_unrecognized_listener(self):
        for line in (
            "load-module module-native-protocol-tcp port=4713 auth-anonymous=1",
            "load-module module-native-protocol-tcp listen=0.0.0.0 port=4713 auth-anonymous=1",
            "load-module module-native-protocol-tcp listen=127.0.0.1 port=4713 auth-anonymous=1 extra=1",
        ):
            with self.subTest(line=line), self.assertRaises(pulse_lifecycle.PulseError):
                pulse_lifecycle.managed_config(line, "/cookie")

    def test_managed_config_rejects_duplicate_listeners(self):
        config = BASE + "load-module module-native-protocol-tcp listen=127.0.0.1 port=4714\n"
        with self.assertRaisesRegex(pulse_lifecycle.PulseError, "multiple"):
            pulse_lifecycle.managed_config(config, "/cookie")

    def test_pulse_probe_uses_explicit_tcp_target_and_cookie_without_autospawn(self):
        paths = {"pactl": Path("/termux/bin/pactl"), "cookie": Path("/private/cookie")}
        completed = subprocess.CompletedProcess([], 0,
            "Server Name: PulseAudio\nDefault Sink: Speaker\n", "")
        with patch.object(pulse_lifecycle.subprocess, "run", return_value=completed) as run:
            info = pulse_lifecycle._pulse_info(paths)
        self.assertEqual(info, {"Server Name": "PulseAudio", "Default Sink": "Speaker"})
        args = run.call_args.args[0]
        self.assertEqual(args, ["/termux/bin/pactl", "--server", "tcp:127.0.0.1:4713", "info"])
        self.assertEqual(run.call_args.kwargs["env"]["PULSE_COOKIE"], "/private/cookie")

    def test_cookie_requires_private_regular_file_and_expected_size(self):
        with tempfile.TemporaryDirectory() as directory:
            cookie = Path(directory) / "cookie"
            cookie.write_bytes(b"x" * 256)
            cookie.chmod(0o600)
            self.assertEqual(pulse_lifecycle._cookie({"cookie": cookie}), cookie)
            cookie.chmod(0o640)
            with self.assertRaisesRegex(pulse_lifecycle.PulseError, "unsafe"):
                pulse_lifecycle._cookie({"cookie": cookie})
            cookie.chmod(0o600)
            cookie.write_bytes(b"short")
            with self.assertRaisesRegex(pulse_lifecycle.PulseError, "unexpected size"):
                pulse_lifecycle._cookie({"cookie": cookie})

    def test_audio_record_rejects_symlink_and_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("{}")
            link = root / "record"
            link.symlink_to(target)
            with self.assertRaises(pulse_lifecycle.PulseError):
                pulse_lifecycle._record_read(link)
            link.unlink()
            link.write_text('{"schema":1,"owner":"ternuxx-native-pulseaudio-v1","pid":1,"start_ticks":"1","process_group":1}')
            link.chmod(0o644)
            with self.assertRaises(pulse_lifecycle.PulseError):
                pulse_lifecycle._record_read(link)

    def test_start_refuses_a_second_lifecycle_operation_while_lock_is_held(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            env = {"PREFIX": "/data/data/com.termux/files/usr",
                   "TERMUX_VERSION": "fixture", "HOME": directory,
                   "TERNUXX_STATE_DIR": str(state)}
            with patch.dict(os.environ, env):
                paths = pulse_lifecycle._native_paths()
                pulse_lifecycle._ensure_audio_dirs(paths)
                with pulse_lifecycle._Lock(paths["lock"]):
                    with self.assertRaisesRegex(pulse_lifecycle.PulseError, "operation is in progress"):
                        pulse_lifecycle.start()
            self.assertFalse(paths["record"].exists())

    def test_lifecycle_refuses_non_native_environment(self):
        with patch.dict(os.environ, {"PREFIX": "/usr", "TERMUX_VERSION": ""}, clear=False):
            with self.assertRaisesRegex(pulse_lifecycle.PulseError, "Native Termux"):
                pulse_lifecycle.status()


if __name__ == "__main__":
    unittest.main()
