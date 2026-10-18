"""Tests for the explicit read-only management HTTP foreground runtime."""
from __future__ import annotations

import http.client
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_http_runtime  # noqa: E402


PREFIX = "/data/data/com.termux/files/usr"
SECRET = "S" * 48


def native_env(home: str) -> dict[str, str]:
    return {
        "PREFIX": PREFIX,
        "TERMUX_VERSION": "test-termux",
        "HOME": home,
        "TERNUXX_STATE_DIR": str(Path(home) / ".local/share/ternuxx"),
        "PATH": f"{PREFIX}/bin:/usr/bin",
    }


class TernuxxManagementHTTPRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-http-runtime-")
        self.env = native_env(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_build_requires_native_termux_and_valid_bootstrap_secret(self) -> None:
        with self.assertRaises(ValueError):
            management_http_runtime.build_server(
                port=0, bootstrap_secret=SECRET, env={"HOME": self.temp.name})
        invalid = dict(self.env)
        invalid["PREFIX"] = "/usr"
        with self.assertRaises(ValueError):
            management_http_runtime.build_server(
                port=0, bootstrap_secret=SECRET, env=invalid)
        with self.assertRaises(ValueError):
            management_http_runtime.build_server(
                port=0, bootstrap_secret="short", env=self.env)

    def test_runtime_bootstrap_is_read_only_and_mutations_stay_disabled(self) -> None:
        server = management_http_runtime.build_server(
            port=0, bootstrap_secret=SECRET, env=self.env)
        self.assertEqual(server.address[0], "127.0.0.1")
        self.assertFalse(server.adapter._allow_mutations)
        server.start()
        connection = http.client.HTTPConnection(*server.address, timeout=3)
        try:
            body = json.dumps({
                "bootstrap_secret": SECRET,
                "capabilities": ["services.manage"],
            }).encode()
            connection.request("POST", "/api/v1/session", body=body, headers={
                "Host": f"127.0.0.1:{server.port}",
                "Origin": f"http://127.0.0.1:{server.port}",
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(body)),
            })
            response = connection.getresponse()
            rejection = json.loads(response.read())
            self.assertEqual(response.status, 401)
            self.assertEqual(rejection["error"], "authentication_failed")
            connection.close()

            connection = http.client.HTTPConnection(*server.address, timeout=3)
            body = json.dumps({
                "bootstrap_secret": SECRET,
                "capabilities": ["diagnostics.read"],
            }).encode()
            connection.request("POST", "/api/v1/session", body=body, headers={
                "Host": f"127.0.0.1:{server.port}",
                "Origin": f"http://127.0.0.1:{server.port}",
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(body)),
            })
            response = connection.getresponse()
            issued = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertNotIn(SECRET, json.dumps(issued))
            connection.close()
        finally:
            connection.close()
            self.assertTrue(server.close(grace_seconds=3))

    def test_liveness_and_readiness_are_distinct_and_readiness_tracks_listener(self) -> None:
        server = management_http_runtime.build_server(
            port=0, bootstrap_secret=SECRET, env=self.env)
        host = f"127.0.0.1:{server.port}"
        headers = {"Host": host, "Origin": f"http://{host}"}
        before_status, _, before_body = server.adapter.handle(
            method="GET", path="/ready", headers=headers, body=b"")
        self.assertEqual(before_status, 503)
        self.assertFalse(json.loads(before_body)["ready"])
        self.assertFalse(server.is_ready())

        server.start()
        self.assertTrue(server.is_ready())
        connection = http.client.HTTPConnection(*server.address, timeout=3)
        try:
            connection.request("GET", "/health", headers=headers)
            live = connection.getresponse()
            self.assertEqual(live.status, 200)
            self.assertEqual(json.loads(live.read())["status"], "alive")
            connection.close()

            connection = http.client.HTTPConnection(*server.address, timeout=3)
            connection.request("GET", "/ready", headers=headers)
            ready = connection.getresponse()
            ready_body = json.loads(ready.read())
            self.assertEqual(ready.status, 200)
            self.assertTrue(ready_body["ready"])
            self.assertEqual(ready_body["status"], "ready")
            connection.close()

            connection = http.client.HTTPConnection(*server.address, timeout=3)
            connection.request("GET", "/ready", headers={
                "Host": host,
                "Origin": "http://untrusted.invalid",
            })
            rejected = connection.getresponse()
            self.assertEqual(rejected.status, 403)
            connection.close()
        finally:
            connection.close()
            self.assertTrue(server.close(grace_seconds=3))
        self.assertFalse(server.is_ready())
        closed_status, _, closed_body = server.adapter.handle(
            method="GET", path="/ready", headers=headers, body=b"")
        self.assertEqual(closed_status, 503)
        self.assertFalse(json.loads(closed_body)["ready"])

    def test_noninteractive_main_refuses_before_generating_or_binding(self) -> None:
        err = io.StringIO()
        with patch.object(management_http_runtime.sys, "stderr", err), \
                patch.object(management_http_runtime.management_sessions,
                             "new_bootstrap_secret") as secret_factory:
            result = management_http_runtime.main(["--port", "8765"])
        self.assertEqual(result, 2)
        self.assertIn("TTY is required", err.getvalue())
        secret_factory.assert_not_called()

    def test_cli_port_is_unprivileged(self) -> None:
        err = io.StringIO()
        with patch.object(management_http_runtime.sys, "stderr", err):
            result = management_http_runtime.main(["--port", "80"])
        self.assertEqual(result, 2)
        self.assertIn("1024 to 65535", err.getvalue())


if __name__ == "__main__":
    unittest.main()
