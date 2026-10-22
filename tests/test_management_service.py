"""Contract tests for the allowlisted local management application service."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_service  # noqa: E402
import operation_journal  # noqa: E402


NATIVE_ENV = {
    "TERMUX_VERSION": "test",
    "PREFIX": "/data/data/com.termux/files/usr",
    "HOME": "/tmp/home",
    "TERNUXX_STATE_DIR": "/tmp/home/.local/share/ternuxx",
}


def request(operation: object, args: object = None, api_version: int = 1) -> dict[str, object]:
    return {"api_version": api_version, "request_id": "request-12345678", "operation": operation,
            "args": {} if args is None else args}


class ManagementServiceTests(unittest.TestCase):
    def test_ssh_key_inventory_is_a_separate_read_only_shared_operation(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="ssh-keys-read-") as temp:
            home = Path(temp)
            (home / ".ssh").mkdir(mode=0o700)
            expected = {"status": "missing", "keys": [], "key_count": 0}
            with patch.object(management_service.ssh_key_inventory, "list_managed_authorized_keys",
                              return_value=expected) as inventory:
                result = management_service.dispatch(
                    request("ssh.keys.list"), env={**NATIVE_ENV, "HOME": str(home)})
            inventory.assert_called_once_with(home=str(home))
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["status"], "missing")
        self.assertEqual(result["data"]["keys"], [])

    def test_ssh_key_enrollment_preview_and_apply_use_shared_confirmed_service(self) -> None:
        import os
        with tempfile.TemporaryDirectory(prefix="ssh-key-service-") as temp:
            home = Path(temp)
            (home / ".ssh").mkdir(mode=0o700)
            os.chown(home, os.getuid(), -1)
            os.chown(home / ".ssh", os.getuid(), -1)
            key_path = home / "test-key"
            generated = management_service.subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C",
                 "service-test", "-f", str(key_path)],
                capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(generated.returncode, 0)
            public_key = key_path.with_suffix(".pub").read_text(encoding="utf-8").strip()
            parsed = management_service.ssh_key_inventory._parse_line(public_key)
            env = {**NATIVE_ENV, "HOME": str(home),
                   "TERNUXX_STATE_DIR": str(home / ".local/share/ternuxx")}
            with patch.object(management_service.ssh_key_inventory, "list_managed_authorized_keys",
                              return_value={"authorized_keys_path_verified": True}):
                preview = management_service.dispatch(request("ssh.keys.add.preview", {
                    "public_key": public_key}), env=env)
                self.assertTrue(preview["ok"])
                self.assertEqual(preview["data"]["fingerprint"], parsed["fingerprint"])
                self.assertNotIn(public_key, repr(preview))
                applied = management_service.dispatch(request("ssh.keys.add.apply", {
                    "public_key": public_key, "confirmed": True,
                    "plan_id": preview["data"]["plan_id"]}), env=env)
            self.assertTrue(applied["ok"])
            self.assertEqual((home / ".ssh/authorized_keys").read_text(), public_key + "\n")
            self.assertEqual((home / ".ssh/authorized_keys").stat().st_mode & 0o777, 0o600)

    def test_ssh_key_rollback_uses_the_authorized_shared_service(self) -> None:
        import os
        with tempfile.TemporaryDirectory(prefix="ssh-key-rollback-service-") as temp:
            home = Path(temp)
            ssh = home / ".ssh"
            home.mkdir(mode=0o700, exist_ok=True)
            ssh.mkdir(mode=0o700)
            os.chown(home, os.getuid(), -1)
            os.chown(ssh, os.getuid(), -1)
            source = home / "test-key"
            generated = management_service.subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(source)],
                capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(generated.returncode, 0)
            public_key = source.with_suffix(".pub").read_text(encoding="utf-8").strip()
            env = {**NATIVE_ENV, "HOME": str(home)}
            with patch.object(management_service.ssh_key_inventory, "list_managed_authorized_keys",
                              return_value={"authorized_keys_path_verified": True}):
                preview = management_service.dispatch(request("ssh.keys.add.preview", {
                    "public_key": public_key}), env=env)
                apply_result = management_service.dispatch(request("ssh.keys.add.apply", {
                    "public_key": public_key, "confirmed": True,
                    "plan_id": preview["data"]["plan_id"]}), env=env)
                self.assertTrue(apply_result["ok"])
                rollback_id = apply_result["data"]["rollback_id"]
                records = management_service.dispatch(request("ssh.keys.rollback.list"), env=env)
                self.assertTrue(records["ok"])
                self.assertEqual(records["data"]["count"], 1)
                self.assertNotIn(public_key, repr(records))
                rollback = management_service.dispatch(request("ssh.keys.rollback.preview", {
                    "rollback_id": rollback_id}), env=env)
                self.assertTrue(rollback["ok"])
                self.assertNotIn(public_key, repr(rollback))
                restored = management_service.dispatch(request("ssh.keys.rollback.apply", {
                    "rollback_id": rollback_id, "confirmed": True,
                    "plan_id": rollback["data"]["plan_id"]}), env=env)
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["data"]["status"], "complete")
            self.assertFalse((ssh / "authorized_keys").exists())

    def test_native_ssh_client_key_generation_uses_preview_and_private_file_permissions(self) -> None:
        import os
        with tempfile.TemporaryDirectory(prefix="ssh-client-key-service-") as temp:
            home = Path(temp)
            home.mkdir(mode=0o700, exist_ok=True)
            ssh = home / ".ssh"
            ssh.mkdir(mode=0o700)
            os.chown(home, os.getuid(), -1); os.chown(ssh, os.getuid(), -1)
            env = {**NATIVE_ENV, "HOME": str(home)}
            preview = management_service.dispatch(request("ssh.client-key.create.preview", {
                "name": "recovery8023"}), env=env)
            self.assertTrue(preview["ok"])
            self.assertTrue(preview["data"]["requires_confirmation"])
            self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", repr(preview))
            created = management_service.dispatch(request("ssh.client-key.create.apply", {
                "name": "recovery8023", "confirmed": True,
                "plan_id": preview["data"]["plan_id"]}), env=env)
            self.assertTrue(created["ok"])
            private = ssh / "ternuxx-keys" / "recovery8023"
            public = Path(str(private) + ".pub")
            self.assertEqual(private.stat().st_mode & 0o777, 0o600)
            self.assertTrue(public.is_file())
            self.assertRegex(created["data"]["fingerprint"], r"^SHA256:[A-Za-z0-9+/]{43}$")
            self.assertNotIn(private.read_text(), repr(created))
            self.assertTrue(created["data"]["enrollment_required"])

    def test_ssh_key_rollback_list_fails_closed_without_verified_managed_key_path(self) -> None:
        result = management_service.dispatch(request("ssh.keys.rollback.list"), env=NATIVE_ENV)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "ssh_configuration_unverified")

    def test_ssh_key_changes_fail_closed_without_verified_managed_key_path(self) -> None:
        result = management_service.dispatch(request("ssh.keys.remove.preview", {
            "fingerprint": "SHA256:abc"}), env=NATIVE_ENV)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "ssh_configuration_unverified")

    def test_terminal_broker_status_is_optional_and_never_probes_proot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="management-terminal-status-") as temp:
            home = Path(temp)
            env = {**NATIVE_ENV, "HOME": str(home),
                   "TERNUXX_STATE_DIR": str(home / ".local/share/ternuxx")}
            with patch.object(management_service.proot_diagnostics, "inspect_installed",
                              side_effect=AssertionError("terminal status must not probe PRoot")):
                result = management_service.dispatch(
                    request("terminal.broker.status"), env=env)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["component"], "terminal_broker")
        self.assertEqual(result["data"]["status"], "not_running")
        self.assertTrue(result["data"]["provider_optional"])

    def test_desktop_status_adapter_preserves_shared_cli_reconciliation_result(self) -> None:
        import json
        from types import SimpleNamespace
        expected = {"status": "stale", "reconciliation_state": "stale", "display": ":1",
                    "supervisor": "absent", "x11": "absent", "xfce4_session": "absent"}
        with patch.object(management_service.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout=json.dumps(expected), stderr="")) as run:
            result = management_service.dispatch(request("desktop.status"), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], expected)
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["--json", "status"])

    def test_gui_monitor_status_and_configuration_share_the_management_api(self) -> None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="management-gui-monitor-") as temp:
            home = Path(temp)
            state = home / ".local/share/ternuxx"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            with patch.object(management_service.gui_monitoring.subprocess, "run",
                              side_effect=AssertionError("status must not probe Android")):
                before = management_service.dispatch(request("desktop.monitor.status"), env=env)
            self.assertTrue(before["ok"])
            self.assertFalse(before["data"]["enabled"])
            self.assertFalse((state / "gui-monitoring.json").exists())
            configured = management_service.dispatch(request("desktop.monitor.configure", {
                "enabled": True, "interval_value": 2, "unit": "minutes",
                "activity_launch": False, "focus_check": False,
            }), env=env)
            self.assertTrue(configured["ok"])
            self.assertEqual(configured["data"]["interval_seconds"], 120)
            after = management_service.dispatch(request("desktop.monitor.status"), env=env)
            self.assertTrue(after["data"]["enabled"])
            self.assertEqual(after["data"]["interval_seconds"], 120)
            invalid = management_service.dispatch(request("desktop.monitor.configure", {
                "activity_launch": True,
            }), env=env)
            self.assertFalse(invalid["ok"])
            self.assertEqual(invalid["error"]["code"], "operation_failed")

    def test_gui_monitor_cli_adapter_uses_shared_persistent_policy(self) -> None:
        import contextlib
        import io
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="management-gui-monitor-cli-") as temp:
            home = Path(temp)
            state = home / ".local/share/ternuxx"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            output = io.StringIO()
            with patch.dict("os.environ", env, clear=False), contextlib.redirect_stdout(output):
                rc = management_service.main([
                    "--operation", "desktop.monitor.configure", "--monitor-enabled",
                    "--monitor-interval", "5", "--monitor-unit", "minutes",
                    "--monitor-focus-check", "--monitor-activity-launch", "--json",
                ])
            self.assertEqual(rc, 0)
            data = json.loads(output.getvalue())["data"]
            self.assertTrue(data["enabled"])
            self.assertEqual(data["interval_seconds"], 300)
            self.assertTrue(data["focus_check"])
            self.assertTrue(data["activity_launch"])
            self.assertEqual(data["scheduler"], "not_running")

    def test_boot_helper_status_and_preview_use_shared_service(self) -> None:
        expected = {"component": "boot_helpers", "helpers": [], "read_only": True}
        with patch.object(management_service.boot_helpers, "status", return_value=expected) as status:
            result = management_service.dispatch(request("boot.helpers.status"), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], expected)
        self.assertEqual(status.call_args.kwargs["home"], NATIVE_ENV["HOME"])
        preview = {"plan": {"plan_id": "a" * 32}, "confirmation_required": True}
        with patch.object(management_service.boot_helpers, "preview", return_value=preview) as plan:
            result = management_service.dispatch(request("boot.helpers.preview", {
                "helper_id": "services", "action": "deploy",
            }), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], preview)
        self.assertEqual(plan.call_args.kwargs["helper_id"], "services")
        self.assertEqual(plan.call_args.kwargs["action"], "deploy")

    def test_rejects_unknown_operation_even_if_unhashable(self) -> None:
        result = management_service.dispatch(request({"shell": "id"}), env=NATIVE_ENV)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "operation_not_supported")

    def test_rejects_unknown_fields_versions_callers_and_environments(self) -> None:
        self.assertEqual(management_service.dispatch({"api_version": 1}, env=NATIVE_ENV)["error"]["code"], "invalid_request")
        self.assertEqual(management_service.dispatch(request("ssh.inspect", api_version=2), env=NATIVE_ENV)["error"]["code"], "unsupported_api_version")
        self.assertEqual(management_service.dispatch(request("ssh.inspect", api_version=True), env=NATIVE_ENV)["error"]["code"], "unsupported_api_version")
        self.assertEqual(management_service.dispatch(request("ssh.inspect"), caller="web_ui", env=NATIVE_ENV)["error"]["code"], "unauthorized")
        self.assertEqual(management_service.dispatch(request("ssh.inspect"), env={})["error"]["code"], "native_termux_required")
        self.assertEqual(management_service.dispatch(request("ssh.inspect", {"arbitrary": True}), env=NATIVE_ENV)["error"]["code"], "invalid_arguments")

    def test_remote_access_preview_uses_local_allowlist_and_never_activates_transport(self) -> None:
        default = management_service.dispatch(request("remote.access.preview"), env=NATIVE_ENV)
        self.assertTrue(default["ok"])
        self.assertEqual(default["data"]["mode"], "disabled")
        self.assertFalse(default["data"]["remote_access_active"])
        policy = {
            "schema_version": 2, "mode": "private_transport", "public_ingress": False,
            "transport": {"kind": "vpn_overlay", "provider_id": "owner_selected",
                          "credential_ref": "credential_ref_00000001"},
            "allowed_client_refs": ["client_ref_001"], "allowed_targets": ["native_termux"],
            "capability_refs": ["capability_001"], "session_ttl_seconds": 900,
        }
        private = management_service.dispatch(request("remote.access.preview", {"policy": policy}), env=NATIVE_ENV)
        self.assertTrue(private["ok"])
        self.assertEqual(private["data"]["readiness"], "unavailable")
        self.assertFalse(private["data"]["remote_access_active"])
        self.assertNotIn("credential_ref_00000001", str(private["data"]))
        self.assertNotIn("client_ref_001", str(private["data"]))
        invalid = management_service.dispatch(request("remote.access.preview", {"policy": {"mode": "public"}}), env=NATIVE_ENV)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid_remote_access_policy")

    def test_remote_policy_stdin_cli_requires_explicit_pipe_and_rejects_bad_json(self) -> None:
        import contextlib
        import io
        policy = {"schema_version": 2, "mode": "disabled", "public_ingress": False}
        stdout = io.StringIO()
        with patch.dict("os.environ", NATIVE_ENV), patch("sys.stdin", io.StringIO(__import__("json").dumps(policy))), \
             contextlib.redirect_stdout(stdout):
            code = management_service.main(["--operation", "remote.access.preview", "--policy-stdin", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(__import__("json").loads(stdout.getvalue())["data"]["mode"], "disabled")
        stdout = io.StringIO()
        with patch.dict("os.environ", NATIVE_ENV), patch("sys.stdin", io.StringIO("not-json")), \
             contextlib.redirect_stdout(stdout):
            code = management_service.main(["--operation", "remote.access.preview", "--policy-stdin", "--json"])
        self.assertEqual(code, 1)
        self.assertFalse(__import__("json").loads(stdout.getvalue())["ok"])

    def test_cron_status_reports_scheduler_runtime_separately_from_registry(self) -> None:
        result = management_service.dispatch(request("cron.status"), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["scheduler"], "stopped")
        self.assertFalse(result["data"]["scheduler_runtime"]["lease_held"])
        self.assertEqual(result["data"]["execution_ledger"]["scheduler"],
                         "runtime_status_reported_by_cron_status")
        self.assertEqual(result["data"]["execution_ledger"]["execution_core"],
                         "typed_action_executor_available")

    def test_cron_scheduler_mutation_is_confirmed_and_scoped(self) -> None:
        import management_authorization
        self.assertEqual(management_authorization.required_capability("cron.scheduler.start"),
                         "cron.scheduler.manage")
        self.assertEqual(management_authorization.required_capability("cron.scheduler.stop"),
                         "cron.scheduler.manage")
        denied = management_service.dispatch(
            request("cron.scheduler.stop", {"confirmed": False}), env=NATIVE_ENV)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "confirmation_required")

    def test_proot_status_routes_to_readonly_inventory_without_entering_guest(self) -> None:
        inventory = {"component": "proot_distribution_inventory", "status": "installed",
                     "manager_available": True, "installed_distributions": ["debian"],
                     "ownership": "unverified", "guest_entered": False, "read_only": True}
        with patch.object(management_service.proot_diagnostics, "inspect_installed", return_value=inventory) as inspect:
            result = management_service.dispatch(request("proot.status"), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], inventory)
        inspect.assert_called_once_with()

    def test_proot_guest_verify_routes_only_typed_readonly_arguments(self) -> None:
        report = {"component": "proot_guest_diagnostics", "status": "partial", "read_only": True}
        args = {"distro": "debian", "user": "sbj", "display": ":1", "backend": "zink"}
        with patch.object(management_service.proot_diagnostics, "verify_proot_guest", return_value=report) as verify:
            result = management_service.dispatch(request("proot.guest.verify", args), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], report)
        verify.assert_called_once_with(**args, prefix=NATIVE_ENV["PREFIX"])
        malformed = management_service.dispatch(
            request("proot.guest.verify", {**args, "user": "sbj;id"}), env=NATIVE_ENV)
        self.assertFalse(malformed["ok"])
        self.assertEqual(malformed["error"]["code"], "invalid_arguments")

    def test_proot_guest_verify_can_resolve_user_from_private_ternux_state(self) -> None:
        secret_user = "configured_guest"
        args = {"distro": "debian", "user_source": "rootfs", "display": ":1", "backend": "zink"}
        report = {"component": "proot_guest_diagnostics", "status": "complete", "read_only": True}
        env = {**NATIVE_ENV, "PATH": "/fixture/bin"}
        with patch.object(management_service.proot_diagnostics, "resolve_proot_guest_user", return_value=secret_user) as resolve, \
             patch.object(management_service.proot_diagnostics, "verify_proot_guest", return_value=report) as verify:
            result = management_service.dispatch(request("proot.guest.verify", args), env=env)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], report)
        resolve.assert_called_once_with(distro="debian", prefix=env["PREFIX"])
        verify.assert_called_once_with(distro="debian", user=secret_user, display=":1", backend="zink",
                                       prefix=env["PREFIX"])
        self.assertNotIn(secret_user, __import__("json").dumps(result))
        ambiguous = management_service.dispatch(
            request("proot.guest.verify", {**args, "user": secret_user}), env=env)
        self.assertFalse(ambiguous["ok"])
        self.assertEqual(ambiguous["error"]["code"], "invalid_arguments")
        malformed_source = management_service.dispatch(
            request("proot.guest.verify", {**args, "user_source": []}), env=env)
        self.assertFalse(malformed_source["ok"])
        self.assertEqual(malformed_source["error"]["code"], "invalid_arguments")

    def test_proot_guest_verify_cli_accepts_private_ternux_state_source_without_echoing_user(self) -> None:
        import contextlib
        import io
        secret_user = "private_guest_account"
        stdout = io.StringIO()
        env = {**NATIVE_ENV, "PATH": "/fixture/bin"}
        report = {"component": "proot_guest_diagnostics", "status": "complete", "read_only": True}
        with patch.dict("os.environ", env), \
             patch.object(management_service.proot_diagnostics, "resolve_proot_guest_user", return_value=secret_user) as resolve, \
             patch.object(management_service.proot_diagnostics, "verify_proot_guest", return_value=report) as verify, \
             contextlib.redirect_stdout(stdout):
            code = management_service.main([
                "--operation", "proot.guest.verify", "--distro", "debian",
                "--guest-user-source", "rootfs", "--display", ":1", "--backend", "zink", "--json",
            ])
        self.assertEqual(code, 0)
        result = __import__("json").loads(stdout.getvalue())
        self.assertTrue(result["ok"])
        self.assertNotIn(secret_user, stdout.getvalue())
        resolve.assert_called_once_with(distro="debian", prefix=env["PREFIX"])
        verify.assert_called_once_with(distro="debian", user=secret_user, display=":1", backend="zink",
                                       prefix=env["PREFIX"])

    def test_proot_guest_verify_cli_requires_all_explicit_profile_fields(self) -> None:
        import contextlib
        import io
        stdout = io.StringIO()
        with patch.dict("os.environ", NATIVE_ENV), contextlib.redirect_stdout(stdout):
            code = management_service.main(["--operation", "proot.guest.verify", "--json"])
        self.assertEqual(code, 1)
        response = __import__("json").loads(stdout.getvalue())
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_arguments")

    def test_ssh_inspection_returns_versioned_envelope_without_checkpoint_state(self) -> None:
        with patch.object(management_service.ssh_diagnostics, "inspect_native", return_value={"read_only": True}) as inspect:
            response = management_service.dispatch(request("ssh.inspect"), env={**NATIVE_ENV, "TERNUXX_STATE_DIR": ""})
        self.assertTrue(response["ok"])
        self.assertEqual(response["api_version"], 1)
        self.assertEqual(response["operation"], "ssh.inspect")
        self.assertEqual(response["data"], {"read_only": True})
        inspect.assert_called_once()

    def test_native_boot_and_wakelock_status_are_readonly(self) -> None:
        response = management_service.dispatch(request("boot.status"), env=NATIVE_ENV)
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["safety"]["read_only"], True)
        with patch.object(management_service.wakelock_manager, "status", return_value={
            "active_lock_state": "unknown", "safety": {"acquire_or_release_invoked": False}
        }) as inspect:
            lock = management_service.dispatch(request("wakelock.status"), env=NATIVE_ENV)
        self.assertTrue(lock["ok"])
        self.assertEqual(lock["data"]["active_lock_state"], "unknown")
        inspect.assert_called_once()

    def test_boot_profile_preview_uses_shared_readonly_management_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-profile-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            status = management_service.dispatch(request("boot.profile.status"), env=env)
            self.assertTrue(status["ok"])
            self.assertEqual(status["data"]["configured_profile"], "cli-only")
            self.assertEqual(status["data"]["managed_script_identity"], "not_configured")
            self.assertEqual(status["data"]["schema_version"], 2)
            result = management_service.dispatch(
                request("boot.profile.preview", {"profile": "cli-only"}), env=env,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"]["requested_profile"], "cli-only")
            self.assertTrue(result["data"]["safety"]["read_only"])
            self.assertFalse((home / ".state").exists())

    def test_boot_enable_requires_confirmation_and_verified_companion_app(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-enable-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            request_args = {"profile": "native", "confirmed": False}
            with patch.object(management_service.runtime_diagnostics, "inspect_boot", return_value={"app": "installed"}):
                preview = management_service.dispatch(request("boot.enable", request_args), env=env)
            self.assertTrue(preview["ok"])
            self.assertTrue(preview["data"]["requires_confirmation"])
            self.assertFalse(preview["data"]["changed"])
            self.assertFalse((home / ".termux").exists())
            self.assertFalse((home / ".state").exists())

            with patch.object(management_service.runtime_diagnostics, "inspect_boot", return_value={"app": "unknown"}):
                denied = management_service.dispatch(
                    request("boot.enable", {"profile": "native", "confirmed": True}), env=env,
                )
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"]["code"], "operation_failed")
            self.assertFalse((home / ".termux").exists())

    def test_boot_disable_without_confirmation_is_a_readonly_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-disable-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            response = management_service.dispatch(request("boot.disable", {"confirmed": False}), env=env)
            self.assertTrue(response["ok"])
            self.assertTrue(response["data"]["safety"]["read_only"])
            self.assertFalse(response["data"]["changed"])
            self.assertFalse((home / ".termux").exists())
            self.assertFalse((home / ".state").exists())

    def test_wakelock_mutation_is_allowlisted_and_bound_to_invoking_process(self) -> None:
        with patch.object(management_service.wakelock_manager, "is_ancestor", return_value=True), \
             patch.object(management_service.wakelock_manager, "acquire", return_value={"state": "acquired"}) as acquire:
            result = management_service.dispatch(
                request("wakelock.acquire", {"owner": "native.sshd", "persistent": True}),
                env={**NATIVE_ENV, "TERNUXX_WAKELOCK_CALLER_PID": "123"},
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["state"], "acquired")
        acquire.assert_called_once()
        with patch.object(management_service.wakelock_manager, "is_ancestor", return_value=False):
            denied = management_service.dispatch(
                request("wakelock.release", {"owner": "native.sshd", "persistent": True}),
                env={**NATIVE_ENV, "TERNUXX_WAKELOCK_CALLER_PID": "123"},
            )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "unauthorized")

    def test_checkpoint_prepare_and_verify_use_same_service_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-management-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            prepared = management_service.dispatch(
                request("continuity.prepare", {"test_id": "api-contract", "commit": "abcdef0", "worktree_state": "dirty"}),
                env=env,
            )
            self.assertTrue(prepared["ok"])
            checkpoint_id = prepared["data"]["checkpoint_id"]
            verified = management_service.dispatch(request("continuity.verify", {"checkpoint_id": checkpoint_id}), env=env)
            self.assertTrue(verified["ok"])
            self.assertIn(verified["data"]["outcome"], {"same_boot", "boot_id_unavailable"})

    def test_reboot_verification_uses_private_checkpoint_nonce(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-management-reboot-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            baseline = {
                "native": {"termux_version": "test"},
                "repository": {"id": "soobujmiah/ternuxx", "branch": "main", "commit": "abcdef0",
                               "modified_paths": 0, "untracked_paths": 0},
                "stage": "test", "references": ["README.md"],
                "ssh": {"sshd_process": "unknown", "auth_modes": ["unknown"], "config_syntax": "unknown",
                        "socket_binding": "unverified", "boot_policy": "unknown"},
                "termux_boot": {"app": "unknown", "script_directory": "unknown", "startup_policy": "unknown"},
                "wake_lock": {"cli_available": False, "launcher_acquire_request": False,
                              "launcher_global_release_request": False, "ownership": "unknown"},
                "required_postboot_checks": [], "recovery_instructions": ["Inspect native status."],
                "rollback_instructions": ["Preserve the checkpoint."], "next_action": "verify",
            }
            prepared = management_service.dispatch(request("continuity.prepare-reboot-test", {
                "test_id": "api-reboot-check", "baseline": baseline,
            }), env=env)
            self.assertTrue(prepared["ok"])
            verified = management_service.dispatch(request("continuity.verify-reboot-test", {
                "test_id": "api-reboot-check",
            }), env=env)
            self.assertTrue(verified["ok"])
            self.assertEqual(verified["data"]["outcome"], "same_boot")
            self.assertNotIn("nonce", verified["data"])
            denied = management_service.dispatch(request("continuity.verify-reboot-test", {
                "test_id": "api-reboot-check", "nonce": "unexpected",
            }), env=env)
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"]["code"], "invalid_arguments")

    def test_ssh_autostart_policy_routes_status_preview_and_apply_through_shared_service(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssh-autostart-service-") as temp:
            home = Path(temp) / "home"; home.mkdir(mode=0o700, parents=True)
            state = home / ".local/share/ternuxx"; state.mkdir(mode=0o700, parents=True)
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            with patch.object(management_service.ssh_service_autostart, "status", return_value={"enabled": True}) as status:
                result = management_service.dispatch(request("ssh.service.autostart.status"), env=env)
            self.assertTrue(result["ok"]); status.assert_called_once()
            with patch.object(management_service.ssh_service_autostart, "preview", return_value={
                    "status": "ready", "changed": True, "plan_id": "a" * 32}) as preview:
                result = management_service.dispatch(request("ssh.service.autostart.preview", {"enabled": False}), env=env)
            self.assertTrue(result["ok"]); preview.assert_called_once()
            self.assertFalse(preview.call_args.kwargs["enabled"])
            with patch.object(management_service.ssh_service_autostart, "apply", return_value={
                    "status": "disabled", "changed": True, "enabled": False}) as apply:
                result = management_service.dispatch(request("ssh.service.autostart.apply", {
                    "enabled": False, "confirmed": True, "plan_id": "a" * 32}), env=env)
            self.assertTrue(result["ok"]); apply.assert_called_once()
            self.assertEqual(apply.call_args.kwargs["plan_id"], "a" * 32)
            denied = management_service.dispatch(request("ssh.service.autostart.apply", {
                "enabled": False, "confirmed": "yes", "plan_id": "a" * 32}), env=env)
            self.assertFalse(denied["ok"])

    def test_ssh_wakelock_policy_uses_preview_apply_and_preserves_running_lease(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssh-wakelock-service-") as temp:
            home = Path(temp) / "home"; home.mkdir(mode=0o700)
            state = home / ".local/share/ternuxx"; state.mkdir(mode=0o700, parents=True)
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            current = management_service.dispatch(request("wakelock.ssh-policy.status"), env=env)
            self.assertTrue(current["ok"]); self.assertTrue(current["data"]["persistent_lease_enabled"])
            preview = management_service.dispatch(request("wakelock.ssh-policy.preview", {"enabled": False}), env=env)
            self.assertTrue(preview["ok"]); self.assertTrue(preview["data"]["requires_confirmation"])
            unconfirmed = management_service.dispatch(request("wakelock.ssh-policy.apply", {
                "enabled": False, "confirmed": False, "plan_id": preview["data"]["plan_id"]}), env=env)
            self.assertFalse(unconfirmed["ok"]); self.assertEqual(unconfirmed["error"]["code"], "confirmation_required")
            applied = management_service.dispatch(request("wakelock.ssh-policy.apply", {
                "enabled": False, "confirmed": True, "plan_id": preview["data"]["plan_id"]}), env=env)
            self.assertTrue(applied["ok"]); self.assertFalse(applied["data"]["current_service_lease_changed"])
            self.assertFalse(management_service.dispatch(request("wakelock.ssh-policy.status"), env=env)["data"]["persistent_lease_enabled"])

    def test_ssh_service_preview_is_allowlisted_and_requires_native_private_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-ssh-service-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(home / ".state")}
            preview_data = {"action": "start", "read_only": True, "requires_confirmation": True}
            with patch.object(management_service.runit_service, "apply", return_value=preview_data) as action:
                response = management_service.dispatch(
                    request("ssh.service.start", {"confirmed": False, "plan_id": None}), env=env)
            self.assertTrue(response["ok"])
            self.assertEqual(response["data"], preview_data)
            action.assert_called_once()
            with patch.object(management_service.runit_service, "apply", return_value={
                    "action": "restart", "read_only": True, "requires_confirmation": True}) as restart:
                response = management_service.dispatch(
                    request("ssh.service.restart", {"confirmed": False, "plan_id": None}), env=env)
            self.assertTrue(response["ok"])
            restart.assert_called_once()
            self.assertEqual(restart.call_args.args[0], "restart")
            denied = management_service.dispatch(
                request("ssh.service.stop", {"confirmed": "false", "plan_id": None}), env=env)
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"]["code"], "invalid_arguments")
            untrusted = management_service.dispatch(
                request("ssh.service.stop", {"confirmed": False, "plan_id": None}),
                caller="web_ui", env=env)
            self.assertEqual(untrusted["error"]["code"], "unauthorized")

    def test_backend_has_no_generic_shell_or_unlisted_operation(self) -> None:
        self.assertNotIn("shell.exec", management_service.OPERATIONS)
        self.assertNotIn("shell.exec", management_service.OPERATIONS)
        self.assertIn("continuity.prepare-reboot-test", management_service.OPERATIONS)
        self.assertIn("boot.status", management_service.OPERATIONS)
        self.assertIn("boot.profile.status", management_service.OPERATIONS)
        self.assertIn("boot.profile.preview", management_service.OPERATIONS)
        self.assertIn("boot.enable", management_service.OPERATIONS)
        self.assertIn("boot.disable", management_service.OPERATIONS)
        self.assertIn("wakelock.acquire", management_service.OPERATIONS)
        self.assertIn("wakelock.release", management_service.OPERATIONS)


    def test_backup_and_restore_preview_are_allowlisted_and_readonly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-recovery-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            state = home / ".state"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            preview = management_service.dispatch(request("backup.create", {"name": "api-snapshot"}), env=env)
            self.assertTrue(preview["ok"])
            self.assertEqual(preview["data"]["action"], "preview")
            self.assertFalse(state.exists())
            self.assertFalse(management_service.dispatch(request("backup.create", {
                "name": "api-snapshot", "confirmed": True,
            }), env=env)["ok"])
            created = management_service.dispatch(request("backup.create", {
                "name": "api-snapshot", "confirmed": True, "plan_id": preview["data"]["plan_id"],
            }), env=env)
            self.assertTrue(created["ok"])
            inspected = management_service.dispatch(request("backup.inspect", {
                "backup_id": "api-snapshot",
            }), env=env)
            self.assertTrue(inspected["ok"])
            restore = management_service.dispatch(request("restore.preview", {
                "backup_id": "api-snapshot",
            }), env=env)
            self.assertTrue(restore["ok"])
            self.assertEqual(restore["data"]["action"], "restore_preview")
            denied = management_service.dispatch(request("restore.apply", {
                "backup_id": "api-snapshot", "confirmed": True, "plan_id": "0" * 64,
            }), env=env)
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"]["code"], "recovery_failed")

    def test_recovery_status_and_inspect_are_readonly_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-recovery-journal-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            state = home / ".state"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            empty = management_service.dispatch(request("recovery.status"), env=env)
            self.assertTrue(empty["ok"])
            self.assertEqual(empty["data"]["operations"], [])
            self.assertFalse(state.exists())
            with patch.object(Path, "home", return_value=home):
                operation_id = operation_journal.begin(str(state), "recovery.backup.create", "fixture")
                operation_journal.update(str(state), operation_id, "complete", "fixture complete")
            status = management_service.dispatch(request("recovery.status"), env=env)
            inspected = management_service.dispatch(request("recovery.inspect", {"operation_id": operation_id}), env=env)
            self.assertTrue(status["ok"] and inspected["ok"])
            self.assertEqual(status["data"]["unresolved_count"], 0)
            self.assertNotIn("initiating_pid", inspected["data"]["operation"])

    def test_generic_recovery_routes_operation_specific_preview_and_apply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-operation-recovery-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            state = home / ".state"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            operation_id = "0123456789abcdef0123456789abcdef"
            with patch.object(management_service.operation_recovery, "resolve", return_value={
                "operation_id": operation_id, "resolution": "failed", "read_only": True,
            }) as resolve:
                response = management_service.dispatch(request("recovery.resolve", {
                    "operation_id": operation_id,
                }), env=env)
            self.assertTrue(response["ok"])
            resolve.assert_called_once_with(operation_id, prefix=env["PREFIX"], home=str(home),
                                            state_dir=str(state), confirmed=False, plan_id=None)
            with patch.object(management_service.operation_recovery, "resolve", return_value={
                "operation_id": operation_id, "resolution": "complete", "boot_files_changed": False,
            }) as resolve:
                response = management_service.dispatch(request("recovery.resolve", {
                    "operation_id": operation_id, "confirmed": True, "plan_id": "a" * 64,
                }), env=env)
            self.assertTrue(response["ok"])
            self.assertFalse(response["data"]["boot_files_changed"])
            resolve.assert_called_once_with(operation_id, prefix=env["PREFIX"], home=str(home),
                                            state_dir=str(state), confirmed=True, plan_id="a" * 64)

    def test_recovery_rollback_routes_preview_and_confirmed_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-recovery-rollback-api-") as temp:
            home = Path(temp) / "home"
            home.mkdir()
            state = home / ".state"
            env = {**NATIVE_ENV, "HOME": str(home), "TERNUXX_STATE_DIR": str(state)}
            operation_id = "0123456789abcdef0123456789abcdef"
            preview_data = {"action": "rollback_preview", "operation_id": operation_id,
                            "plan_id": "f" * 64, "read_only": True}
            with patch.object(management_service.config_recovery, "rollback_preview", return_value=preview_data) as preview:
                response = management_service.dispatch(request("recovery.rollback.preview",
                    {"operation_id": operation_id}), env=env)
            self.assertTrue(response["ok"])
            self.assertTrue(response["data"]["read_only"])
            preview.assert_called_once_with(home=str(home), state_dir=str(state), operation_id=operation_id)
            with patch.object(management_service.config_recovery, "rollback_restore", return_value={
                "action": "rolled_back", "rollback_of_operation": operation_id,
            }) as apply:
                response = management_service.dispatch(request("recovery.rollback.apply", {
                    "operation_id": operation_id, "confirmed": True, "plan_id": "f" * 64,
                }), env=env)
            self.assertTrue(response["ok"])
            apply.assert_called_once_with(home=str(home), state_dir=str(state), operation_id=operation_id,
                                          confirmed=True, plan_id="f" * 64)

    def test_recovery_service_rejects_nonlocal_caller_and_unlisted_fields(self) -> None:
        denied = management_service.dispatch(request("backup.list"), caller="remote", env=NATIVE_ENV)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "unauthorized")
        invalid = management_service.dispatch(request("backup.create", {"name": "one", "path": "/tmp/escape"}), env=NATIVE_ENV)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid_arguments")

    def test_proot_profiles_and_start_preview_use_shared_typed_operations(self) -> None:
        import proot_sessions
        profiles = {"profiles": [{"id": "isolated-probe"}, {"id": "debian-interactive"}],
                    "rootfs_state": "available", "rootfs_identity": {"device": 1, "inode": 2},
                    "launcher": "/fixture/proot-distro", "diagnostic": None}
        plan = {"profile": "debian-interactive", "plan_id": "plan-" + "a" * 64,
                "confirmation_required": True, "mode": "foreground-tty"}
        with patch.object(proot_sessions, "profile_inventory", return_value=profiles) as inventory, \
             patch.object(proot_sessions, "preview_start", return_value=plan) as preview:
            listed = management_service.dispatch(request("proot.profiles.list"), env=NATIVE_ENV)
            shown = management_service.dispatch(request("proot.profiles.show", {"profile": "debian-interactive"}), env=NATIVE_ENV)
            ready = management_service.dispatch(request("proot.start.preview", {"profile": "debian-interactive"}), env=NATIVE_ENV)
        self.assertTrue(listed["ok"] and shown["ok"] and ready["ok"])
        self.assertEqual(listed["data"], profiles)
        self.assertEqual(ready["data"], plan)
        self.assertEqual(inventory.call_count, 2)
        preview.assert_called_once_with("debian-interactive", prefix=NATIVE_ENV["PREFIX"])

    def test_proot_start_mutation_requires_exact_confirmation_and_narrow_scope(self) -> None:
        import management_authorization
        self.assertEqual(management_authorization.required_capability("proot.start"), "proot.session.manage")
        self.assertEqual(management_authorization.required_capability("proot.stop"), "proot.session.manage")
        denied = management_service.dispatch(request("proot.start", {
            "profile": "isolated-probe", "confirmed": False, "plan_id": "plan-x",
            "timeout_seconds": 300}), env=NATIVE_ENV)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "confirmation_required")


    def test_proot_start_rejects_arbitrary_guest_command_fields(self) -> None:
        base = {"profile": "debian-interactive", "confirmed": True,
                "plan_id": "plan-" + "a" * 64, "timeout_seconds": 300}
        for field, value in (("command", "/bin/sh -c id"),
                             ("argv", ["/bin/sh", "-c", "id"]),
                             ("environment", {"LD_PRELOAD": "/tmp/host.so"}),
                             ("rootfs", "/data/local/tmp/rootfs"),
                             ("user", "root"),
                             ("working_directory", "/tmp")):
            with self.subTest(field=field):
                args = {**base, field: value}
                denied = management_service.dispatch(request("proot.start", args), env=NATIVE_ENV)
                self.assertFalse(denied["ok"])
                self.assertEqual(denied["error"]["code"], "invalid_arguments")

    def test_proot_session_health_is_shared_read_only_operation(self) -> None:
        import proot_sessions
        session_id = "proot-" + "a" * 32
        expected = {"session_id": session_id, "state": "running", "read_only": True,
                    "reattach_supported": False}
        with patch.object(proot_sessions, "session_health", return_value=expected) as health:
            response = management_service.dispatch(request(
                "proot.sessions.health", {"session_id": session_id}), env=NATIVE_ENV)
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"], expected)
        health.assert_called_once()
        invalid = management_service.dispatch(request("proot.sessions.health", {}), env=NATIVE_ENV)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid_arguments")


if __name__ == "__main__":
    unittest.main()
