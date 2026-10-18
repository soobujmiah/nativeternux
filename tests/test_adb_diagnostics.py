"""Contract tests for the loopback-only read-only ADB server probe."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import adb_diagnostics  # noqa: E402


class FakeConnection:
    def __init__(self, response: bytes, *, chunk_size: int = 4096) -> None:
        self.response = bytearray(response)
        self.chunk_size = chunk_size
        self.sent = bytearray()
        self.timeout = None
        self.closed = False

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def sendall(self, value: bytes) -> None:
        self.sent.extend(value)

    def recv(self, size: int) -> bytes:
        count = min(size, self.chunk_size, len(self.response))
        value = bytes(self.response[:count])
        del self.response[:count]
        return value

    def close(self) -> None:
        self.closed = True


class AdbDiagnosticsTests(unittest.TestCase):
    def test_reads_only_local_host_version_and_reports_protocol_version(self) -> None:
        connection = FakeConnection(b"OKAY00040029", chunk_size=2)
        calls = []

        def connect(address, **kwargs):
            calls.append((address, kwargs))
            return connection

        report = adb_diagnostics.inspect_local_server(connector=connect)
        self.assertEqual(report["status"], "available")
        self.assertEqual(report["host"], "127.0.0.1")
        self.assertEqual(report["port"], 5037)
        self.assertEqual(report["server_protocol_version_hex"], "0029")
        self.assertEqual(calls, [(('127.0.0.1', 5037), {"timeout": 1.5})])
        self.assertEqual(bytes(connection.sent), b"000chost:version")
        self.assertTrue(connection.closed)
        self.assertEqual(report["safety"], {
            "read_only": True,
            "adb_executable_invoked": False,
            "server_started_or_stopped": False,
            "device_list_requested": False,
            "device_command_sent": False,
        })

    def test_connection_refusal_is_not_observed_not_claimed_absent(self) -> None:
        def refuse(*_args, **_kwargs):
            raise ConnectionRefusedError("fixture")
        report = adb_diagnostics.inspect_local_server(connector=refuse)
        self.assertEqual(report["status"], "not_observed")
        self.assertIsNone(report["server_protocol_version_hex"])

    def test_timeout_and_io_errors_are_unknown(self) -> None:
        for error in (TimeoutError("fixture"), OSError("fixture")):
            def fail(*_args, _error=error, **_kwargs):
                raise _error
            self.assertEqual(adb_diagnostics.inspect_local_server(connector=fail)["status"], "unknown")

    def test_invalid_protocol_is_reported_without_returning_payload(self) -> None:
        for response in (b"FAIL", b"OKAYzzzz", b"OKAY0009", b"OKAY0004xy!z"):
            connection = FakeConnection(response)
            report = adb_diagnostics.inspect_local_server(
                connector=lambda *_args, **_kwargs: connection)
            self.assertEqual(report["status"], "protocol_error")
            self.assertIsNone(report["server_protocol_version_hex"])

    def test_report_matches_strict_schema_for_all_states(self) -> None:
        schema = json.loads((ROOT / "schemas/adb-server-diagnostics.schema.json").read_text())
        reports = [
            adb_diagnostics.inspect_local_server(connector=lambda *_a, **_k: FakeConnection(b"OKAY00040029")),
            adb_diagnostics.inspect_local_server(connector=lambda *_a, **_k: (_ for _ in ()).throw(ConnectionRefusedError())),
            adb_diagnostics.inspect_local_server(connector=lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError())),
            adb_diagnostics.inspect_local_server(connector=lambda *_a, **_k: FakeConnection(b"NOPE")),
        ]
        expected = set(schema["properties"])
        for report in reports:
            self.assertEqual(set(report), expected)
            self.assertEqual(report["component"], "adb_server_diagnostics")
            self.assertEqual(report["host"], "127.0.0.1")
            self.assertEqual(report["port"], 5037)
            self.assertIs(report["safety"]["read_only"], True)
            self.assertIs(report["safety"]["device_command_sent"], False)


if __name__ == "__main__":
    unittest.main()
