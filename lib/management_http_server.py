"""Explicitly started, loopback-only HTTP listener for the management adapter.

This module never starts or binds a listener at import time. Callers must supply
an adapter factory so its exact Host/Origin policy can use the selected port.
"""
from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socket
import threading
import time
from typing import Any
from socketserver import ThreadingMixIn

import management_request_policy


MAX_WORKERS = 4
MAX_HEADER_COUNT = 64
MAX_RESPONSE_BYTES = 1024 * 1024
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0


def _error_body(code: str) -> bytes:
    return json.dumps({"ok": False, "error": code}, separators=(",", ":")).encode()


class _BoundedHTTPServer(ThreadingMixIn, HTTPServer):
    request_queue_size = 16
    allow_reuse_address = False
    daemon_threads = False
    block_on_close = False

    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], *,
                 max_workers: int, request_timeout: float) -> None:
        self._worker_slots = threading.BoundedSemaphore(max_workers)
        self._request_timeout = request_timeout
        self._active_condition = threading.Condition()
        self._active_workers = 0
        self._closing = False
        super().__init__(address, handler, bind_and_activate=True)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(self._request_timeout)
        return connection, address

    def process_request(self, request: socket.socket, client_address: Any) -> None:
        if self._closing or not self._worker_slots.acquire(blocking=False):
            try:
                body = _error_body("server_busy")
                response = (
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\nCache-Control: no-store\r\n"
                    b"X-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n"
                    b"Content-Security-Policy: default-src 'none'; frame-ancestors 'none'\r\n"
                    b"Content-Type: application/json\r\n"
                    + f"Content-Length: {len(body)}\r\n\r\n".encode() + body
                )
                request.sendall(response)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        with self._active_condition:
            self._active_workers += 1
        try:
            super().process_request(request, client_address)
        except Exception:
            with self._active_condition:
                self._active_workers -= 1
                self._active_condition.notify_all()
            self._worker_slots.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._active_condition:
                self._active_workers -= 1
                self._active_condition.notify_all()
            self._worker_slots.release()

    def handle_error(self, request: socket.socket, client_address: Any) -> None:
        # Never emit request/parser details into stderr or service logs.
        return

    def reject_new_workers(self) -> None:
        self._closing = True

    def wait_for_workers(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        with self._active_condition:
            while self._active_workers:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._active_condition.wait(remaining)
            return True


class LoopbackManagementServer:
    """Manage one explicit IPv4 loopback listener with bounded request workers."""

    def __init__(
        self,
        *,
        adapter_factory: Callable[[int], Any],
        host: str = "127.0.0.1",
        port: int,
        max_workers: int = MAX_WORKERS,
        request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("management HTTP server must bind exactly to 127.0.0.1")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("management HTTP port must be 0..65535")
        if type(max_workers) is not int or not 1 <= max_workers <= 16:
            raise ValueError("management HTTP worker limit must be 1..16")
        if (not isinstance(request_timeout_seconds, (int, float))
                or not 1.0 <= request_timeout_seconds <= 60.0):
            raise ValueError("management HTTP request timeout must be 1..60 seconds")

        self._handler_type = self._make_handler()
        self._server = _BoundedHTTPServer(
            (host, port), self._handler_type,
            max_workers=max_workers, request_timeout=float(request_timeout_seconds))
        self.host, self.port = self._server.server_address[:2]
        try:
            self.adapter = adapter_factory(self.port)
        except Exception:
            self._server.server_close()
            raise
        if not callable(getattr(self.adapter, "handle", None)):
            self._server.server_close()
            raise TypeError("adapter factory must return a management HTTP adapter")
        self._serve_thread: threading.Thread | None = None
        self._closed = False
        self._lifecycle_lock = threading.Lock()
        self._ready_event = threading.Event()
        readiness_probe = getattr(self.adapter, "set_readiness_probe", None)
        if callable(readiness_probe):
            try:
                readiness_probe(self.is_ready)
            except Exception:
                self._server.server_close()
                raise

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    def is_ready(self) -> bool:
        """Report ready only while the owned serving thread is accepting work."""
        thread = self._serve_thread
        return bool(
            self._ready_event.is_set()
            and thread is not None
            and thread.is_alive()
            and not self._server._closing
            and not self._closed
        )

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server_owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "TernuxxManagement/1"
            sys_version = ""

            def log_message(self, _format: str, *args: object) -> None:
                # The request target and header values may contain secrets.
                return

            def send_error(self, code: int, message: str | None = None,
                           explain: str | None = None) -> None:
                # Replace the base handler's HTML and reflected parser text.
                self.close_connection = True
                self.request_version = "HTTP/1.1"
                self._send(code, {"error": "bad_http_request"})

            def handle_one_request(self) -> None:
                timeout = server_owner._server._request_timeout
                deadline = threading.Timer(timeout, self._expire_request)
                deadline.daemon = True
                deadline.start()
                try:
                    super().handle_one_request()
                finally:
                    deadline.cancel()

            def _expire_request(self) -> None:
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            def do_GET(self) -> None:
                self._dispatch()

            def do_POST(self) -> None:
                self._dispatch()

            def _dispatch(self) -> None:
                self.close_connection = True
                if len(self.headers) > MAX_HEADER_COUNT:
                    self._send(431, {"ok": False, "error": "too_many_headers"})
                    return
                normalized: dict[str, str] = {}
                for name in self.headers.keys():
                    key = name.lower()
                    values = self.headers.get_all(name, [])
                    if key in normalized or len(values) != 1:
                        self._send(400, {"ok": False, "error": "duplicate_header"})
                        return
                    normalized[key] = values[0]

                raw_length = normalized.get("content-length")
                body = b""
                if raw_length is not None:
                    if not raw_length.isascii() or not raw_length.isdecimal():
                        self._send(400, {"ok": False, "error": "invalid_content_length"})
                        return
                    if len(raw_length) > 5:
                        self._send(413, {"ok": False, "error": "body_too_large"})
                        return
                    length = int(raw_length)
                    if length > management_request_policy.MAX_JSON_BODY_BYTES:
                        self._send(413, {"ok": False, "error": "body_too_large"})
                        return
                    try:
                        body = self.rfile.read(length)
                    except (OSError, TimeoutError):
                        self._send(408, {"ok": False, "error": "request_timeout"})
                        return
                    if len(body) != length:
                        self._send(400, {"ok": False, "error": "incomplete_body"})
                        return
                try:
                    status, headers, response_body = server_owner.adapter.handle(
                        method=self.command, path=self.path, headers=normalized, body=body)
                    if (type(status) is not int or not 100 <= status <= 599
                            or not isinstance(headers, dict)
                            or any(not isinstance(k, str) or not isinstance(v, str)
                                   for k, v in headers.items())
                            or not isinstance(response_body, bytes)
                            or len(response_body) > MAX_RESPONSE_BYTES):
                        raise TypeError("invalid management adapter response")
                except Exception:
                    response_body = _error_body("internal_error")
                    status, headers, response_body = 500, {
                        "Content-Type": "application/json; charset=utf-8",
                        "Content-Length": str(len(response_body)), "Cache-Control": "no-store",
                        "Connection": "close",
                    }, response_body
                self._send(status, headers, response_body)

            def _send(self, status: int, headers: dict[str, str], body: bytes | None = None) -> None:
                if body is None:
                    body = _error_body(str(headers.get("error", "request_rejected")))
                    headers = {"Content-Type": "application/json; charset=utf-8",
                               "Content-Length": str(len(body)), "Cache-Control": "no-store",
                               "X-Content-Type-Options": "nosniff",
                               "Referrer-Policy": "no-referrer",
                               "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
                               "Connection": "close"}
                self.send_response(status)
                for name, value in headers.items():
                    if "\r" not in name and "\n" not in name and "\r" not in value and "\n" not in value:
                        self.send_header(name, value)
                self.end_headers()
                try:
                    self.wfile.write(body)
                    self.wfile.flush()
                except (OSError, TimeoutError):
                    pass

        return Handler

    def start(self) -> None:
        """Start the listener in a non-daemon owned thread; repeated start is safe."""
        with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("management HTTP server is closed")
            if self._serve_thread is not None and self._serve_thread.is_alive():
                return
            self._serve_thread = threading.Thread(
                target=self._server.serve_forever, kwargs={"poll_interval": 0.1},
                name="ternuxx-management-http", daemon=False)
            self._serve_thread.start()
            self._ready_event.set()

    def close(self, *, grace_seconds: float = 5.0) -> bool:
        """Stop accepting requests and wait up to grace_seconds for handlers."""
        if not isinstance(grace_seconds, (int, float)) or not 0 <= grace_seconds <= 60:
            raise ValueError("shutdown grace must be between 0 and 60 seconds")
        with self._lifecycle_lock:
            if self._closed:
                return self._server.wait_for_workers(float(grace_seconds))
            self._ready_event.clear()
            self._server.reject_new_workers()
            thread = self._serve_thread
            if thread is not None and thread.is_alive():
                self._server.shutdown()
                thread.join(timeout=min(float(grace_seconds), 5.0))
            drained = self._server.wait_for_workers(float(grace_seconds))
            self._server.server_close()
            self._closed = True
            return drained
