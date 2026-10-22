"""In-process contract tests for authenticated management HTTP request routing."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_http_adapter  # noqa: E402
import management_service  # noqa: E402
import management_request_store  # noqa: E402
import management_sessions  # noqa: E402
import proot_sessions  # noqa: E402


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
        bootstrap_capabilities=caps if caps is not None else {"diagnostics.read", "ssh.managed.lifecycle"},
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
    def test_web_terminal_preserves_63_bit_generation_through_json(self):
        generation=(1 << 62) + 12345
        session_id="proot-" + "a"*32
        lease={"session_id":session_id,"profile":"debian-interactive",
               "state":"running","generation":generation,"attachment_id":"attachment-test"}
        adapter=make_adapter()
        client=Mock()
        client.request.side_effect=lambda operation, **kwargs: (
            {"ok":True,"result":lease} if operation=="terminal.start"
            else {"ok":True,"columns":100,"rows":30})
        def dispatch(operation, **values):
            payload={"operation":operation,"request_id":"request-1234",
                     "session_id":values.get("session_id"),"generation":values.get("generation"),
                     "attachment_id":values.get("attachment_id"),
                     "channel_ticket":values.get("channel_ticket"),"args":values.get("args",{})}
            status,_headers,raw=adapter._terminal_dispatch({"origin":ORIGIN},payload,"web-session")
            return status,json.loads(raw)
        with patch.object(management_http_adapter.terminal_broker,"UnixBrokerClient",return_value=client):
            status,started=dispatch("terminal.start",args={"confirmed":True,"plan_id":"plan-"+"b"*64})
            self.assertEqual(status,200)
            status,attached=dispatch("terminal.attach",session_id=session_id,
                                     channel_ticket=started["data"]["channel_ticket"])
            self.assertEqual(status,200)
            self.assertEqual(attached["data"]["generation"],str(generation))
            self.assertIsInstance(attached["data"]["generation"],str)
            status,resized=dispatch("terminal.resize",session_id=session_id,
                                    generation=attached["data"]["generation"],
                                    attachment_id=lease["attachment_id"],
                                    args={"columns":100,"rows":30})
            self.assertEqual(status,200)
            self.assertTrue(resized["ok"])
            self.assertEqual(client.request.call_args.kwargs["generation"],generation)
            for bad in (generation, str(generation+1), "0"+str(generation), str(1 << 63)):
                with self.subTest(bad=bad):
                    status,rejected=dispatch("terminal.resize",session_id=session_id,
                                             generation=bad,attachment_id=lease["attachment_id"],
                                             args={"columns":100,"rows":30})
                    self.assertIn(status,{400,403})
                    self.assertFalse(rejected["ok"])

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
        status, response = bootstrap(adapter, ["ssh.managed.lifecycle"])
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

    def test_web_can_inspect_optional_terminal_broker_status(self) -> None:
        dispatch = Mock(return_value={"ok": True, "api_version": 1,
                                      "request_id": "request-1234",
                                      "data": {"status": "not_running"}})
        adapter = make_adapter(dispatcher=dispatch, caps={"diagnostics.read"})
        _status, issued = bootstrap(adapter, ["diagnostics.read"])
        session = issued["session"]
        payload = {"api_version": 1, "request_id": "request-1234",
                   "operation": "terminal.broker.status", "args": {}}
        body = payload_bytes(payload)
        headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}")
        status, _response_headers, raw = adapter.handle(
            method="POST", path="/api/v1/operations", headers=headers, body=body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["data"]["status"], "not_running")
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
        _status, issued = bootstrap(adapter, ["ssh.managed.lifecycle"])
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
        _status, issued = bootstrap(adapter, ["ssh.managed.lifecycle"])
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
            ("proot.shortcuts.apply", "applications.shortcuts.manage", {
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

    def test_web_recovery_reconcile_requires_scoped_preview_and_confirmed_idempotent_apply(self) -> None:
        dispatch = Mock(side_effect=[
            {"ok": True, "api_version": 1, "request_id": "request-1234",
             "data": {"action": "mark_exited_without_signal", "confirmation_required": True,
                      "signal_allowed": False, "plan_id": "plan-" + "b" * 64,
                      "evidence": "process_absent"}},
            {"ok": True, "api_version": 1, "request_id": "request-1235",
             "data": {"state": "stopped", "signal_sent": False}},
        ])
        with tempfile.TemporaryDirectory(prefix="ternuxx-http-reconcile-") as temp:
            home = Path(temp) / "home"
            home.mkdir(mode=0o700)
            state_dir = home / ".state"
            state_dir.mkdir(mode=0o700)
            store = management_request_store.ManagementRequestStore(home=home, state_dir=state_dir)
            capabilities = {"diagnostics.read", "proot.session.manage"}
            adapter = make_adapter(dispatcher=dispatch, caps=capabilities,
                                   allow_mutations=True, request_store=store)
            _status, issued = bootstrap(adapter, sorted(capabilities))
            session = issued["session"]

            preview = {"api_version": 1, "request_id": "request-1234",
                       "operation": "proot.recovery.reconcile.preview",
                       "args": {"session_id": "proot-" + "a" * 32}}
            preview_body = payload_bytes(preview)
            status, _headers, raw = adapter.handle(
                method="POST", path="/api/v1/operations",
                headers=headers_for(preview_body, Authorization=f"Bearer {session['bearer_token']}"),
                body=preview_body)
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(raw)["data"]["signal_allowed"] is False)

            apply = {"api_version": 1, "request_id": "request-1235",
                     "operation": "proot.recovery.reconcile",
                     "args": {"session_id": "proot-" + "a" * 32, "confirmed": True,
                              "plan_id": "plan-" + "b" * 64}}
            apply_body = payload_bytes(apply)
            apply_headers = headers_for(
                apply_body, Authorization=f"Bearer {session['bearer_token']}",
                **{"X-Ternuxx-CSRF": session["csrf_token"],
                   "Idempotency-Key": "mutation-key-0004"})
            status, _headers, raw = adapter.handle(
                method="POST", path="/api/v1/operations", headers=apply_headers, body=apply_body)
            self.assertEqual(status, 200)
            self.assertFalse(json.loads(raw)["data"]["signal_sent"])
            self.assertEqual(dispatch.call_count, 2)
            self.assertEqual(dispatch.call_args_list[1].kwargs["caller"], "local_cli")

    def test_web_recovery_reconcile_runs_shared_service_on_private_dead_session_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-web-reconcile-live-") as temp:
            base = Path(temp)
            home = base / "home"
            home.mkdir(mode=0o700)
            state_dir = home / ".local/share/ternuxx"
            state_dir.mkdir(parents=True, mode=0o700)
            rootfs = base / "fixture-rootfs"
            rootfs.mkdir(mode=0o700)
            launcher = base / "fixture-proot-distro"
            launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            launcher.chmod(0o700)
            state_root, registry_path, _lock_path = proot_sessions._paths(state_dir, create=True)
            session_id = "proot-" + "c" * 32
            pid = 2_000_000_000
            profile = proot_sessions.PROFILES["isolated-probe"]
            marker = "TERNUXX_PROOT_SESSION=" + "d" * 32
            record = {
                "schema_version": proot_sessions.SCHEMA,
                "session_id": session_id,
                "profile": "isolated-probe",
                "profile_version": 1,
                "purpose": profile["purpose"],
                "mode": profile["mode"],
                "rootfs": str(rootfs),
                "rootfs_device": rootfs.stat().st_dev,
                "rootfs_inode": rootfs.stat().st_ino,
                "launcher": str(launcher),
                "launcher_device": launcher.stat().st_dev,
                "launcher_inode": launcher.stat().st_ino,
                "pid": pid,
                "process_start": "fixture-process-that-does-not-exist",
                "process_group": pid,
                "marker": marker,
                "expected_argv": [str(launcher), "login", "--minimal", "debian", "--",
                                  "/usr/bin/env", marker, "/bin/sleep", "300"],
                "working_directory": "guest-default",
                "environment_profile": "isolated-no-host-home-or-display",
                "created_at": "2026-10-22T00:00:00+00:00",
                "state": "running",
                "last_verified_at": None,
                "last_exit_code": None,
                "transitions": [],
            }
            proot_sessions._write_registry(state_root, registry_path, [record])
            env = {
                "TERMUX_VERSION": "test",
                "PREFIX": "/data/data/com.termux/files/usr",
                "HOME": str(home),
                "TERNUXX_STATE_DIR": str(state_dir),
            }
            store = management_request_store.ManagementRequestStore(home=home, state_dir=state_dir)
            adapter = management_http_adapter.ManagementHTTPAdapter(
                expected_origin=ORIGIN,
                bootstrap_secret=BOOTSTRAP,
                bootstrap_capabilities={"diagnostics.read", "proot.session.manage"},
                env=env,
                dispatcher=management_service.dispatch,
                allow_mutations=True,
                request_store=store,
            )
            _status, issued = bootstrap(adapter, ["diagnostics.read", "proot.session.manage"])
            session = issued["session"]
            session_args = {"session_id": session_id}
            preview = {"api_version": 1, "request_id": "request-1234",
                       "operation": "proot.recovery.reconcile.preview", "args": session_args}
            preview_body = payload_bytes(preview)
            status, _headers, raw = adapter.handle(
                method="POST", path="/api/v1/operations",
                headers=headers_for(preview_body, Authorization=f"Bearer {session['bearer_token']}"),
                body=preview_body)
            self.assertEqual(status, 200)
            preview_result = json.loads(raw)
            self.assertTrue(preview_result["ok"])
            self.assertEqual(preview_result["data"]["action"], "mark_exited_without_signal")
            self.assertFalse(preview_result["data"]["signal_allowed"])

            apply = {"api_version": 1, "request_id": "request-1235",
                     "operation": "proot.recovery.reconcile",
                     "args": {"session_id": session_id, "confirmed": True,
                              "plan_id": preview_result["data"]["plan_id"]}}
            apply_body = payload_bytes(apply)
            apply_headers = headers_for(
                apply_body, Authorization=f"Bearer {session['bearer_token']}",
                **{"X-Ternuxx-CSRF": session["csrf_token"],
                   "Idempotency-Key": "mutation-key-0005"})
            status, _headers, raw = adapter.handle(
                method="POST", path="/api/v1/operations", headers=apply_headers, body=apply_body)
            self.assertEqual(status, 200)
            apply_result = json.loads(raw)
            self.assertTrue(apply_result["ok"])
            self.assertEqual(apply_result["data"]["state"], "stopped")
            self.assertFalse(apply_result["data"]["signal_sent"])
            self.assertEqual(
                proot_sessions.show_session(state_dir, session_id)["state"], "stopped")

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
        _status, issued = bootstrap(adapter, ["ssh.managed.lifecycle"])
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


    def test_terminal_http_route_requires_csrf_and_never_uses_generic_operations_route(self):
        dispatch = Mock()
        adapter = make_adapter(dispatcher=dispatch, caps={"proot.session.manage"})
        _status, issued = bootstrap(adapter, ["proot.session.manage"])
        session = issued["session"]
        body = payload_bytes({
            "operation": "terminal.start.preview", "request_id": "terminal-request-1",
            "session_id": None, "generation": None, "attachment_id": None,
            "channel_ticket": None, "args": {},
        })
        base = headers_for(body, Authorization=f"Bearer {session['bearer_token']}")
        status, _headers, raw = adapter.handle(method="POST", path="/api/v1/terminal",
                                               headers=base, body=body)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(raw)["error"], "csrf_rejected")
        base["X-Ternuxx-CSRF"] = session["csrf_token"]
        generic_body = payload_bytes({
            "api_version": 1, "request_id": "terminal-request-2",
            "operation": "terminal.start.preview", "args": {},
        })
        generic_headers = headers_for(generic_body, Authorization=f"Bearer {session['bearer_token']}",
                                      **{"X-Ternuxx-CSRF": session["csrf_token"]})
        status, _headers, raw = adapter.handle(method="POST", path="/api/v1/operations",
                                               headers=generic_headers, body=generic_body)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(raw)["error"], "terminal_channel_transport_required")
        dispatch.assert_not_called()

    def test_web_terminal_channel_ticket_is_single_use_and_bound_to_session_and_origin(self):
        adapter = make_adapter(caps={"diagnostics.read", "proot.session.manage"})
        _status, issued = bootstrap(adapter, ["diagnostics.read", "proot.session.manage"])
        session = issued["session"]
        session_id = "proot-" + "a" * 32
        lease = {"ok": True, "session_id": session_id, "generation": 17,
                 "attachment_id": "attach-" + "b" * 32, "writer_attached": True}
        broker = Mock()
        broker.request.side_effect = [
            lease,
            {"ok": True, "chunks": [], "next_sequence": 0, "truncated": False},
            {"ok": True, "session_id": session_id, "writer_attached": False,
             "session_closed": False},
        ]

        def call(operation, request_id, *, args=None, channel_ticket=None,
                 selected=session_id, generation=None, attachment_id=None,
                 origin=ORIGIN):
            value = {"operation": operation, "request_id": request_id,
                     "session_id": selected, "generation": generation,
                     "attachment_id": attachment_id, "channel_ticket": channel_ticket,
                     "args": args or {}}
            body = payload_bytes(value)
            headers = headers_for(body, Authorization=f"Bearer {session['bearer_token']}",
                                  **{"X-Ternuxx-CSRF": session["csrf_token"], "Origin": origin})
            return adapter.handle(method="POST", path="/api/v1/terminal",
                                  headers=headers, body=body)

        with patch.object(management_http_adapter.terminal_broker, "UnixBrokerClient",
                          return_value=broker):
            status, _h, raw = call("terminal.channel.issue", "terminal-issue-1")
            self.assertEqual(status, 200)
            grant = json.loads(raw)["data"]
            ticket = grant["channel_ticket"]
            status, _h, raw = call("terminal.attach", "terminal-attach-1",
                                  channel_ticket=ticket)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)["data"]["attachment_id"], lease["attachment_id"])
            self.assertEqual(json.loads(raw)["data"]["generation"], "17")
            status, _h, raw = call("terminal.attach", "terminal-replay-1",
                                  channel_ticket=ticket)
            self.assertEqual(status, 403)
            self.assertEqual(json.loads(raw)["error"], "terminal_channel_rejected")
            status, _h, raw = call("terminal.output", "terminal-output-1",
                                  args={"after_sequence": 0}, generation="17",
                                  attachment_id=lease["attachment_id"])
            self.assertEqual(status, 200)
            status, _h, raw = call("terminal.detach", "terminal-detach-1",
                                  generation="17", attachment_id=lease["attachment_id"])
            self.assertEqual(status, 200)
            self.assertEqual(broker.request.call_args_list[0].args, ("terminal.attach",))
            self.assertEqual(broker.request.call_args_list[1].args, ("terminal.output",))


if __name__ == "__main__":
    unittest.main()
