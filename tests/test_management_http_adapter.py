"""In-process contract tests for authenticated management HTTP request routing."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_http_adapter  # noqa: E402
import management_request_store  # noqa: E402
import management_sessions  # noqa: E402


BOOTSTRAP = "T" * 48
ORIGIN = "http://127.0.0.1:8765"


def payload_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def headers_for(body: bytes, **extra: str) -> dict[str, str]:
    return {
        "Host": "127.0.0.1:8765",
        "Origin": ORIGIN,
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        **extra,
    }


def make_adapter(dispatcher=None, *, caps=None, allow_mutations=False, request_store=None):
    return management_http_adapter.ManagementHTTPAdapter(
        expected_origin=ORIGIN,
        bootstrap_secret=BOOTSTRAP,
        bootstrap_capabilities=caps if caps is not None else {"diagnostics.read", "services.manage"},
        env={"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr",
             "HOME": "/tmp/home", "TERNUXX_STATE_DIR": "/tmp/home/.state"},
        dispatcher=dispatcher or Mock(return_value={"ok": True, "api_version": 1,
                                                     "request_id": "request-1234", "data": {"state": "ready"}}),
        allow_mutations=allow_mutations,
        request_store=request_store,
    )


def bootstrap(adapter, capabilities):
    body = payload_bytes({"bootstrap_secret": BOOTSTRAP, "capabilities": capabilities})
    status, _headers, response = adapter.handle(
        method="POST", path="/api/v1/session", headers=headers_for(body), body=body)
    return status, json.loads(response)


class ManagementHTTPAdapterTests(unittest.TestCase):
    def test_health_is_minimal_and_responses_have_security_headers_without_cors(self) -> None:
        adapter = make_adapter()
        status, headers, body = adapter.handle(
            method="GET", path="/health", headers={"Host": "127.0.0.1:8765"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "alive")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_bootstrap_issues_scoped_tokens_once_and_never_echoes_bootstrap(self) -> None:
        adapter = make_adapter()
        status, response = bootstrap(adapter, ["diagnostics.read"])
        self.assertEqual(status, 200)
        self.assertTrue(response["ok"])
        session = response["session"]
        self.assertEqual(session["capabilities"], ["diagnostics.read"])
        self.assertNotIn(BOOTSTRAP, json.dumps(response))
        status, again = bootstrap(adapter, ["diagnostics.read"])
        self.assertEqual(status, 401)
        self.assertEqual(again["error"], "authentication_failed")

    def test_bootstrap_rejects_wider_scopes_and_duplicate_json_fields(self) -> None:
        adapter = make_adapter(caps={"diagnostics.read"})
        status, response = bootstrap(adapter, ["services.manage"])
        self.assertEqual(status, 401)
        self.assertEqual(response["error"], "authentication_failed")
        body = b'{"bootstrap_secret":"' + BOOTSTRAP.encode() + b'","bootstrap_secret":"x","capabilities":[]}'
        status, _headers, raw = adapter.handle(
            method="POST", path="/api/v1/session", headers=headers_for(body), body=body)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw)["error"], "invalid_json")

    def test_authenticated_read_operation_dispatches_shared_service(self) -> None:
        dispatch = Mock(return_value={"ok": True, "api_version": 1,
                                      "request_id": "request-1234", "data": {"state": "ready"}})
        adapter = make_adapter(dispatcher=dispatch)
        _status, issued = bootstrap(adapter, ["diagnostics.read"])
        session = issued["session"]
        payload = {"api_version": 1, "request_id": "request-1234",
                   "operation": "ssh.inspect", "args": {}}
        body = payload_bytes(payload)
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}")
        status, _response_headers, raw = adapter.handle(
            method="POST", path="/api/v1/operations", headers=headers, body=body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["data"]["state"], "ready")
        dispatch.assert_called_once_with(payload, caller="local_cli", env=adapter._env)

    def test_scope_denial_and_csrf_rejection_happen_before_dispatch(self) -> None:
        dispatch = Mock()
        adapter = make_adapter(dispatcher=dispatch, caps={"diagnostics.read"})
        _status, issued = bootstrap(adapter, ["diagnostics.read"])
        session = issued["session"]
        payload = {"api_version": 1, "request_id": "request-1234",
                   "operation": "ssh.service.stop", "args": {"confirmed": True}}
        body = payload_bytes(payload)
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                              **{"X-Ternuxx-CSRF": session["csrf_token"],
                                 "Idempotency-Key": "mutation-key-0001"})
        status, _h, response = adapter.handle(method="POST", path="/api/v1/operations",
                                              headers=headers, body=body)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(response)["error"], "permission_denied")
        dispatch.assert_not_called()

        adapter = make_adapter(dispatcher=dispatch)
        _status, issued = bootstrap(adapter, ["services.manage"])
        session = issued["session"]
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                              **{"Idempotency-Key": "mutation-key-0001"})
        status, _h, response = adapter.handle(method="POST", path="/api/v1/operations",
                                              headers=headers, body=body)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(response)["error"], "csrf_rejected")
        dispatch.assert_not_called()

    def test_mutation_transport_defaults_disabled(self) -> None:
        dispatch = Mock()
        adapter = make_adapter(dispatcher=dispatch, allow_mutations=True)
        _status, issued = bootstrap(adapter, ["services.manage"])
        session = issued["session"]
        payload = {"api_version": 1, "request_id": "request-1234",
                   "operation": "ssh.service.stop", "args": {"confirmed": True}}
        body = payload_bytes(payload)
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                              **{"X-Ternuxx-CSRF": session["csrf_token"],
                                 "Idempotency-Key": "mutation-key-0001"})
        status, _h, response = adapter.handle(method="POST", path="/api/v1/operations",
                                              headers=headers, body=body)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(response)["error"], "mutation_transport_disabled")
        dispatch.assert_not_called()

    def test_new_proot_launch_and_shortcut_apply_remain_mutations(self) -> None:
        self.assertIn("proot.app.launch", management_sessions.MUTATING_OPERATIONS)
        self.assertIn("proot.shortcuts.apply", management_sessions.MUTATING_OPERATIONS)
        self.assertIn("proot.shortcuts.list", management_sessions.READ_ONLY_OPERATIONS)
        self.assertIn("proot.shortcuts.preview", management_sessions.READ_ONLY_OPERATIONS)
        for operation, capability, args in (
            ("proot.app.launch", "applications.launch", {"app_id": "files"}),
            ("proot.shortcuts.apply", "applications.manage", {
                "action": "remove", "app_id": "files", "confirmed": True, "plan_id": "a" * 24,
            }),
        ):
            dispatch = Mock()
            adapter = make_adapter(dispatcher=dispatch, caps={capability}, allow_mutations=False)
            _status, issued = bootstrap(adapter, [capability])
            session = issued["session"]
            payload = {"api_version": 1, "request_id": "request-1234",
                       "operation": operation, "args": args}
            body = payload_bytes(payload)
            headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                                  **{"X-Ternuxx-CSRF": session["csrf_token"],
                                     "Idempotency-Key": "mutation-key-0012"})
            status, _h, response = adapter.handle(method="POST", path="/api/v1/operations",
                                                  headers=headers, body=body)
            self.assertEqual(status, 403)
            self.assertEqual(json.loads(response)["error"], "mutation_transport_disabled")
            dispatch.assert_not_called()

    def test_mutation_idempotency_replays_and_rejects_key_reuse(self) -> None:
        dispatch = Mock(return_value={"ok": True, "api_version": 1,
                                      "request_id": "request-1234", "data": {"started": True}})
        with tempfile.TemporaryDirectory(prefix="ternuxx-http-store-") as temp:
            home = Path(temp) / "home"
            home.mkdir(mode=0o700)
            state_dir = home / ".state"
            state_dir.mkdir(mode=0o700)
            store = management_request_store.ManagementRequestStore(home=home, state_dir=state_dir)
            adapter = make_adapter(dispatcher=dispatch, allow_mutations=True, request_store=store)
            self._assert_mutation_idempotency(adapter, dispatch)

    def _assert_mutation_idempotency(self, adapter, dispatch):
        _status, issued = bootstrap(adapter, ["services.manage"])
        session = issued["session"]
        payload = {"api_version": 1, "request_id": "request-1234",
                   "operation": "ssh.service.start", "args": {"confirmed": True}}
        body = payload_bytes(payload)
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                              **{"X-Ternuxx-CSRF": session["csrf_token"],
                                 "Idempotency-Key": "mutation-key-0001"})
        first = adapter.handle(method="POST", path="/api/v1/operations", headers=headers, body=body)
        replay = adapter.handle(method="POST", path="/api/v1/operations", headers=headers, body=body)
        self.assertEqual(first[0], 200)
        self.assertEqual(replay[0], 409)
        self.assertEqual(json.loads(replay[2])["error"], "request_already_completed")
        dispatch.assert_called_once()

        changed = {**payload, "args": {"confirmed": False}}
        changed_body = payload_bytes(changed)
        changed_headers = headers_for(changed_body, Authorization=f"Bearer {session['bearer_token']}",
                                      **{"X-Ternuxx-CSRF": session["csrf_token"],
                                         "Idempotency-Key": "mutation-key-0001"})
        status, _h, response = adapter.handle(method="POST", path="/api/v1/operations",
                                              headers=changed_headers, body=changed_body)
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(response)["error"], "idempotency_conflict")
        dispatch.assert_called_once()

    def test_revoke_requires_token_and_csrf_and_invalidates_session(self) -> None:
        adapter = make_adapter()
        _status, issued = bootstrap(adapter, ["diagnostics.read"])
        session = issued["session"]
        body = b"{}"
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}")
        status, _h, _response = adapter.handle(method="POST", path="/api/v1/session/revoke",
                                              headers=headers, body=body)
        self.assertEqual(status, 401)
        headers["X-Ternuxx-CSRF"] = session["csrf_token"]
        status, _h, response = adapter.handle(method="POST", path="/api/v1/session/revoke",
                                              headers=headers, body=body)
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(response)["revoked"])

    def test_bad_origin_length_transfer_encoding_and_route_rejected(self) -> None:
        adapter = make_adapter()
        body = b"{}"
        invalid = [
            (headers_for(body, **{"Origin": "http://evil.example"}), 403),
            ({**headers_for(body), "Content-Length": "99"}, 400),
            ({**headers_for(body), "Transfer-Encoding": "chunked"}, 400),
        ]
        for headers, expected in invalid:
            with self.subTest(headers=headers):
                status, _h, _raw = adapter.handle(method="POST", path="/api/v1/session",
                                                 headers=headers, body=body)
                self.assertEqual(status, expected)
        status, _h, response = adapter.handle(
            method="POST", path="/api/v1/operations?x=1", headers=headers_for(body), body=body)
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(response)["error"], "route_not_found")


if __name__ == "__main__":
    unittest.main()
