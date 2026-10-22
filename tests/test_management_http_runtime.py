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
    def test_web_ssh_help_matches_publickey_only_service_policy(self) -> None:
        ui = (ROOT / "lib" / "management_web_ui.html").read_text(encoding="utf-8")
        self.assertIn("public-key login only", ui)
        self.assertIn("password login is disabled", ui)
        self.assertNotIn("Keep password recovery", ui)

    def test_web_resource_detail_uses_actions_instead_of_duplicate_capability_lists(self) -> None:
        ui = (ROOT / "lib" / "management_web_ui.html").read_text()
        self.assertIn('id="resource-actions"', ui)
        self.assertNotIn('Supported capabilities (', ui)
        self.assertNotIn('Planned capabilities (', ui)
        self.assertIn("Technical API response", ui)

    def test_bootstrap_secret_clipboard_copy_is_stdin_only_and_silent(self) -> None:
        completed = type("Completed", (), {"returncode": 0})()
        with patch.object(management_http_runtime.shutil, "which", return_value="/usr/bin/termux-clipboard-set"), \
             patch.object(management_http_runtime.subprocess, "run", return_value=completed) as run:
            self.assertTrue(management_http_runtime.copy_bootstrap_secret("one-time-private-secret"))
        args, kwargs = run.call_args
        self.assertEqual(args, (["/usr/bin/termux-clipboard-set"],))
        self.assertEqual(kwargs["input"], "one-time-private-secret")
        self.assertEqual(kwargs["stdout"], management_http_runtime.subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], management_http_runtime.subprocess.DEVNULL)
        self.assertNotIn("one-time-private-secret", repr(args))

    def test_default_clipboard_failure_stops_without_disclosing_secret(self) -> None:
        err = io.StringIO()
        err.isatty = lambda: True
        server = type("Server", (), {"port": 8765, "start": lambda self: None,
                                    "close": lambda self, **kwargs: True})()
        with patch.object(management_http_runtime.management_sessions, "new_bootstrap_secret", return_value=SECRET), \
             patch.object(management_http_runtime, "build_server", return_value=server), \
             patch.object(management_http_runtime, "copy_bootstrap_secret", return_value=False), \
             patch.object(management_http_runtime.sys, "stderr", err), \
             patch.object(management_http_runtime.signal, "signal"), \
             patch.object(management_http_runtime.threading, "Event") as event:
            self.assertEqual(management_http_runtime.main(["--port", "8765", "--web", "--browser", "android"]), 1)
        self.assertNotIn(SECRET, err.getvalue())
        self.assertIn("Clipboard copy failed", err.getvalue())
        event.return_value.wait.assert_not_called()

    def test_browser_detection_reads_rootfs_without_entering_guest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "var/lib/proot-distro/containers/debian/rootfs"
            (root / "etc").mkdir(parents=True)
            (root / "etc/passwd").write_text("sbj:x:1000:1000::/home/sbj:/bin/bash\n")
            (root / "usr/bin").mkdir(parents=True)
            browser = root / "usr/bin/firefox-esr"
            browser.write_text("#!/bin/sh\n")
            browser.chmod(0o755)
            with patch.object(management_http_runtime.shutil, "which", return_value="/fixture/proot-distro"), \
                 patch.object(management_http_runtime.subprocess, "run", side_effect=AssertionError("detection must not log in")):
                self.assertEqual(management_http_runtime.detect_proot_browser({"PREFIX": directory}),
                                 management_http_runtime.PROOT_BROWSER)
                browser.unlink()
                (root / "usr/lib").mkdir()
                target = root / "usr/lib/browser"
                target.write_text("#!/bin/sh\n")
                target.chmod(0o755)
                browser.symlink_to("../lib/browser")
                self.assertEqual(management_http_runtime.detect_proot_browser({"PREFIX": directory}),
                                 management_http_runtime.PROOT_BROWSER)
                browser.unlink()
                browser.symlink_to(Path(directory) / "outside-browser")
                self.assertIsNone(management_http_runtime.detect_proot_browser({"PREFIX": directory}))

    def test_interactive_auto_choices_resolve_to_a_launch_target(self) -> None:
        native = ("/native/firefox", "Firefox")
        proot = ("/guest/firefox-esr", "Firefox ESR")
        for text in ("4\n", "auto\n", "\n"):
            stream = io.StringIO(text)
            stream.isatty = lambda: True
            with self.subTest(text=text):
                self.assertEqual(management_http_runtime.choose_browser(
                    "choose", native=native, proot=proot,
                    stdin=stream, stderr=io.StringIO()), "native")
        stream = io.StringIO("3\n")
        stream.isatty = lambda: True
        self.assertEqual(management_http_runtime.choose_browser(
            "choose", native=None, proot=proot,
            stdin=stream, stderr=io.StringIO()), "proot")

    def test_failed_browser_and_clipboard_handoffs_stop_or_use_explicit_fallback(self) -> None:
        for explicit in (False, True):
            err = io.StringIO()
            err.isatty = lambda: True
            server = type("Server", (), {"port": 8765, "start": lambda self: None,
                                        "close": lambda self, **kwargs: True})()
            with self.subTest(explicit=explicit), \
                 patch.object(management_http_runtime, "detect_native_browser",
                              return_value=("/native/firefox", "Firefox")), \
                 patch.object(management_http_runtime.management_sessions, "new_bootstrap_secret", return_value=SECRET), \
                 patch.object(management_http_runtime, "build_server", return_value=server) as build, \
                 patch.object(management_http_runtime, "copy_bootstrap_secret", return_value=False), \
                 patch.object(management_http_runtime, "open_browser", return_value=(False, False)), \
                 patch.object(management_http_runtime.sys, "stderr", err), \
                 patch.object(management_http_runtime.signal, "signal"), \
                 patch.object(management_http_runtime.threading, "Event") as event:
                argv = ["--port", "8765", "--web", "--browser", "native"]
                if explicit:
                    argv.append("--show-secret-on-clipboard-failure")
                self.assertEqual(management_http_runtime.main(argv), 0 if explicit else 1)
                self.assertEqual(SECRET in err.getvalue(), explicit)
                self.assertEqual(build.call_args.kwargs["env"]["TERNUXX_WEB_MODE"], "1")
                self.assertEqual(event.return_value.wait.called, explicit)

    def test_readonly_command_cannot_inherit_web_mutation_mode(self) -> None:
        err = io.StringIO()
        err.isatty = lambda: True
        server = type("Server", (), {"port": 8765, "start": lambda self: None,
                                    "close": lambda self, **kwargs: True})()
        with patch.dict(management_http_runtime.os.environ, {"TERNUXX_WEB_MODE": "1"}), (
             patch.object(management_http_runtime, "build_server", return_value=server)) as build, (
             patch.object(management_http_runtime.sys, "stderr", err)), (
             patch.object(management_http_runtime.signal, "signal")), (
             patch.object(management_http_runtime.threading, "Event")):
            self.assertEqual(management_http_runtime.main(["--port", "8765"]), 0)
            self.assertEqual(build.call_args.kwargs["env"]["TERNUXX_WEB_MODE"], "0")
            self.assertEqual(management_http_runtime.os.environ["TERNUXX_WEB_MODE"], "1")

    def test_clipboard_copy_failure_is_reported_as_boolean_only(self) -> None:
        with patch.object(management_http_runtime.shutil, "which", return_value=None):
            self.assertFalse(management_http_runtime.copy_bootstrap_secret("secret"))

    def test_web_page_has_compact_portfolio_branding(self) -> None:
        page = (ROOT / "lib" / "management_web_ui.html").read_text(encoding="utf-8")
        self.assertIn("Workstation in your pocket — by Sobuj Miah", page)
        self.assertIn('href="https://soobujmiah.github.io/"', page)
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
        self.assertNotIn("applications.launch", server.adapter.sessions._bootstrap_capabilities)
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

    def test_web_ssh_key_inventory_control_uses_its_separate_capability(self) -> None:
        ui = (ROOT / "lib" / "management_web_ui.html").read_text()
        self.assertIn("ssh.credentials.read", ui)
        self.assertIn("View shared SSH key fingerprints", ui)
        self.assertIn('b.onclick=()=>run("ssh.keys.list")', ui)

    def test_web_mode_exposes_scoped_desktop_monitoring_and_managed_ssh_8023_mutations(self) -> None:
        env = dict(self.env, TERNUXX_WEB_MODE="1")
        Path(env["TERNUXX_STATE_DIR"]).mkdir(parents=True, mode=0o700)
        Path(env["TERNUXX_STATE_DIR"]).chmod(0o700)
        with patch.object(management_http_runtime.management_service, "dispatch") as dispatch:
            server = management_http_runtime.build_server(
                port=0, bootstrap_secret=SECRET, env=env)
            try:
                self.assertTrue(server.adapter._allow_mutations)
                self.assertTrue(server.adapter._request_store.durable)
                self.assertEqual(server.adapter.sessions._bootstrap_capabilities,
                                 management_http_runtime.WEB_CAPABILITIES)
                session = server.adapter.sessions.exchange_bootstrap(
                    SECRET, sorted(management_http_runtime.WEB_CAPABILITIES))
                host = "127.0.0.1:%s" % server.port

                def post(operation: str, request_id: str, key: str, args: dict[str, object], *, csrf: bool = True):
                    body = json.dumps({"api_version": 1, "request_id": request_id,
                                       "operation": operation, "args": args}).encode()
                    headers = {"Host": host, "Origin": "http://" + host,
                               "Content-Type": "application/json", "Content-Length": str(len(body)),
                               "Authorization": "Bearer " + session.bearer_token,
                               "Idempotency-Key": key}
                    if csrf:
                        headers["X-Ternuxx-CSRF"] = session.csrf_token
                    return server.adapter.handle(method="POST", path="/api/v1/operations",
                                                 headers=headers, body=body)

                dispatch.return_value = {"api_version": 1, "request_id": "web-start-result-1",
                    "ok": True, "operation": "desktop.start", "data": {"state": "running"}}
                status, _headers, response = post("desktop.start", "web-start-request-01",
                    "web-start-key-00000001", {"display": ":1"})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "desktop.start")
                dispatch.assert_called_once()

                status, _headers, response = post("desktop.stop", "web-stop-request-001",
                    "web-stop-key-000000001", {}, csrf=False)
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(response)["error"], "csrf_rejected")
                self.assertEqual(dispatch.call_count, 1)

                dispatch.return_value = {"api_version": 1, "request_id": "web-ssh-preview-001",
                    "ok": True, "operation": "ssh.service.stop", "data": {
                        "service_id": "ternuxx-sshd", "current_status": "running",
                        "requires_confirmation": True, "plan_id": "a" * 64,
                        "impact": "Stops only the managed SSH unit."}}
                status, _headers, response = post("ssh.service.stop", "web-ssh-request-001",
                    "web-ssh-key-000000001", {"confirmed": False, "plan_id": None})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "ssh.service.stop")
                self.assertEqual(dispatch.call_count, 2)

                status, _headers, response = post("ssh.service.deploy", "web-ssh-deploy-001",
                    "web-ssh-deploy-key-0001", {"confirmed": False, "plan_id": None})
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(response)["error"], "permission_denied")
                self.assertEqual(dispatch.call_count, 2)

                dispatch.return_value = {"api_version": 1, "request_id": "web-history-read-001",
                    "ok": True, "operation": "recovery.status", "data": {
                        "operations": [{"kind": "service.start", "status": "complete"}],
                        "unresolved_count": 0, "read_only": True}}
                status, _headers, response = post("recovery.status", "web-history-request-01",
                    "web-history-key-00001", {})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "recovery.status")
                self.assertEqual(dispatch.call_count, 3)

                dispatch.return_value = {"api_version": 1, "request_id": "web-proot-launch-001",
                    "ok": True, "operation": "proot.app.launch", "data": {"app_id": "files"}}
                status, _headers, response = post("proot.app.launch", "web-proot-launch-01",
                    "web-proot-launch-key1", {"app_id": "files"})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "proot.app.launch")
                self.assertEqual(dispatch.call_count, 4)

                status, _headers, response = post("proot.app.launch", "web-proot-desktop-01",
                    "web-proot-desktop-key1", {"desktop_id": "unreviewed.desktop"})
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(response)["error"], "named_app_only")
                self.assertEqual(dispatch.call_count, 4)

                status, _headers, response = post("proot.start", "web-proot-session-01",
                    "web-proot-session-key1", {"profile": "debian-interactive",
                                                "command": "/bin/sh -c id",
                                                "argv": ["/bin/sh", "-c", "id"],
                                                "rootfs": "/data/local/tmp/rootfs",
                                                "user": "root"})
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(response)["error"], "proot_profile_restricted")
                self.assertEqual(dispatch.call_count, 4)

                dispatch.return_value = {"api_version": 1, "request_id": "web-probe-start-001",
                    "ok": True, "operation": "proot.start", "data": {
                        "profile": "isolated-probe", "state": "running", "ownership": "ternuxx_verified"}}
                status, _headers, response = post("proot.start", "web-probe-start-001",
                    "web-probe-start-key-0001", {"profile": "isolated-probe", "confirmed": True,
                                                  "plan_id": "plan-" + "a" * 64, "timeout_seconds": 300})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "proot.start")
                self.assertEqual(dispatch.call_count, 5)

                dispatch.return_value = {"api_version": 1, "request_id": "web-probe-stop-001",
                    "ok": True, "operation": "proot.stop", "data": {"stopped": True}}
                status, _headers, response = post("proot.stop", "web-probe-stop-request-01",
                    "web-probe-stop-key-0001", {"session_id": "proot-" + "a" * 32,
                                                  "confirmed": True, "plan_id": "plan-" + "b" * 64})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "proot.stop")
                self.assertEqual(dispatch.call_count, 6)

                dispatch.return_value = {"api_version": 1, "request_id": "web-shortcut-preview-1",
                    "ok": True, "operation": "proot.shortcuts.preview", "data": {
                        "plan_id": "b" * 24, "changed": True}}
                status, _headers, response = post("proot.shortcuts.preview", "web-shortcut-preview-1",
                    "web-shortcut-preview-key1", {"action": "add", "app_id": "files"})
                self.assertEqual(status, 200, response)
                self.assertEqual(dispatch.call_count, 7)

                dispatch.return_value = {"api_version": 1, "request_id": "web-shortcut-apply-01",
                    "ok": True, "operation": "proot.shortcuts.apply", "data": {"status": "complete"}}
                status, _headers, response = post("proot.shortcuts.apply", "web-shortcut-apply-001",
                    "web-shortcut-apply-key1", {"action": "add", "app_id": "files",
                                                "confirmed": True, "plan_id": "b" * 24})
                self.assertEqual(status, 200, response)
                self.assertEqual(json.loads(response)["operation"], "proot.shortcuts.apply")
                self.assertEqual(dispatch.call_count, 8)

                status, _headers, response = post("proot.shortcuts.sync", "web-shortcut-sync-001",
                    "web-shortcut-sync-key1", {})
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(response)["error"], "permission_denied")
                self.assertEqual(dispatch.call_count, 8)

                dispatch.return_value = {"api_version": 1, "request_id": "web-failure-result-1",
                    "ok": False, "error": {"code": "desktop_operation_failed", "message": "redacted"}}
                status, _headers, response = post("desktop.restart", "web-restart-request-01",
                    "web-restart-key-0000001", {"display": ":1"})
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(response)["error"]["code"], "desktop_operation_failed")
                self.assertNotIn("redacted", response.decode())
            finally:
                self.assertTrue(server.close(grace_seconds=1))

        page = (ROOT / "lib" / "management_web_ui.html").read_text()
        self.assertIn('id="categories"', page)
        self.assertIn('id="search"', page)
        self.assertIn('id="resource-detail"', page)
        self.assertIn("window.confirm", page)
        self.assertIn("Idempotency-Key", page)
        self.assertIn("desktop.monitor.manage", page)
        self.assertIn("desktop.manage", page)
        self.assertIn("ssh.managed.lifecycle", page)
        self.assertIn("network.ssh.managed-8023", page)
        self.assertIn("Recent management activity", page)
        self.assertIn("Load recent activity", page)
        self.assertIn('run("recovery.status")', page)
        self.assertIn('id="logs-panel"', page)
        self.assertIn("management.logs.read", page)
        self.assertIn('id="monitor-panel" hidden', page)
        self.assertIn('monitorPanel.hidden=r?.id!=="native.gui.activity-monitor"', page)
        self.assertIn("grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))", page)
        self.assertIn("Technical API response", page)
        self.assertNotIn("network.ssh.manual-8022", page.split("manageSsh(operation)", 1)[-1].split("function drawCategories", 1)[0])
        self.assertIn("applications.launch", page)
        self.assertIn("applications.shortcuts.manage", page)
        self.assertIn("cron.manage", page)
        self.assertIn("proot.session.manage", page)
        self.assertIn("proot.recovery.inspect", page)
        self.assertIn('run("proot.start.preview",{profile:"isolated-probe"})', page)
        self.assertIn('run("proot.stop.preview",{session_id:item.session_id})', page)
        self.assertIn('run("cron.jobs.mutation.preview",args)', page)
        self.assertIn('run("cron.jobs.mutation.apply",{plan_id:plan.plan_id,confirmed:true})', page)
        self.assertIn('run("proot.shortcuts.preview",{action,app_id:select.value})', page)
        self.assertIn('run("proot.shortcuts.apply",{action,app_id:select.value,confirmed:true,plan_id:data.plan_id})', page)
        self.assertIn('run("proot.shortcuts.list")', page)
        self.assertIn('run("proot.app.launch",chosen?{app_id:select.value,display:chosen}:{app_id:select.value})', page)
        self.assertIn("Remove owned shortcut", page)
        self.assertIn("proot.shortcuts.apply", page)
        self.assertIn("Use an X11 display like :1", page)
        self.assertIn("Launch named PRoot app", page)
        self.assertIn("availability unverified", page)

    def test_web_console_has_bounded_mobile_layout_and_touch_navigation_rules(self) -> None:
        page = (ROOT / "lib" / "management_web_ui.html").read_text()
        self.assertIn('<meta name="viewport" content="width=device-width,initial-scale=1">', page)
        self.assertIn('@media(max-width:760px)', page)
        self.assertIn('grid-template-columns:minmax(0,1fr)', page)
        self.assertIn('max-width:100%', page)
        self.assertIn('min-height:44px', page)
        self.assertIn('overscroll-behavior-inline:contain', page)
        self.assertIn('max-width:min(42vw,17rem);white-space:normal', page)
        self.assertIn('window.addEventListener("resize",revealActiveCategory', page)
        self.assertIn('@media(max-width:380px)', page)
        self.assertIn('font:15px system-ui,sans-serif', page)
        for handler in ('$("#connect").onclick=connect', '$("#disconnect").onclick=',
                        '$("#refresh").onclick=', '$("#search").oninput=drawResources',
                        '$("#status").onchange=drawResources', '$("#save-monitor").onclick='):
            self.assertIn(handler, page)
        self.assertIn('document.querySelectorAll("[data-op]").forEach(button=>button.onclick=()=>run(button.dataset.op))', page)
        self.assertIn('card.onclick=()=>selectResource(resource)', page)
        self.assertIn('automation.cron-registry', page)
        self.assertIn('b.textContent="List saved jobs"', page)
        self.assertIn('b.onclick=()=>run("cron.jobs.list")', page)
        self.assertIn('b.onclick=()=>run("cron.executions.list",{limit:20})', page)
        self.assertIn('b.onclick=()=>run("timezone.list")', page)
        self.assertIn("timezone.status", page)
        self.assertNotIn("timezone.set", page)

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

    def test_web_root_serves_the_real_category_console_with_same_origin_policy(self) -> None:
        env = dict(self.env, TERNUXX_WEB_MODE="1")
        Path(env["TERNUXX_STATE_DIR"]).mkdir(parents=True, mode=0o700)
        Path(env["TERNUXX_STATE_DIR"]).chmod(0o700)
        server = management_http_runtime.build_server(port=0, bootstrap_secret=SECRET, env=env)
        server.start()
        connection = http.client.HTTPConnection(*server.address, timeout=3)
        host = f"127.0.0.1:{server.port}"
        try:
            connection.request("GET", "/", headers={"Host": host, "Origin": "http://" + host})
            response = connection.getresponse()
            page = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Content-Type"), "text/html; charset=utf-8")
            self.assertIn('id="categories"', page)
            self.assertIn('id="resource-list"', page)
            self.assertIn('id="resource-detail"', page)
            connection.close()
            connection = http.client.HTTPConnection(*server.address, timeout=3)
            connection.request("GET", "/", headers={"Host": host, "Origin": "http://untrusted.invalid"})
            rejected = connection.getresponse()
            self.assertEqual(rejected.status, 403)
        finally:
            connection.close()
            self.assertTrue(server.close(grace_seconds=3))

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
