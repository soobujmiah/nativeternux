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
    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {
            "PREFIX": "/data/data/com.termux/files/usr", "TERMUX_VERSION": "test-termux",
            "HOME": "/tmp/ternuxx-management-ui", "TERNUXX_STATE_DIR": "/tmp/ternuxx-management-ui/state",
        })
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

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
        self.assertIn('"jobs": []', output.getvalue())

    def test_history_bridge_reads_the_shared_recovery_journal(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "operations": [], "unresolved_count": 0, "read_only": True}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["history"]), 0)
        dispatch.assert_called_once_with("recovery.status")
        self.assertIn("unresolved_count", output.getvalue())

    def test_managed_ssh_preview_is_typed_and_targets_only_8023(self) -> None:
        with mock.patch.object(bridge, "call", return_value={"ok": True, "data": {
            "plan_id": "c" * 64, "requires_confirmation": True,
            "impact": "Starts only the fixed managed unit."}}) as dispatch:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(bridge.main(["ssh-preview-start"]), 0)
        dispatch.assert_called_once_with("ssh.service.start", {"confirmed": False, "plan_id": None})
        self.assertIn("P\t" + "c" * 64 + "\ttrue", output.getvalue())

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
