"""Authenticated HTTP request adapter; deliberately does not bind a socket.

The foreground server binds to 127.0.0.1 and enforces worker, request, and time
bounds before passing each request here. After session authentication, this
adapter dispatches typed operations through the shared application service and
does not expose generic shell or ADB forwarding. The default management API keeps mutation dispatch disabled. Web mode may enable
a fixed, explicitly scoped set of typed operations.
"""
from __future__ import annotations

from collections.abc import Mapping, Iterable
import hashlib
import json
import re
import secrets
import threading
import time
from typing import Callable

import management_request_policy
import management_service
import management_sessions
import terminal_broker


REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,96}$")
_MISSING = object()
_WEB_TERMINAL_OPERATIONS = frozenset({
    "terminal.start.preview", "terminal.start", "terminal.channel.issue",
    "terminal.attach", "terminal.input", "terminal.resize", "terminal.output",
    "terminal.detach", "terminal.close.preview", "terminal.close",
})


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> object:
    raise ValueError("invalid JSON constant")


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


class ManagementHTTPAdapter:
    """Translate guarded, authenticated local HTTP requests into typed calls."""

    def __init__(
        self,
        *,
        expected_origin: str,
        bootstrap_secret: str,
        bootstrap_capabilities: Iterable[str],
        env: dict[str, str] | None = None,
        dispatcher: Callable[..., dict[str, object]] = management_service.dispatch,
        clock: Callable[[], float] = time.monotonic,
        allow_mutations: bool = False,
        request_store: object | None = None,
        readiness_probe: Callable[[], bool] | None = None,
    ) -> None:
        self.policy = management_request_policy.LoopbackRequestPolicy(expected_origin, clock=clock)
        self.sessions = management_sessions.ManagementSessionAuthority(
            bootstrap_secret, bootstrap_capabilities, clock=clock)
        self._env = env
        self._dispatcher = dispatcher
        self._request_store = request_store
        self._allow_mutations = (allow_mutations is True
                                 and getattr(request_store, "durable", False) is True)
        self._readiness_probe = readiness_probe
        self._terminal_lock = threading.RLock()
        self._terminal_tickets: dict[str, dict[str, object]] = {}
        self._terminal_attachments: dict[tuple[str, str], dict[str, object]] = {}

    def set_readiness_probe(self, probe: Callable[[], bool]) -> None:
        """Attach the owning HTTP listener's lifecycle readiness check."""
        if not callable(probe):
            raise ValueError("readiness probe must be callable")
        self._readiness_probe = probe

    def handle(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, object],
        body: bytes = b"",
    ) -> tuple[int, dict[str, str], bytes]:
        """Return (status, headers, JSON bytes); never emits request secrets."""
        if not isinstance(body, bytes):
            return self._response(400, {"ok": False, "error": "invalid_body"})
        normalized_headers: dict[str, object] = {}
        for name, value in headers.items():
            key = str(name).lower()
            if key in normalized_headers:
                return self._response(400, {"ok": False, "error": "duplicate_header"})
            normalized_headers[key] = value
        content_length = normalized_headers.get("content-length", _MISSING)
        if method == "GET" and content_length is _MISSING and not body:
            parsed_length: object = 0
        elif content_length is _MISSING or not isinstance(content_length, str) or not content_length.isdecimal():
            parsed_length: object = _MISSING
        else:
            parsed_length = int(content_length)
        if "transfer-encoding" in normalized_headers:
            return self._response(400, {"ok": False, "error": "transfer_encoding_rejected"})
        if parsed_length is _MISSING or parsed_length != len(body):
            return self._response(400, {"ok": False, "error": "content_length_mismatch"})

        decision = self.policy.check(
            host=normalized_headers.get("host"), method=method,
            origin=normalized_headers.get("origin"),
            content_type=normalized_headers.get("content-type"),
            content_length=parsed_length,
        )
        if not decision.allowed:
            status = 429 if decision.reason == "rate_limited" else 403
            return self._response(status, {"ok": False, "error": decision.reason})

        if method == "GET" and path == "/health":
            return self._response(200, {"ok": True, "api_version": 1, "status": "alive"})
        if method == "GET" and path == "/ready":
            ready = False
            if self._readiness_probe is not None:
                try:
                    ready = self._readiness_probe() is True
                except Exception:
                    ready = False
            return self._response(200 if ready else 503, {
                "ok": ready,
                "api_version": 1,
                "ready": ready,
                "status": "ready" if ready else "not_ready",
            })
        if not isinstance(path, str) or method != "POST" or "?" in path or "#" in path:
            return self._response(404, {"ok": False, "error": "route_not_found"})
        try:
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                                 parse_constant=_reject_json_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return self._response(400, {"ok": False, "error": "invalid_json"})
        if not isinstance(payload, dict):
            return self._response(400, {"ok": False, "error": "invalid_request"})

        if path == "/api/v1/session":
            return self._bootstrap(payload)
        if path == "/api/v1/session/revoke":
            return self._revoke(normalized_headers, payload)
        if path == "/api/v1/operations":
            return self._operation(normalized_headers, payload)
        if path == "/api/v1/terminal":
            return self._terminal_operation(normalized_headers, payload)
        return self._response(404, {"ok": False, "error": "route_not_found"})

    def _bootstrap(self, payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        if set(payload) != {"bootstrap_secret", "capabilities"}:
            return self._response(400, {"ok": False, "error": "invalid_request"})
        secret = payload.get("bootstrap_secret")
        requested = payload.get("capabilities")
        if not isinstance(requested, list) or any(not isinstance(scope, str) for scope in requested):
            return self._response(400, {"ok": False, "error": "invalid_capabilities"})
        try:
            issued = self.sessions.exchange_bootstrap(secret, requested)
        except PermissionError:
            return self._response(401, {"ok": False, "error": "authentication_failed"})
        except ValueError:
            return self._response(400, {"ok": False, "error": "invalid_capabilities"})
        return self._response(200, {
            "ok": True,
            "session": {
                "session_ref": issued.session_ref,
                "bearer_token": issued.bearer_token,
                "csrf_token": issued.csrf_token,
                "capabilities": list(issued.capabilities),
                "idle_ttl_seconds": issued.idle_ttl_seconds,
                "absolute_ttl_seconds": issued.absolute_ttl_seconds,
            },
        })

    def _revoke(self, headers: dict[str, object], payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        if payload:
            return self._response(400, {"ok": False, "error": "invalid_request"})
        bearer = self._bearer(headers)
        csrf = headers.get("x-ternuxx-csrf")
        if not bearer or not isinstance(csrf, str):
            return self._response(401, {"ok": False, "error": "authentication_failed"})
        auth = self.sessions.authorize_request(bearer, "management.catalog")
        if not auth.allowed or not self.sessions.revoke_session(bearer, csrf):
            return self._response(401, {"ok": False, "error": "authentication_failed"})
        if auth.session_ref:
            self._revoke_terminal_channels(auth.session_ref)
        return self._response(200, {"ok": True, "revoked": True})

    def _terminal_operation(self, headers: dict[str, object], payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        operation = payload.get("operation")
        bearer = self._bearer(headers)
        csrf = headers.get("x-ternuxx-csrf")
        if not bearer:
            return self._response(401, {"ok": False, "error": "authentication_required"})
        auth = self.sessions.authorize_request(bearer, operation, csrf_token=csrf)
        if not auth.allowed:
            code = {"unauthenticated": "authentication_required", "session_expired": "session_expired",
                    "scope_denied": "permission_denied", "csrf_rejected": "csrf_rejected"}.get(
                        auth.reason, "permission_denied")
            return self._response(401 if auth.reason in {"unauthenticated", "session_expired"} else 403,
                                  {"ok": False, "error": code})
        request_id = payload.get("request_id")
        if (operation not in _WEB_TERMINAL_OPERATIONS
                or not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id)
                or set(payload) != {"operation", "request_id", "session_id", "generation",
                                    "attachment_id", "channel_ticket", "args"}
                or not isinstance(payload.get("args"), dict)
                or headers.get("origin") != self.policy.expected_origin):
            return self._response(400, {"ok": False, "error": "invalid_terminal_request"})
        try:
            response = self._terminal_dispatch(headers, payload, auth.session_ref or "")
        except (terminal_broker.BrokerError, OSError, ValueError):
            return self._response(503, {"ok": False, "error": "terminal_broker_unavailable"})
        return response

    def _terminal_dispatch(self, headers: dict[str, object], payload: dict[str, object],
                           session_ref: str) -> tuple[int, dict[str, str], bytes]:
        operation = str(payload.get("operation"))
        request_id = str(payload.get("request_id") or "")
        session_id = payload.get("session_id")
        generation = payload.get("generation")
        attachment_id = payload.get("attachment_id")
        ticket = payload.get("channel_ticket")
        args = payload.get("args")
        origin = headers.get("origin")
        if not isinstance(args, dict):
            return self._response(400, {"ok": False, "error": "invalid_terminal_arguments"})
        self._expire_terminal_tickets()
        state_dir = ((self._env or {}).get("TERNUXX_STATE_DIR")
                     or str(__import__("pathlib").Path((self._env or {}).get("HOME") or ".").expanduser()
                            / ".local/share/ternuxx"))
        client = terminal_broker.UnixBrokerClient(state_dir)

        if operation == "terminal.start.preview":
            if any(value is not None for value in (session_id, generation, attachment_id, ticket)) or args:
                return self._response(400, {"ok": False, "error": "invalid_terminal_arguments"})
            result = client.request("terminal.start.preview")
            return self._terminal_result(request_id, result)
        if operation == "terminal.start":
            if (any(value is not None for value in (session_id, generation, attachment_id, ticket))
                    or set(args) != {"confirmed", "plan_id"}
                    or args.get("confirmed") is not True or not isinstance(args.get("plan_id"), str)):
                return self._response(400, {"ok": False, "error": "invalid_terminal_arguments"})
            result = client.request("terminal.start", args=args)
            data = result.get("result") if isinstance(result, dict) else None
            if result.get("ok") is not True or not isinstance(data, dict):
                return self._terminal_result(request_id, result)
            sid = data.get("session_id")
            if not isinstance(sid, str):
                raise terminal_broker.BrokerError("broker start returned no session identity")
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode()).hexdigest()
            with self._terminal_lock:
                self._terminal_tickets[digest] = {
                    "session_ref": session_ref, "session_id": sid, "origin": origin,
                    "lease": data, "expires": time.monotonic() + 20.0,
                }
            return self._response(200, {"ok": True, "request_id": request_id,
                "data": {"session_id": sid, "profile": data.get("profile"),
                         "state": data.get("state"), "channel_ticket": token,
                         "ticket_expires_in": 20}})

        if operation == "terminal.channel.issue":
            if (not isinstance(session_id, str) or generation is not None
                    or attachment_id is not None or ticket is not None or args):
                return self._response(400, {"ok": False, "error": "invalid_terminal_arguments"})
            lease = client.request("terminal.attach", session_id=session_id)
            if lease.get("ok") is not True:
                return self._terminal_result(request_id, lease)
            lease.pop("ok", None)
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode()).hexdigest()
            with self._terminal_lock:
                self._terminal_tickets[digest] = {
                    "session_ref": session_ref, "session_id": session_id, "origin": origin,
                    "lease": lease, "expires": time.monotonic() + 20.0,
                }
            return self._response(200, {"ok": True, "request_id": request_id,
                "data": {"session_id": session_id, "channel_ticket": token,
                         "ticket_expires_in": 20}})

        if operation == "terminal.attach":
            if (not isinstance(session_id, str) or generation is not None
                    or attachment_id is not None or not isinstance(ticket, str) or args):
                return self._response(400, {"ok": False, "error": "invalid_terminal_arguments"})
            digest = hashlib.sha256(ticket.encode()).hexdigest()
            with self._terminal_lock:
                grant = self._terminal_tickets.pop(digest, None)
                if (not grant or grant["session_ref"] != session_ref
                        or grant["session_id"] != session_id or grant["origin"] != origin
                        or grant["expires"] <= time.monotonic()):
                    grant = None
                key = (session_ref, session_id)
                if grant and key in self._terminal_attachments:
                    grant = None
                if grant:
                    lease = dict(grant["lease"])
                    self._terminal_attachments[key] = {
                        "origin": origin, "lease": lease,
                        "last_seen": time.monotonic(),
                    }
                else:
                    lease = {}
            if not grant:
                return self._response(403, {"ok": False, "error": "terminal_channel_rejected"})
            return self._response(200, {"ok": True, "request_id": request_id, "data": lease})

        if not isinstance(session_id, str):
            return self._response(400, {"ok": False, "error": "terminal_session_required"})
        key = (session_ref, session_id)
        with self._terminal_lock:
            channel = self._terminal_attachments.get(key)
            lease = dict(channel["lease"]) if channel else {}
            if (not channel or channel["origin"] != origin
                    or lease.get("generation") != generation
                    or lease.get("attachment_id") != attachment_id):
                channel = None
            else:
                channel["last_seen"] = time.monotonic()
        if not channel:
            return self._response(403, {"ok": False, "error": "terminal_channel_rejected"})
        if operation not in {"terminal.input", "terminal.resize", "terminal.output",
                             "terminal.detach", "terminal.close.preview", "terminal.close"}:
            return self._response(400, {"ok": False, "error": "invalid_terminal_operation"})
        result = client.request(operation, session_id=session_id, generation=generation,
                                attachment_id=attachment_id, args=args)
        if operation == "terminal.detach" and result.get("ok") is True:
            with self._terminal_lock:
                self._terminal_attachments.pop(key, None)
        if operation == "terminal.close" and result.get("ok") is True:
            closed = result.get("result")
            if isinstance(closed, dict) and closed.get("state") == "stopped":
                with self._terminal_lock:
                    self._terminal_attachments.pop(key, None)
        return self._terminal_result(request_id, result)

    def _terminal_result(self, request_id: str, result: object) -> tuple[int, dict[str, str], bytes]:
        if not isinstance(result, dict):
            return self._response(502, {"ok": False, "error": "invalid_terminal_response"})
        if result.get("ok") is not True:
            error = result.get("error")
            code = error.get("code") if isinstance(error, dict) else "terminal_operation_failed"
            return self._response(409, {"ok": False, "error": code})
        return self._response(200, {"ok": True, "request_id": request_id, "data": result})

    def _expire_terminal_tickets(self) -> None:
        now = time.monotonic()
        with self._terminal_lock:
            expired = [key for key, item in self._terminal_tickets.items()
                       if item.get("expires", 0) <= now]
            leases = [self._terminal_tickets.pop(key).get("lease", {}) for key in expired]
            stale = [key for key, item in self._terminal_attachments.items()
                     if now - item.get("last_seen", now) > 90.0]
            leases.extend(self._terminal_attachments.pop(key).get("lease", {}) for key in stale)
        if not leases:
            return
        state_dir = ((self._env or {}).get("TERNUXX_STATE_DIR")
                     or str(__import__("pathlib").Path((self._env or {}).get("HOME") or ".").expanduser()
                            / ".local/share/ternuxx"))
        client = terminal_broker.UnixBrokerClient(state_dir)
        for lease in leases:
            try:
                client.request("terminal.detach", session_id=lease.get("session_id"),
                    generation=lease.get("generation"), attachment_id=lease.get("attachment_id"))
            except terminal_broker.BrokerError:
                pass

    def _revoke_terminal_channels(self, session_ref: str) -> None:
        with self._terminal_lock:
            items = [(key, value) for key, value in self._terminal_attachments.items()
                     if key[0] == session_ref]
            tickets = [value for value in self._terminal_tickets.values()
                       if value.get("session_ref") == session_ref]
            for key, _value in items:
                self._terminal_attachments.pop(key, None)
            self._terminal_tickets = {key: value for key, value in self._terminal_tickets.items()
                                      if value.get("session_ref") != session_ref}
        leases = [value.get("lease", {}) for _key, value in items] + [
            value.get("lease", {}) for value in tickets]
        if not leases:
            return
        state_dir = ((self._env or {}).get("TERNUXX_STATE_DIR")
                     or str(__import__("pathlib").Path((self._env or {}).get("HOME") or ".").expanduser()
                            / ".local/share/ternuxx"))
        client = terminal_broker.UnixBrokerClient(state_dir)
        for lease in leases:
            try:
                client.request("terminal.detach", session_id=lease.get("session_id"),
                    generation=lease.get("generation"), attachment_id=lease.get("attachment_id"))
            except terminal_broker.BrokerError:
                pass

    def _operation(self, headers: dict[str, object], payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        operation = payload.get("operation")
        if operation == "proot.recovery.reconcile":
            return self._response(403, {"ok": False, "error": "operation_not_available_in_web"})
        bearer = self._bearer(headers)
        csrf = headers.get("x-ternuxx-csrf")
        if not bearer:
            return self._response(401, {"ok": False, "error": "authentication_required"})
        auth = self.sessions.authorize_request(bearer, operation, csrf_token=csrf)
        if not auth.allowed:
            code = {"unauthenticated": "authentication_required", "session_expired": "session_expired",
                    "scope_denied": "permission_denied", "csrf_rejected": "csrf_rejected"}.get(
                        auth.reason, "permission_denied")
            return self._response(401 if auth.reason in {"unauthenticated", "session_expired"} else 403,
                                  {"ok": False, "error": code})

        if operation in _WEB_TERMINAL_OPERATIONS:
            return self._response(403, {"ok": False, "error": "terminal_channel_transport_required"})

        # Network clients may launch only a fixed named app. Desktop-entry IDs
        # can select a broader guest launcher surface and remain local-only.
        if operation == "proot.app.launch":
            args = payload.get("args")
            if (not isinstance(args, dict) or "app_id" not in args
                    or set(args) - {"app_id", "display"}):
                return self._response(400, {"ok": False, "error": "named_app_only"})

        # Browser sessions can run only the fixed bounded headless probe.
        # Interactive login requires an attached terminal and is unavailable
        # through this HTTP transport.
        if operation == "proot.start":
            args = payload.get("args")
            if (not isinstance(args, dict) or args.get("profile") != "isolated-probe"
                    or args.get("timeout_seconds") != 300):
                return self._response(403, {"ok": False, "error": "proot_profile_restricted"})

        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
            return self._response(400, {"ok": False, "error": "invalid_request_id"})
        is_mutation = operation in management_sessions.MUTATING_OPERATIONS
        idempotency_key = headers.get("idempotency-key")
        fingerprint = ""
        if is_mutation:
            if not isinstance(idempotency_key, str) or not IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key):
                return self._response(400, {"ok": False, "error": "idempotency_key_required"})
            fingerprint = hashlib.sha256(_canonical_json(payload)).hexdigest()
            if not self._allow_mutations:
                return self._response(403, {"ok": False, "error": "mutation_transport_disabled"})
            try:
                cache_status = self._request_store.begin(
                    session_ref=auth.session_ref or "", idempotency_key=idempotency_key,
                    fingerprint=fingerprint, request_id=request_id, operation=operation)
            except (OSError, RuntimeError, ValueError):
                return self._response(503, {"ok": False, "error": "durable_request_store_unavailable"})
            if cache_status == "conflict":
                return self._response(409, {"ok": False, "error": "idempotency_conflict"})
            if cache_status == "completed":
                return self._response(409, {"ok": False, "error": "request_already_completed"})
            if cache_status == "in_progress":
                return self._response(409, {"ok": False, "error": "operation_outcome_unknown"})
            if cache_status != "new":
                return self._response(503, {"ok": False, "error": "durable_request_store_unavailable"})

        started_at = time.monotonic()
        try:
            result = self._dispatcher(payload, caller="local_cli", env=self._env)
            if not isinstance(result, dict):
                raise TypeError("application service returned a non-object")
            # Strip free-form service messages from remote-capable transport errors.
            if result.get("ok") is False and isinstance(result.get("error"), dict):
                error = result["error"]
                safe = {"api_version": result.get("api_version", 1),
                        "request_id": result.get("request_id", request_id), "ok": False,
                        "error": {"code": error.get("code", "operation_failed")}}
                result = safe
            response = self._response(200 if result.get("ok") else 400, result)
        except Exception:
            response = self._response(500, {"ok": False, "error": "operation_failed",
                                            "request_id": request_id})
        if is_mutation:
            outcome = "succeeded" if response[0] < 400 else "failed"
            if response[0] >= 500:
                outcome = "unknown"
            try:
                self._request_store.complete(
                    session_ref=auth.session_ref or "", idempotency_key=str(idempotency_key),
                    fingerprint=fingerprint, http_status=response[0], outcome=outcome,
                    duration_ms=max(0, int((time.monotonic() - started_at) * 1000)))
            except (OSError, RuntimeError, ValueError):
                return self._response(503, {"ok": False, "error": "operation_outcome_requires_review",
                                            "request_id": request_id})
        return response

    @staticmethod
    def _bearer(headers: dict[str, object]) -> str | None:
        value = headers.get("authorization")
        if not isinstance(value, str) or len(value) > management_sessions.MAX_TOKEN_LENGTH + 7:
            return None
        parts = value.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
            return None
        return parts[1]

    @staticmethod
    def _response(status: int, payload: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                              allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            status = 500
            body = b'{"ok":false,"error":"response_encoding_failed"}'
        return ManagementHTTPAdapter._base_headers(body, status=status)

    @staticmethod
    def _base_headers(body: bytes, *, status: int = 200) -> tuple[int, dict[str, str], bytes]:
        return status, {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            "Connection": "close",
        }, body
