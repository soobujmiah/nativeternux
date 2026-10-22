from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import os
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lib"))
import management_desktop_bridge as bridge


class ManagementDesktopBridgeTests(unittest.TestCase):
    def test_optional_terminal_broker_resource_inspects_shared_status(self) -> None:
        catalog = {"ok": True, "data": {"resources": [
            {"id": "proot.interactive-terminal-broker",
             "supported_operations": ["terminal.broker.status"]},
        ]}}
        status = {"ok": True, "data": {"component": "terminal_broker",
                                       "status": "not_running"}}
        with mock.patch.object(bridge, "call", side_effect=lambda operation, args=None:
                               catalog if operation == "management.catalog" else status) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(
                    ["inspect", "proot.interactive-terminal-broker"]), 0)
        self.assertIn(mock.call("terminal.broker.status"), dispatch.call_args_list)

    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {
            "PREFIX": "/data/data/com.termux/files/usr", "TERMUX_VERSION": "test-termux",
            "HOME": "/tmp/ternuxx-management-ui", "TERNUXX_STATE_DIR": "/tmp/ternuxx-management-ui/state",
        })
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

    def test_ssh_key_previews_and_applies_use_shared_service_with_exact_plan(self) -> None:
        preview = {"ok": True, "data": {"plan_id": "a" * 24,
                  "fingerprint": "SHA256:" + "b" * 43}}
        with mock.patch.object(bridge, "call", return_value=preview) as dispatch, \
             redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-key-add-preview", "ssh-ed25519 AAAA test"]), 0)
        dispatch.assert_called_once_with("ssh.keys.add.preview", {"public_key": "ssh-ed25519 AAAA test"})
        fields = output.getvalue().strip().split(chr(9))
        self.assertEqual(fields[:3], ["P", "a" * 24, "SHA256:" + "b" * 43])
        self.assertIn("8022", fields[3]); self.assertIn("8023", fields[3])
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"changed": True}}) as dispatch, \
             redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-key-add-apply", "confirmed", "ssh-ed25519 AAAA test", "a" * 24]), 0)
        dispatch.assert_called_once_with("ssh.keys.add.apply", {
            "public_key": "ssh-ed25519 AAAA test", "confirmed": True, "plan_id": "a" * 24,
        })

    def test_ssh_autostart_status_preview_and_apply_share_typed_service(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"enabled": True}}) as dispatch, \
             redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-autostart-status"]), 0)
        dispatch.assert_called_once_with("ssh.service.autostart.status")
        self.assertEqual(output.getvalue().strip(), "S\ttrue")
        preview = {"ok": True, "data": {"changed": True, "plan_id": "d" * 32,
                   "effect": "next supervisor starts with sshd down; current service unchanged"}}
        with mock.patch.object(bridge, "call", return_value=preview) as dispatch, \
             redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-autostart-preview", "disabled"]), 0)
        dispatch.assert_called_once_with("ssh.service.autostart.preview", {"enabled": False})
        self.assertEqual(output.getvalue().strip().split(chr(9))[:3], ["P", "d" * 32, "false"])
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"enabled": False}}) as dispatch, \
             redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-autostart-apply", "confirmed", "false", "d" * 32]), 0)
        dispatch.assert_called_once_with("ssh.service.autostart.apply", {
            "enabled": False, "confirmed": True, "plan_id": "d" * 32})

    def test_ssh_wakelock_policy_bridge_uses_shared_preview_and_apply(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
                "persistent_lease_enabled": True}}) as dispatch, redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-wakelock-status"]), 0)
        dispatch.assert_called_once_with("wakelock.ssh-policy.status")
        self.assertEqual(output.getvalue().strip(), "S\ttrue")
        preview = {"ok": True, "data": {"changed": True, "plan_id": "e" * 32,
                   "effect": "current SSH lease remains unchanged"}}
        with mock.patch.object(bridge, "call", return_value=preview) as dispatch, redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-wakelock-preview", "disabled"]), 0)
        dispatch.assert_called_once_with("wakelock.ssh-policy.preview", {"enabled": False})
        self.assertEqual(output.getvalue().strip().split(chr(9))[:3], ["P", "e" * 32, "false"])
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"status": "updated"}}) as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-wakelock-apply", "confirmed", "false", "e" * 32]), 0)
        dispatch.assert_called_once_with("wakelock.ssh-policy.apply", {
            "enabled": False, "confirmed": True, "plan_id": "e" * 32})

    def test_ssh_autostart_apply_rejects_malformed_plan(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-autostart-apply", "confirmed", "false", "bad"]), 2)
        dispatch.assert_not_called()

    def test_native_ssh_client_key_preview_and_apply_use_exact_shared_plan(self) -> None:
        preview = {"ok": True, "data": {"changed": True, "plan_id": "c" * 32,
                   "name": "recovery8023", "private_key_path": "/tmp/native/.ssh/ternuxx-keys/recovery8023"}}
        with mock.patch.object(bridge, "call", return_value=preview) as dispatch, \
             redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-client-key-preview", "recovery8023"]), 0)
        dispatch.assert_called_once_with("ssh.client-key.create.preview", {"name": "recovery8023"})
        fields = output.getvalue().strip().split(chr(9))
        self.assertEqual(fields[:4], ["P", "c" * 32, "recovery8023", "/tmp/native/.ssh/ternuxx-keys/recovery8023"])
        self.assertIn("not enrolled", fields[4])
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"created": True}}) as dispatch, \
             redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-client-key-apply", "confirmed", "recovery8023", "c" * 32]), 0)
        dispatch.assert_called_once_with("ssh.client-key.create.apply", {
            "name": "recovery8023", "confirmed": True, "plan_id": "c" * 32,
        })

    def test_native_ssh_client_key_apply_rejects_malformed_plan_before_dispatch(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-client-key-apply", "confirmed", "recovery8023", "bad"]), 2)
        dispatch.assert_not_called()

    def test_ssh_key_apply_rejects_malformed_plan_before_dispatch(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-key-remove-apply", "confirmed", "SHA256:x", "bad"]), 2)
        dispatch.assert_not_called()

    def test_ssh_key_inventory_uses_the_shared_read_operation(self) -> None:
        report = {"ok": True, "data": {"status": "available", "key_count": 1,
                  "keys": [{"key_type": "ssh-ed25519", "fingerprint": "SHA256:abc", "label": "laptop"}]}}
        with mock.patch.object(bridge, "call", return_value=report) as dispatch, \
             redirect_stdout(StringIO()) as output:
            self.assertEqual(bridge.main(["ssh-keys-list"]), 0)
        dispatch.assert_called_once_with("ssh.keys.list")

    def test_catalog_bridge_emits_catalog_categories_and_resources(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = bridge.main(["catalog"])
        self.assertEqual(code, 0)
        lines = output.getvalue().splitlines()
        categories = [line.split(chr(9)) for line in lines if line.startswith("C" + chr(9))]
        resources = [line.split(chr(9)) for line in lines if line.startswith("R" + chr(9))]
        self.assertGreaterEqual(len(categories), 10)
        self.assertIn("native.desktop.session", {row[1] for row in resources})
        self.assertIn("native.gui.activity-monitor", {row[1] for row in resources})
        desktop = next(row for row in resources if row[1] == "native.desktop.session")
        graphics = next(row for row in resources if row[1] == "graphics.native")
        self.assertGreaterEqual(len(desktop), 8)
        self.assertIn("Start desktop", desktop[7])
        self.assertIn("Graphics provider verify", graphics[7])

    def test_inspection_is_selected_from_resource_supported_read_operation(self) -> None:
        output = StringIO()
        original = bridge.call
        with mock.patch.object(bridge, "call", side_effect=lambda op, args=None:
                               original(op, args) if op == "management.catalog" else
                               {"ok": True, "data": {"state": "unknown"}}) as dispatch:
            with redirect_stdout(output):
                result = bridge.main(["inspect", "native.desktop.session"])
        self.assertEqual(result, 0)
        self.assertIn(mock.call("desktop.status"), dispatch.call_args_list)

    def test_acceleration_resource_runs_only_read_only_display_qualification(self) -> None:
        payload = {"ok": True, "data": {"findings": [
            {"id": "NTX-CPU-001"}, {"id": "NTX-GPU-103"}, {"id": "NTX-NPU-001"}]}}
        with mock.patch.object(bridge, "call", return_value=payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                result = bridge.main(["inspect", "native.acceleration.qualification"])
        self.assertEqual(result, 0)
        dispatch.assert_called_once_with("doctor.report", {"graphics": True})
        self.assertIn("NTX-NPU-001", output.getvalue())

    def test_audio_resource_inspection_uses_read_only_doctor_report(self) -> None:
        original = bridge.call
        payload = {"ok": True, "data": {"findings": [
            {"id": "NTX-AUDIO-001", "summary": "ready"}]}}
        with mock.patch.object(bridge, "call", side_effect=lambda op, args=None:
                               original(op, args) if op == "management.catalog" else payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                result = bridge.main(["inspect", "native.audio.pulseaudio"])
        self.assertEqual(result, 0)
        self.assertIn(mock.call("doctor.report", {"graphics": False}), dispatch.call_args_list)
        self.assertIn("NTX-AUDIO-001", output.getvalue())

    def test_health_resource_uses_doctor_report_without_graphics_probe(self) -> None:
        original = bridge.call
        payload = {"ok": True, "data": {"findings": []}}
        with mock.patch.object(bridge, "call", side_effect=lambda op, args=None:
                               original(op, args) if op == "management.catalog" else payload) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["inspect", "native.system.health"]), 0)
        self.assertIn(mock.call("doctor.report", {"graphics": False}), dispatch.call_args_list)

    def test_port_8022_uses_read_only_ssh_inspection(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["inspect", "network.ssh.manual-8022"]), 0)
        dispatch.assert_called_once_with("ssh.inspect")

    def test_gui_monitoring_status_only_reads_policy(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "enabled": False, "interval_seconds": 300, "focus_check": False, "activity_launch": False,
        }}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["monitor"]), 0)
        dispatch.assert_called_once_with("desktop.monitor.status")
        self.assertIn("M" + chr(9) + "False" + chr(9) + "300" + chr(9) + "False" + chr(9) + "False", output.getvalue())

    def test_cron_bridge_lists_registry_through_shared_service(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"jobs": []}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["cron-jobs"]), 0)
        dispatch.assert_called_once_with("cron.jobs.list")
        self.assertIn("Jobs: None", output.getvalue())

    def test_cron_preview_and_apply_bridge_use_shared_saved_plan(self) -> None:
        preview_result = {"ok": True, "data": {"plan": {
            "plan_id": "a" * 32, "action": "create", "before": None, "after": {"name": "daily"},
        }}}
        with mock.patch.object(bridge, "call", return_value=preview_result) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["cron-preview", "create", "daily", "diagnostics.doctor", "0 8 * * *"]), 0)
        request = dispatch.call_args.args[0]
        self.assertEqual(request, "cron.jobs.mutation.preview")
        self.assertEqual(dispatch.call_args.args[1]["action"], "create")
        self.assertEqual(dispatch.call_args.args[1]["job"]["action_id"], "diagnostics.doctor")
        self.assertIn("P" + chr(9) + "a" * 32, output.getvalue())
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"applied": True}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["cron-apply", "a" * 32]), 0)
        dispatch.assert_called_once_with("cron.jobs.mutation.apply", {"plan_id": "a" * 32, "confirmed": True})

    def test_proot_shortcut_list_bridge_uses_shared_service(self) -> None:
        payload = {"ok": True, "data": {"items": [
            {"id": "files", "name": "Files", "shortcut_state": "installed"}]}}
        with mock.patch.object(bridge, "call", return_value=payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["shortcut-list"]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.list")
        self.assertIn("Shortcut state: Installed", output.getvalue())

    def test_proot_shortcut_sync_rollback_bridge_lists_previews_and_applies_exact_plan(self) -> None:
        rollback_id = "a" * 32
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"rollbacks": [
                {"rollback_id": rollback_id, "created_at": "today", "entry_count": 2,
                 "integrity": "valid", "status": "applied"},
                {"rollback_id": "b" * 32, "integrity": "invalid", "status": "applied"}]}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["shortcut-sync-rollback-list"]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.sync.rollback.list")
        self.assertIn("R" + chr(9) + rollback_id + chr(9) + "today", output.getvalue())
        self.assertNotIn("b" * 32, output.getvalue())
        preview_payload = {"ok": True, "data": {"plan_id": "c" * 24, "rollback_id": rollback_id,
            "changes": [{"action": "restore", "path": "xfce/data/applications/ternuxx-proot-app-files.desktop"}]}}
        with mock.patch.object(bridge, "call", return_value=preview_payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["shortcut-sync-rollback-preview", rollback_id]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.sync.rollback.preview", {"rollback_id": rollback_id})
        self.assertIn("restore", output.getvalue())
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"status": "complete"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["shortcut-sync-rollback-apply", rollback_id, "c" * 24]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.sync.rollback.apply", {
            "rollback_id": rollback_id, "confirmed": True, "plan_id": "c" * 24})

    def test_proot_shortcut_sync_rollback_bridge_rejects_bad_ids(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["shortcut-sync-rollback-preview", "../bad"]), 2)
            self.assertEqual(bridge.main(["shortcut-sync-rollback-apply", "../bad", "x"]), 2)
        dispatch.assert_not_called()

    def test_proot_session_inventory_and_recovery_bridge_use_read_operations(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"sessions": []}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["proot-session-list"]), 0)
        dispatch.assert_called_once_with("proot.sessions.list")
        session_id = "proot-" + "a" * 32
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"state": "unknown"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["proot-session-recovery", session_id]), 0)
        dispatch.assert_called_once_with("proot.recovery.inspect", {"session_id": session_id})

    def test_terminal_picker_bridge_lists_only_owned_running_debian(self) -> None:
        sid="proot-"+"a"*32
        payload={"ok":True,"data":{"sessions":[
            {"session_id":sid,"profile":"debian-interactive","state":"running",
             "ownership":"ternuxx_verified"},
            {"session_id":"proot-"+"b"*32,"profile":"debian-interactive",
             "state":"running","ownership":"unverified"},
            {"session_id":"proot-"+"c"*32,"profile":"isolated-probe",
             "state":"running","ownership":"ternuxx_verified"}]}}
        with mock.patch.object(bridge,"call",return_value=payload) as dispatch:
            output=StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["terminal-session-options"]),0)
        dispatch.assert_called_once_with("proot.sessions.list")
        self.assertEqual(output.getvalue(),"S\t"+sid+"\tDebian aaaaaaaa · Running\n")

    def test_proot_probe_bridge_previews_fixed_profile_and_applies_exact_plan(self) -> None:
        plan_id = "plan-" + "a" * 64
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
                "plan_id": plan_id, "impact": "Starts one bounded headless Debian diagnostic process."}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-probe-preview"]), 0)
        dispatch.assert_called_once_with("proot.start.preview", {"profile": "isolated-probe"})
        self.assertIn("P\t" + plan_id, output.getvalue())
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"state": "running"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["proot-probe-apply", plan_id]), 0)
        dispatch.assert_called_once_with("proot.start", {"profile": "isolated-probe", "confirmed": True,
                                                          "plan_id": plan_id, "timeout_seconds": 300})

    def test_proot_stop_bridge_requires_verified_preview_and_exact_plan(self) -> None:
        session_id = "proot-" + "b" * 32
        plan_id = "plan-" + "c" * 64
        preview = {"ok": True, "data": {"ownership": "ternuxx_verified",
                   "action": "signal_owned_process_group", "signal": "SIGTERM",
                   "scope": "verified_process_group", "impact": "Stop this owned probe.",
                   "plan_id": plan_id, "profile": "isolated-probe"}}
        with mock.patch.object(bridge, "call", return_value=preview) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-session-stop-preview", session_id]), 0)
        dispatch.assert_called_once_with("proot.stop.preview", {"session_id": session_id})
        self.assertIn("P\t" + plan_id, output.getvalue())
        applied = {"ok": True, "data": {"stopped": True, "state": "stopped",
                                             "ownership": "verified", "session_id": session_id}}
        with mock.patch.object(bridge, "call", return_value=applied) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-session-stop-apply", session_id, plan_id]), 0)
        dispatch.assert_called_once_with("proot.stop", {"session_id": session_id,
                                                          "confirmed": True, "plan_id": plan_id})
        self.assertIn("Result: Completed", output.getvalue())
        self.assertIn("State: Stopped", output.getvalue())
        self.assertIn("Ownership: Verified", output.getvalue())
        self.assertNotIn("api_version", output.getvalue())

    def test_interactive_terminal_stop_preview_discloses_hangup_scope(self) -> None:
        session_id="proot-"+"d"*32
        plan_id="plan-"+"e"*64
        preview={"ok":True,"data":{"ownership":"ternuxx_verified",
            "action":"hangup_owned_terminal_session","signal":"SIGHUP",
            "scope":"verified_private_session_job_groups",
            "impact":"Hang up this owned terminal and its verified private-session job groups.",
            "plan_id":plan_id,"profile":"debian-interactive"}}
        with mock.patch.object(bridge,"call",return_value=preview) as dispatch:
            output=StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-session-stop-preview",session_id]),0)
        dispatch.assert_called_once_with("proot.stop.preview",{"session_id":session_id})
        self.assertIn("SIGHUP",output.getvalue())
        self.assertIn("Verified private session job groups",output.getvalue())

    def test_proot_session_bridge_rejects_invalid_ids_before_dispatch(self) -> None:
        for args in (["proot-session-recovery", "../../bad"],
                     ["proot-session-stop-preview", "../../bad"],
                     ["proot-session-stop-apply", "../../bad", "bad"]):
            with self.subTest(args=args), mock.patch.object(bridge, "call") as dispatch:
                with redirect_stdout(StringIO()):
                    self.assertEqual(bridge.main(list(args)), 2)
                dispatch.assert_not_called()

    def test_proot_app_options_use_discovered_friendly_names_and_valid_ids(self) -> None:
        payload = {"ok": True, "data": {"items": [], "desktop_applications": {"items": [
            {"desktop_id": "firefox.desktop", "name": "Firefox ESR", "status": "available"},
            {"desktop_id": "../escape.desktop", "name": "Unsafe", "status": "available"},
            {"desktop_id": "hidden.desktop", "name": "Hidden", "status": "hidden"},
        ]}}}
        with mock.patch.object(bridge, "call", return_value=payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-app-options"]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.list")
        self.assertIn("D\tfirefox.desktop\tFirefox ESR", output.getvalue())
        self.assertNotIn("escape", output.getvalue())
        self.assertNotIn("Hidden", output.getvalue())

    def test_dynamic_proot_launch_bridge_uses_typed_desktop_id(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"desktop_id": "firefox.desktop"}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-app-launch", "desktop:firefox.desktop"]), 0)
        dispatch.assert_called_once_with("proot.app.launch", {"desktop_id": "firefox.desktop"})

    def test_dynamic_proot_launch_bridge_rejects_invalid_desktop_id(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["proot-app-launch", "desktop:../bad"]), 2)
        dispatch.assert_not_called()

    def test_named_proot_launch_bridge_calls_shared_typed_operation(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"app_id": "files"}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-app-launch", "files"]), 0)
        dispatch.assert_called_once_with("proot.app.launch", {"app_id": "files"})
        self.assertIn("App: Files", output.getvalue())

    def test_named_proot_launch_bridge_rejects_unknown_app_before_dispatch(self) -> None:
        with mock.patch.object(bridge, "call") as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["proot-app-launch", "arbitrary-shell-command"]), 2)
        dispatch.assert_not_called()
        self.assertIn("unknown_proot_app", output.getvalue())

    def test_proot_shortcut_preview_emits_exact_review_fields(self) -> None:
        payload = {"ok": True, "data": {"plan_id": "a" * 24, "changed": True,
            "affected_resources": [{"path": "xfce/data/applications/files.desktop",
                                    "before": "absent", "after": "present"}]}}
        with mock.patch.object(bridge, "call", return_value=payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["shortcut-preview", "add", "files"]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.preview", {"action": "add", "app_id": "files"})
        self.assertIn("P\t" + "a" * 24 + "\ttrue\t", output.getvalue())

    def test_proot_shortcut_apply_requires_catalog_id_and_exact_plan(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"status": "complete"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["shortcut-apply", "remove", "files", "b" * 24]), 0)
        dispatch.assert_called_once_with("proot.shortcuts.apply", {
            "action": "remove", "app_id": "files", "confirmed": True, "plan_id": "b" * 24,
        })
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["shortcut-apply", "add", "unknown", "b" * 24]), 2)
        dispatch.assert_not_called()

    def test_ssh_key_rollback_bridge_lists_and_uses_exact_preview(self) -> None:
        listing = {"ok": True, "data": {"entries": [{"rollback_id": "a" * 32,
            "fingerprint": "SHA256:" + "b" * 43, "action": "remove", "status": "applied"}]}}
        with mock.patch.object(bridge, "call", return_value=listing) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["ssh-key-rollback-list"]), 0)
        dispatch.assert_called_once_with("ssh.keys.rollback.list")
        self.assertTrue(output.getvalue().startswith("R\t" + "a" * 32))
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
                "plan_id": "c" * 24, "rollback_id": "a" * 32,
                "effect": "Restore exact prior file."}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["ssh-key-rollback-preview", "a" * 32]), 0)
        dispatch.assert_called_once_with("ssh.keys.rollback.preview", {"rollback_id": "a" * 32})
        self.assertTrue(output.getvalue().startswith("P\t" + "c" * 24 + "\t" + "a" * 32))

    def test_timezone_set_bridge_calls_typed_preference_operation(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"timezone": "UTC"}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["timezone-set", "UTC"]), 0)
        dispatch.assert_called_once_with("timezone.set", {"timezone": "UTC"})
        self.assertIn("UTC", output.getvalue())

    def test_cron_history_bridge_reads_bounded_shared_execution_history(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"executions": []}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["cron-history"]), 0)
        dispatch.assert_called_once_with("cron.executions.list", {"limit": 20})
        self.assertIn("Executions: None", output.getvalue())

    def test_history_bridge_reads_the_shared_recovery_journal(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "operations": [], "unresolved_count": 0, "read_only": True}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["history"]), 0)
        dispatch.assert_called_once_with("recovery.status")
        self.assertIn("Items needing attention: 0", output.getvalue())

    def test_history_bridge_hides_internal_ids_and_formats_timestamps(self) -> None:
        payload = {"ok": True, "data": {"unresolved_count": 0, "operations": [{
            "operation_id": "a" * 32, "kind": "service.deploy", "status": "complete",
            "created_at": "2026-10-18T23:04:19.753138+00:00",
            "updated_at": "2026-10-18T23:04:19.782579+00:00",
            "detail": "Definition deployed; rollback=" + "b" * 64,
        }]}}
        with mock.patch.object(bridge, "call", return_value=payload) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["history"]), 0)
        dispatch.assert_called_once_with("recovery.status")
        rendered = output.getvalue()
        self.assertIn("Deploy service definition - Complete", rendered)
        self.assertIn("Items needing attention: 0", rendered)
        self.assertIn("Definition deployed", rendered)
        self.assertIn("reference hidden", rendered)
        self.assertNotIn("2026-10-18T", rendered)
        self.assertNotIn("b" * 32, rendered)
        self.assertNotIn("a" * 32, rendered)

    def test_managed_ssh_preview_is_typed_and_targets_only_8023(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "plan_id": "c" * 64, "requires_confirmation": True,
            "impact": "Starts only the fixed managed unit."}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["ssh-preview-start"]), 0)
        dispatch.assert_called_once_with("ssh.service.start", {"confirmed": False, "plan_id": None})
        self.assertIn("P\t" + "c" * 64 + "\ttrue", output.getvalue())

    def test_managed_ssh_restart_bridge_uses_shared_preview_and_apply(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "plan_id": "e" * 64, "requires_confirmation": True,
            "impact": "Restart may disconnect 8023 clients."}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["ssh-preview-restart"]), 0)
        dispatch.assert_called_once_with("ssh.service.restart", {"confirmed": False, "plan_id": None})
        self.assertIn("P\t" + "e" * 64 + "\ttrue", output.getvalue())
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"status": "running"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["ssh-apply-restart", "confirmed", "e" * 64]), 0)
        dispatch.assert_called_once_with("ssh.service.restart", {"confirmed": True, "plan_id": "e" * 64})

    def test_managed_ssh_apply_requires_exact_plan_and_confirmation(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {"status": "stopped"}}) as dispatch:
            with redirect_stdout(StringIO()):
                self.assertEqual(bridge.main(["ssh-apply-stop", "confirmed", "d" * 64]), 0)
        dispatch.assert_called_once_with("ssh.service.stop", {"confirmed": True, "plan_id": "d" * 64})
        with mock.patch.object(bridge, "call") as dispatch, redirect_stdout(StringIO()):
            self.assertEqual(bridge.main(["ssh-apply-stop", "confirmed", "bad-plan"]), 2)
        dispatch.assert_not_called()

    def test_unknown_bridge_action_cannot_become_a_shell_command(self) -> None:
        error = StringIO()
        with mock.patch("sys.stderr", error):
            self.assertEqual(bridge.main(["run", "arbitrary command"]), 2)
        self.assertIn("Unsupported typed management action", error.getvalue())


if __name__ == "__main__":
    unittest.main()
