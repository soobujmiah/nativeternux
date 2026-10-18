"""Loopback listener tests using only disposable ephemeral ports."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import socket
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_http_server  # noqa: E402


class ManagementHTTPServerTests(unittest.TestCase):
    def make_server(self, *, adapter_factory=None, max_workers=2, timeout=2):
        return management_http_server.LoopbackManagementServer(
            host="127.0.0.1", port=0,
            adapter_factory=adapter_factory or (lambda _port: _Adapter()),
            max_workers=max_workers, request_timeout_seconds=timeout,
        )

    def test_listener_is_loopback_and_routes_health_then_closes(self) -> None:
        server = self.make_server()
        self.assertEqual(server.address[0], "127.0.0.1")
        server.start()
        connection = http.client.HTTPConnection(*server.address, timeout=2)
        connection.request("GET", "/health")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.read())["status"], "alive")
        connection.close()
        self.assertTrue(server.close(grace_seconds=2))
        self.assertTrue(server.close(grace_seconds=2))

    def test_factory_receives_bound_ephemeral_port(self) -> None:
        observed = []
        server = self.make_server(adapter_factory=lambda port: observed.append(port) or _Adapter())
        self.assertEqual(observed, [server.address[1]])
        server.close()

    def test_non_loopback_bind_and_invalid_limits_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            management_http_server.LoopbackManagementServer(
                host="0.0.0.0", port=0, adapter_factory=lambda _port: _Adapter())
        with self.assertRaises(ValueError):
            management_http_server.LoopbackManagementServer(
                host="127.0.0.1", port=0, max_workers=17,
                adapter_factory=lambda _port: _Adapter())
        with self.assertRaises(ValueError):
            management_http_server.LoopbackManagementServer(
                host="127.0.0.1", port=0, request_timeout_seconds=0.1,
                adapter_factory=lambda _port: _Adapter())

    def test_oversized_body_is_rejected_before_adapter_dispatch(self) -> None:
        adapter = _Adapter()
        server = self.make_server(adapter_factory=lambda _port: adapter)
        server.start()
        connection = http.client.HTTPConnection(*server.address, timeout=2)
        connection.request("POST", "/api/v1/operations", body=b"", headers={
            "Content-Length": str(management_http_server.management_request_policy.MAX_JSON_BODY_BYTES + 1),
            "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{server.port}",
        })
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        self.assertEqual(json.loads(response.read())["error"], "body_too_large")
        self.assertEqual(adapter.calls, 0)
        connection.close()
        self.assertTrue(server.close(grace_seconds=2))

    def test_oversized_decimal_length_is_rejected_without_integer_conversion(self) -> None:
        adapter = _Adapter()
        server = self.make_server(adapter_factory=lambda _port: adapter)
        server.start()
        try:
            connection = socket.create_connection(server.address, timeout=2)
            connection.sendall(
                b"POST /api/v1/operations HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\nContent-Type: application/json\r\n"
                b"Origin: http://127.0.0.1\r\nContent-Length: " + b"9" * 5000 + b"\r\n\r\n"
            )
            response = connection.recv(4096)
            connection.close()
            self.assertIn(b"HTTP/1.1 413 ", response)
            self.assertEqual(adapter.calls, 0)
        finally:
            self.assertTrue(server.close(grace_seconds=2))

    def test_malformed_http_uses_redacted_json_error(self) -> None:
        adapter = _Adapter()
        server = self.make_server(adapter_factory=lambda _port: adapter)
        server.start()
        try:
            connection = socket.create_connection(server.address, timeout=2)
            connection.sendall(b"not a valid request line\r\n")
            response = bytearray()
            while True:
                chunk = connection.recv(1024)
                if not chunk:
                    break
                response.extend(chunk)
            connection.close()
            self.assertIn(b"400 Bad Request", response)
            self.assertIn(b"Content-Type: application/json", response)
            self.assertIn(b"X-Content-Type-Options: nosniff", response)
            self.assertNotIn(b"not a valid request line", response)
            self.assertEqual(adapter.calls, 0)
        finally:
            self.assertTrue(server.close(grace_seconds=2))

    def test_worker_limit_rejects_excess_connection_and_shutdown_drains(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        adapter = _BlockingAdapter(entered, release)
        server = self.make_server(adapter_factory=lambda _port: adapter, max_workers=1)
        server.start()
        first_result = []

        def first_request():
            connection = http.client.HTTPConnection(*server.address, timeout=3)
            connection.request("GET", "/health")
            response = connection.getresponse()
            first_result.append((response.status, response.read()))
            connection.close()

        first = threading.Thread(target=first_request)
        first.start()
        self.assertTrue(entered.wait(2))
        second = socket.create_connection(server.address, timeout=2)
        second.sendall(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
        second_reply = second.recv(1024)
        second.close()
        self.assertIn(b"503 Service Unavailable", second_reply)
        release.set()
        first.join(timeout=3)
        self.assertFalse(first.is_alive())
        self.assertEqual(first_result[0][0], 200)
        self.assertTrue(server.close(grace_seconds=2))

    def test_request_deadline_closes_client_but_does_not_fake_cancel_operation(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        server = self.make_server(
            adapter_factory=lambda _port: _BlockingAdapter(entered, release), timeout=1)
        server.start()
        errors = []

        def slow_request():
            connection = http.client.HTTPConnection(*server.address, timeout=3)
            try:
                connection.request("GET", "/health")
                response = connection.getresponse()
                response.read()
                errors.append("unexpected response")
            except (OSError, http.client.HTTPException):
                errors.append("connection_closed")
            finally:
                connection.close()

        client = threading.Thread(target=slow_request)
        client.start()
        self.assertTrue(entered.wait(2))
        client.join(timeout=2)
        self.assertFalse(client.is_alive())
        self.assertEqual(errors, ["connection_closed"])
        self.assertFalse(server.close(grace_seconds=0.1))
        release.set()
        self.assertTrue(server.close(grace_seconds=2))


class _Adapter:
    def __init__(self):
        self.calls = 0

    def handle(self, *, method, path, headers, body):
        self.calls += 1
        payload = b'{"ok":true,"status":"alive"}'
        return 200, {"Content-Type": "application/json", "Content-Length": str(len(payload)),
                     "Connection": "close"}, payload


class _BlockingAdapter(_Adapter):
    def __init__(self, entered, release):
        super().__init__()
        self.entered = entered
        self.release = release

    def handle(self, *, method, path, headers, body):
        self.calls += 1
        self.entered.set()
        self.release.wait(2)
        payload = b'{"ok":true}'
        return 200, {"Content-Type": "application/json", "Content-Length": str(len(payload)),
                     "Connection": "close"}, payload


if __name__ == "__main__":
    unittest.main()
