from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import hermes_adapter


class HermesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-hermes-")
        self.addCleanup(self.temp.cleanup)
        self.prefix = Path(self.temp.name) / "prefix"
        executable = self.prefix / "bin/hermes"
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
        executable.chmod(0o700)
        patcher = mock.patch.object(hermes_adapter, "_NATIVE_PREFIX", self.prefix)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _fake(self, responses):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            result = responses[len(calls) - 1]
            if isinstance(result, BaseException):
                raise result
            return result
        return runner, calls

    def _prefix(self):
        return str(self.prefix)

    def _response(self, stdout="", code=0):
        return subprocess.CompletedProcess([], code, stdout, "sensitive stderr must not escape")

    def test_reports_verified_not_running_without_returning_raw_output(self):
        runner, calls = self._fake([
            self._response("Hermes Agent v0.22.0+canary\nInstall directory: /private/path\n"),
            self._response("✗ No scheduler is serving profile 'default' — jobs will NOT fire\nAPI_KEY=should-not-escape"),
        ])
        result = hermes_adapter.inspect(prefix=self._prefix(), home="/native/home", runner=runner)
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["version"], "v0.22.0+canary")
        self.assertEqual(result["scheduler"], {"state": "not_running", "profile": "default", "health": "not_ready"})
        self.assertNotIn("API_KEY", str(result))
        self.assertNotIn("private/path", str(result))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], [self._prefix() + "/bin/hermes", "--version"])
        self.assertEqual(calls[1][0], [self._prefix() + "/bin/hermes", "cron", "status"])

    def test_recognizes_ready_scheduler(self):
        runner, _ = self._fake([self._response("Hermes Agent v1.2\n"),
                                self._response("✓ Gateway is running — cron jobs will fire automatically")])
        result = hermes_adapter.inspect(prefix=self._prefix(), home="/native/home", runner=runner)
        self.assertEqual(result["scheduler"]["state"], "running")
        self.assertEqual(result["scheduler"]["health"], "ready")

    def test_unknown_output_fails_closed(self):
        runner, _ = self._fake([self._response("Hermes Agent v1.2"), self._response("new unrecognized output")])
        result = hermes_adapter.inspect(prefix=self._prefix(), home="/native/home", runner=runner)
        self.assertEqual(result["scheduler"]["state"], "unknown")
        self.assertEqual(result["error_code"], "unrecognized_status_output")

    def test_timeout_is_unknown_without_leaking_exception(self):
        runner, _ = self._fake([subprocess.TimeoutExpired("hermes", 5)])
        result = hermes_adapter.inspect(prefix=self._prefix(), home="/native/home", runner=runner)
        self.assertEqual(result["availability"], "unknown")
        self.assertEqual(result["error_code"], "probe_timeout")

    def test_rejects_wrong_runtime(self):
        result = hermes_adapter.inspect(prefix="/usr", home="/tmp")
        self.assertEqual(result["availability"], "unavailable")
        self.assertEqual(result["error_code"], "native_termux_required")


if __name__ == "__main__":
    unittest.main()
