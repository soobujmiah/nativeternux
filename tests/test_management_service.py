"""Contract tests for the allowlisted local management application service."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
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
    def test_typed_cron_create_builds_canonical_jobs_for_every_schedule_in_service(self) -> None:
        cases = [
            ("cron", {"expression": "0 8 * * *"}, {"expression": "0 8 * * *", "timezone": "Asia/Dhaka"}),
            ("interval", {"interval_seconds": 3600, "anchor_at": "2026-10-24T00:00:00Z"},
             {"interval_seconds": 3600, "anchor_at": "2026-10-24T00:00:00Z"}),
            ("calendar", {"mode": "daily", "time": "08:30"},
             {"mode": "daily", "time": "08:30", "timezone": "Asia/Dhaka"}),
            ("calendar", {"mode": "specific", "datetime": "2099-01-01T08:30:00+06:00"},
             {"mode": "specific", "datetime": "2099-01-01T08:30:00+06:00"}),
            ("one_time", {"at": "2099-01-01T08:30:00+06:00"},
             {"at": "2099-01-01T08:30:00+06:00"}),
        ]
        with tempfile.TemporaryDirectory() as temp:
            env = {**NATIVE_ENV, "HOME": temp, "TERNUXX_STATE_DIR": str(Path(temp) / "state")}
            for index, (schedule_type, schedule, expected_schedule) in enumerate(cases):
                with self.subTest(schedule_type=schedule_type, schedule=schedule),                         patch.object(management_service.timezone_support, "current_timezone", return_value="Asia/Dhaka"),                         patch.object(management_service.cron_registry, "preview_job_mutation",
                                     return_value={"plan_id": "a" * 32, "action": "create"}) as preview:
                    payload = {"action": "create", "name": f"job {index}",
                               "action_id": "diagnostics.doctor", "schedule_type": schedule_type,
                               "schedule": schedule}
                    result = management_service.dispatch(request("cron.jobs.mutation.preview", payload), env=env)
                    self.assertTrue(result["ok"])
                    job = preview.call_args.kwargs["job"]
                    self.assertEqual(job["schedule_type"], schedule_type)
                    self.assertEqual(job["schedule"], expected_schedule)
                    self.assertEqual(job["owner"], "ternuxx")
                    self.assertEqual(job["enabled"], False)

    def test_typed_cron_create_rejects_invalid_schedule_before_preview(self) -> None:
        with patch.object(management_service.cron_registry, "preview_job_mutation") as preview:
            result = management_service.dispatch(request("cron.jobs.mutation.preview", {
                "action": "create", "name": "bad", "action_id": "diagnostics.doctor",
                "schedule_type": "interval", "schedule": {"interval_seconds": "60", "anchor_at": "bad"}}),
                env=NATIVE_ENV)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "cron_registry_error")
        preview.assert_not_called()

    def test_cpu_inference_is_a_shared_native_management_resource(self) -> None:
        status = {"runtime": {"available": True}, "model": {"state": "present-unverified"}}
        with patch.object(management_service.cpu_inference, "status", return_value=status) as probe:
            result = management_service.dispatch(request("inference.cpu.status"), env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], status)
        probe.assert_called_once()
        catalog = management_service.dispatch(request("management.catalog"), env=NATIVE_ENV)
        self.assertTrue(catalog["ok"])
        resource = next(item for item in catalog["data"]["resources"] if item["id"] == "inference.cpu.local")
        self.assertEqual(resource["supported_operations"], [
            "inference.cpu.status", "inference.cpu.model.preview",
            "inference.cpu.model.apply", "inference.cpu.run"])

    def test_cpu_model_apply_requires_typed_exact_plan_and_dispatches_same_runtime(self) -> None:
        with patch.object(management_service.cpu_inference, "install_model", return_value={"installed": True}) as install:
            missing = management_service.dispatch(request("inference.cpu.model.apply", {
                "action": "install", "plan_id": "a" * 24}), env=NATIVE_ENV)
            self.assertFalse(missing["ok"])
            self.assertEqual(missing["error"]["code"], "confirmation_required")
            applied = management_service.dispatch(request("inference.cpu.model.apply", {
                "action": "install", "plan_id": "a" * 24, "confirmed": True}), env=NATIVE_ENV)
        self.assertTrue(applied["ok"])
        install.assert_called_once()
        self.assertEqual(install.call_args.kwargs["plan_id"], "a" * 24)
        self.assertEqual(install.call_args.kwargs["confirmed"], "DOWNLOAD")

    def test_cpu_run_is_bounded_and_rejects_invalid_input_before_runtime(self) -> None:
        with patch.object(management_service.cpu_inference, "run_inference", return_value={"output": "ok"}) as run:
            invalid = management_service.dispatch(request("inference.cpu.run", {
                "prompt": "bad\nline", "max_tokens": 64}), env=NATIVE_ENV)
            self.assertFalse(invalid["ok"])
            self.assertEqual(invalid["error"]["code"], "invalid_arguments")
            too_many = management_service.dispatch(request("inference.cpu.run", {
                "prompt": "hello", "max_tokens": 129}), env=NATIVE_ENV)
            self.assertFalse(too_many["ok"])
            good = management_service.dispatch(request("inference.cpu.run", {
                "prompt": "hello", "max_tokens": 32}), env=NATIVE_ENV)
        self.assertTrue(good["ok"])
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["max_tokens"], 32)

    def test_cli_inference_operations_use_the_shared_service_contract(self) -> None:
        calls = []
        def fake_dispatch(request_data, env=None):
            calls.append(request_data)
            return {"api_version": 1, "request_id": request_data["request_id"],
                    "ok": True, "operation": request_data["operation"], "data": {}}

        with patch.object(management_service, "dispatch", side_effect=fake_dispatch), \
                patch.dict(os.environ, NATIVE_ENV, clear=False), \
                patch("sys.stdin", io.StringIO("one-line local prompt")), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(management_service.main([
                "--operation", "inference.cpu.status", "--json"]), 0)
            self.assertEqual(management_service.main([
                "--operation", "inference.cpu.model.preview", "--model-action", "install", "--json"]), 0)
            self.assertEqual(management_service.main([
                "--operation", "inference.cpu.model.apply", "--model-action", "install",
                "--plan-id", "a" * 24, "--model-confirm", "DOWNLOAD", "--json"]), 0)
            self.assertEqual(management_service.main([
                "--operation", "inference.cpu.run", "--prompt-stdin", "--max-tokens", "32", "--json"]), 0)

        self.assertEqual([call["operation"] for call in calls], [
            "inference.cpu.status", "inference.cpu.model.preview",
            "inference.cpu.model.apply", "inference.cpu.run"])
        self.assertEqual(calls[1]["args"], {"action": "install"})
        self.assertEqual(calls[2]["args"], {
            "action": "install", "plan_id": "a" * 24, "confirmed": True})
        self.assertEqual(calls[3]["args"], {
            "prompt": "one-line local prompt", "max_tokens": 32})
        self.assertEqual([json.loads(line)["operation"] for line in output.getvalue().splitlines()], [
            "inference.cpu.status", "inference.cpu.model.preview",
            "inference.cpu.model.apply", "inference.cpu.run"])

    def test_cli_inference_model_apply_rejects_a_confirmation_for_the_wrong_action(self) -> None:
        with patch.object(management_service, "dispatch") as dispatch, \
                patch.dict(os.environ, NATIVE_ENV, clear=False), \
                redirect_stdout(io.StringIO()) as output:
            result = management_service.main([
                "--operation", "inference.cpu.model.apply", "--model-action", "install",
                "--plan-id", "a" * 24, "--model-confirm", "REMOVE", "--json"])
        self.assertEqual(result, 1)
        dispatch.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "confirmation_required")

    def test_public_tx_ai_wrapper_routes_cpu_work_through_the_shared_service(self) -> None:
        source = (ROOT / "lib/ai.sh").read_text(encoding="utf-8")
        self.assertIn('management_service.py', source)
        self.assertIn('--operation inference.cpu.status', source)
        self.assertIn('--operation inference.cpu.model.preview', source)
        self.assertIn('--operation inference.cpu.model.apply', source)
        self.assertIn('--operation inference.cpu.run', source)
        self.assertNotIn('cpu_inference.py', source)

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

    def test_curated_file_handoff_is_read_only_and_only_accepts_directory_tree(self) -> None:
        with patch.object(management_service.optional_software, "inspect_directory_tree",
                          return_value={"read_only": True, "contents_read": False}) as run:
            result = management_service.dispatch(request("software.app.run", {
                "app_id": "directory-tree", "path": "Documents"}), caller="local_cli", env=NATIVE_ENV)
        self.assertTrue(result["ok"])
        run.assert_called_once()
        denied = management_service.dispatch(request("software.app.run", {
            "app_id": "process-monitor", "path": "/etc"}), caller="local_cli", env=NATIVE_ENV)
        self.assertFalse(denied["ok"])
        run.assert_called_once()

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

if __name__ == "__main__":
    unittest.main()
