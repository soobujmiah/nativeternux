from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_presentation
import management_service
import terminal_ui


class TerminalUISharedServiceTests(unittest.TestCase):
    def test_compact_branding_is_available_in_tui_header(self) -> None:
        self.assertEqual(terminal_ui.BRANDING_TAGLINE, "Workstation in your pocket — by Sobuj Miah")
        self.assertEqual(terminal_ui.BRANDING_URL, "soobujmiah.github.io")

    def test_guided_proot_launch_uses_only_native_ternuxx_display(self) -> None:
        prompts = ["files", "", "yes"]
        with mock.patch.object(terminal_ui, "_prompt", side_effect=prompts) as prompt, \
             mock.patch.object(terminal_ui, "_call", return_value={"ok": True}) as call:
            result = terminal_ui._launch_proot_app(mock.Mock())
        self.assertEqual(result, {"ok": True})
        self.assertEqual(call.call_args.args, ("proot.app.launch", {"app_id": "files"}))
        labels = [item.args[1] for item in prompt.call_args_list]
        self.assertIn("Native Ternuxx X11 display", labels[1])
        self.assertNotIn("ternux or ternuxx", " ".join(labels).lower())

    def test_proot_shortcut_change_previews_and_applies_the_exact_confirmed_plan(self) -> None:
        plan = {"plan_id": "a" * 24, "changed": True, "affected_resources": [
            {"path": "xfce/data/applications/ternuxx-proot-files.desktop",
             "before": "absent", "after": "present"}]}
        preview = {"ok": True, "data": plan}
        applied = {"ok": True, "data": {"status": "complete"}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["add", "files", "yes"]), \
             mock.patch.object(terminal_ui, "_call", side_effect=[preview, applied]) as call:
            result = terminal_ui._manage_proot_shortcut(mock.Mock())
        self.assertIs(result, applied)
        call.assert_has_calls([
            mock.call("proot.shortcuts.preview", {"action": "add", "app_id": "files"}),
            mock.call("proot.shortcuts.apply", {
                "action": "add", "app_id": "files", "confirmed": True, "plan_id": "a" * 24,
            }),
        ])

    def test_proot_shortcut_cancel_does_not_apply(self) -> None:
        preview = {"ok": True, "data": {"changed": True, "plan_id": "b" * 24}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["remove", "files", "no"]), \
             mock.patch.object(terminal_ui, "_call", return_value=preview) as call:
            result = terminal_ui._manage_proot_shortcut(mock.Mock())
        self.assertEqual(result["error"]["code"], "cancelled")
        call.assert_called_once_with("proot.shortcuts.preview", {"action": "remove", "app_id": "files"})

    def test_catalog_categories_and_resources_define_navigation(self) -> None:
        with mock.patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr",
                                          "TERMUX_VERSION": "fixture"}):
            result = terminal_ui._call("management.catalog")
        self.assertTrue(result["ok"])
        categories = result["data"]["categories"]
        resources = result["data"]["resources"]
        self.assertTrue(categories)
        self.assertTrue(all(item["category_id"] in {c["id"] for c in categories} for item in resources))
        self.assertIn("native.desktop.session", {item["id"] for item in resources})

    def test_only_unargumented_read_operations_are_inspectable(self) -> None:
        self.assertIn("desktop.status", terminal_ui.READ_WITHOUT_ARGUMENTS)
        self.assertNotIn("desktop.start", terminal_ui.READ_WITHOUT_ARGUMENTS)
        self.assertNotIn("restore.preview", terminal_ui.READ_WITHOUT_ARGUMENTS)

    def test_selected_status_operation_comes_from_catalog_and_read_allowlist(self) -> None:
        resource = {"supported_operations": ["desktop.start", "desktop.status"]}
        self.assertEqual(terminal_ui._selected_status_operation(resource), "desktop.status")
        self.assertIsNone(terminal_ui._selected_status_operation({"supported_operations": ["desktop.start"]}))

    def test_selected_resource_lists_only_implemented_guided_actions(self) -> None:
        managed = next(item for item in management_service.management_catalog.RESOURCES
                       if item["id"] == "network.ssh.managed-8023")
        manual = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "network.ssh.manual-8022")
        managed_actions = terminal_ui._available_action_labels(managed)
        manual_actions = terminal_ui._available_action_labels(manual)
        self.assertIn("start SSH 8023 (preview)", managed_actions)
        self.assertIn("stop SSH 8023 (preview)", managed_actions)
        self.assertFalse(any("start" in item or "stop" in item for item in manual_actions))
        self.assertTrue(any("status" in item for item in manual_actions))

    def test_graphics_action_labels_match_provider_operations(self) -> None:
        native = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "graphics.native")
        debian = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "graphics.debian")
        native_actions = terminal_ui._available_action_labels(native)
        debian_actions = terminal_ui._available_action_labels(debian)
        self.assertIn("verify GLES", native_actions)
        self.assertIn("verify Vulkan", native_actions)
        self.assertIn("select Native backend", native_actions)
        self.assertNotIn("select Native backend", debian_actions)

    def test_cron_resource_exposes_status_and_saved_job_listing_only(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "automation.cron-registry")
        self.assertIn("check status", terminal_ui._available_action_labels(resource))
        self.assertIn("list persisted job definitions", terminal_ui._available_action_labels(resource))
        self.assertIn("view Cron execution history", terminal_ui._available_action_labels(resource))
        result = {"ok": True, "data": {"jobs": []}}
        with mock.patch.object(terminal_ui, "_call", return_value=result) as dispatch:
            self.assertIs(terminal_ui._cron_jobs(), result)
        dispatch.assert_called_once_with("cron.jobs.list")
        history = {"ok": True, "data": {"executions": []}}
        with mock.patch.object(terminal_ui, "_call", return_value=history) as dispatch:
            self.assertIs(terminal_ui._cron_executions(), history)
        dispatch.assert_called_once_with("cron.executions.list", {"limit": 20})

    def test_timezone_action_checks_available_zones_and_confirms_before_saving(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "native.timezone")
        self.assertIn("configure Ternuxx timezone preference", terminal_ui._available_action_labels(resource))
        current = {"ok": True, "data": {"timezone": "Asia/Dhaka"}}
        zones = {"ok": True, "data": {"timezones": ["Asia/Dhaka", "UTC"]}}
        with mock.patch.object(terminal_ui, "_call", side_effect=[current, zones, {"ok": True}]) as dispatch, \
             mock.patch.object(terminal_ui, "_prompt", side_effect=["UTC", "yes"]):
            result = terminal_ui._timezone_action(object())
        self.assertTrue(result["ok"])
        dispatch.assert_has_calls([
            mock.call("timezone.status"), mock.call("timezone.list"),
            mock.call("timezone.set", {"timezone": "UTC"}),
        ])

    def test_timezone_action_rejects_unavailable_zone_without_write(self) -> None:
        current = {"ok": True, "data": {"timezone": "Asia/Dhaka"}}
        zones = {"ok": True, "data": {"timezones": ["Asia/Dhaka"]}}
        with mock.patch.object(terminal_ui, "_call", side_effect=[current, zones]) as dispatch, \
             mock.patch.object(terminal_ui, "_prompt", return_value="../UTC"):
            result = terminal_ui._timezone_action(object())
        self.assertEqual(result["error"]["code"], "timezone_unavailable")
        self.assertEqual(dispatch.call_count, 2)

    def test_operation_history_is_available_only_from_recovery_resource(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "recovery.native-state")
        result = {"ok": True, "data": {"operations": [], "unresolved_count": 0}}
        with mock.patch.object(terminal_ui, "_call", return_value=result) as dispatch:
            self.assertIs(terminal_ui._operation_history(resource), result)
        dispatch.assert_called_once_with("recovery.status")
        with mock.patch.object(terminal_ui, "_call") as dispatch:
            denied = terminal_ui._operation_history({"id": "network.ssh.manual-8022", "supported_operations": ["ssh.inspect"]})
        self.assertEqual(denied["error"]["code"], "history_unavailable")
        dispatch.assert_not_called()

    def test_advanced_detail_lines_render_the_full_operation_history(self) -> None:
        report = {"ok": True, "data": {"operations": [{"operation_id": "a" * 32,
                  "kind": "service.stop", "status": "complete"}]}}
        rendered = "\n".join(terminal_ui._detail_lines(report, 52))
        self.assertIn("operation_id", rendered)
        self.assertIn("service.stop", rendered)
        self.assertIn("complete", rendered)

    def test_monitoring_policy_uses_typed_shared_operation_and_bounds_interval(self) -> None:
        status = {"ok": True, "data": {"enabled": False, "interval_seconds": 300,
                                           "focus_check": False, "activity_launch": False}}
        with mock.patch.object(terminal_ui, "_call", return_value=status) as dispatch, \
             mock.patch.object(terminal_ui, "_prompt", side_effect=["y", "10", "minutes", "n", "n", "yes"]):
            result = terminal_ui._edit_monitor_policy(object())
        self.assertTrue(result["ok"])
        dispatch.assert_any_call("desktop.monitor.configure", {
            "enabled": True, "interval_value": 10, "unit": "minutes",
            "focus_check": False, "activity_launch": False,
        })
        with mock.patch.object(terminal_ui, "_call", return_value=status), \
             mock.patch.object(terminal_ui, "_prompt", side_effect=["y", "10", "n", "n"]):
            invalid = terminal_ui._edit_monitor_policy(object())
        self.assertEqual(invalid["error"]["code"], "invalid_interval")

    def test_desktop_action_requires_visible_resource_and_explicit_confirmation(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "native.desktop.session")
        self.assertIn("desktop.start", resource["supported_operations"])
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["stop", "no"]), \
             mock.patch.object(terminal_ui, "_call") as dispatch:
            result = terminal_ui._desktop_action(object(), resource)
        self.assertEqual(result["error"]["code"], "cancelled")
        dispatch.assert_not_called()
        success = {"ok": True, "data": {"state": "running"}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["start", "yes"]), \
             mock.patch.object(terminal_ui, "_call", return_value=success) as dispatch:
            self.assertIs(terminal_ui._desktop_action(object(), resource), success)
        dispatch.assert_called_once_with("desktop.start")

    def test_managed_ssh_action_previews_and_confirms_only_8023(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "network.ssh.managed-8023")
        preview = {"ok": True, "data": {"requires_confirmation": True,
                   "plan_id": "a" * 64, "impact": "Stops only ternuxx-sshd."}}
        result = {"ok": True, "data": {"status": "stopped"}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["stop", "yes"]), \
             mock.patch.object(terminal_ui, "_call", side_effect=[preview, result]) as dispatch:
            self.assertIs(terminal_ui._managed_ssh_action(object(), resource), result)
        self.assertEqual(dispatch.call_args_list, [
            mock.call("ssh.service.stop", {"confirmed": False, "plan_id": None}),
            mock.call("ssh.service.stop", {"confirmed": True, "plan_id": "a" * 64}),
        ])

    def test_managed_ssh_cancel_does_not_apply_and_manual_8022_stays_read_only(self) -> None:
        managed = next(item for item in management_service.management_catalog.RESOURCES
                       if item["id"] == "network.ssh.managed-8023")
        manual = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "network.ssh.manual-8022")
        preview = {"ok": True, "data": {"requires_confirmation": True,
                   "plan_id": "b" * 64, "impact": "Client connections may close."}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["stop", "no"]), \
             mock.patch.object(terminal_ui, "_call", return_value=preview) as dispatch:
            self.assertEqual(terminal_ui._managed_ssh_action(object(), managed)["error"]["code"], "cancelled")
        dispatch.assert_called_once_with("ssh.service.stop", {"confirmed": False, "plan_id": None})
        with mock.patch.object(terminal_ui, "_prompt") as prompt, mock.patch.object(terminal_ui, "_call") as dispatch:
            self.assertEqual(terminal_ui._managed_ssh_action(object(), manual)["error"]["code"],
                             "externally_managed_resource")
        prompt.assert_not_called(); dispatch.assert_not_called()

    def test_proot_launch_is_provider_aware_and_rejects_unknown_app(self) -> None:
        with mock.patch.object(terminal_ui, "_prompt", return_value="arbitrary-shell"), \
             mock.patch.object(terminal_ui, "_call") as dispatch:
            result = terminal_ui._launch_proot_app(object())
        self.assertEqual(result["error"]["code"], "unknown_proot_app")
        dispatch.assert_not_called()

    def test_compact_screen_contains_category_resources_and_keyboard_help(self) -> None:
        class FakeScreen:
            def __init__(self): self.rows = []
            def erase(self): self.rows.clear()
            def getmaxyx(self): return (14, 100)
            def attron(self, _attr): pass
            def attroff(self, _attr): pass
            def addnstr(self, row, col, value, _limit): self.rows.append((row, col, value))
            def refresh(self): pass
        screen = FakeScreen()
        category = [{"id": "desktop-audio", "name": "Desktop & multimedia"}]
        resources = [{"id": "native.audio.pulseaudio", "category_id": "desktop-audio",
                      "name": "Audio server", "status": "partial", "description": "Shared audio",
                      "supported_operations": ["desktop.status"]}]
        with mock.patch.object(terminal_ui.curses, "color_pair", return_value=0):
            terminal_ui._draw(screen, category, 0, resources, 0, "", {"ok": True}, 0)
        rendered = "\n".join(text for _row, _col, text in screen.rows)
        self.assertIn("Ternuxx Management Center", rendered)
        self.assertIn("Workstation in your pocket — by Sobuj Miah", rendered)
        self.assertIn("soobujmiah.github.io", rendered)
        header = {row: (col, value) for row, col, value in screen.rows if row < 3}
        self.assertEqual(set(header), {0, 1, 2})
        self.assertEqual(header[0][0], (100 - len("Ternuxx Management Center")) // 2)
        self.assertEqual(header[1][0], (100 - len(terminal_ui.BRANDING_TAGLINE)) // 2)
        self.assertEqual(header[2][0], (100 - len(terminal_ui.BRANDING_URL)) // 2)
        self.assertIn("Desktop & multimedia", rendered)
        self.assertIn("Audio server", rendered)
        self.assertIn("Enter status", rendered)
        self.assertIn("Available:", rendered)
        self.assertIn("check status", rendered)

    def test_small_terminal_warning_does_not_overwrite_three_line_header(self) -> None:
        class SmallScreen:
            def __init__(self): self.rows = []
            def erase(self): self.rows.clear()
            def getmaxyx(self): return (8, 60)
            def attron(self, _attr): pass
            def attroff(self, _attr): pass
            def addnstr(self, row, col, value, _limit): self.rows.append((row, col, value))
            def refresh(self): pass
        screen = SmallScreen()
        with mock.patch.object(terminal_ui.curses, "color_pair", return_value=0):
            terminal_ui._draw(screen, [], 0, [], 0, "", None)
        self.assertIn((2, (60 - len(terminal_ui.BRANDING_URL)) // 2, terminal_ui.BRANDING_URL), screen.rows)
        self.assertIn((7, 1, "Resize terminal to at least 34x10"), screen.rows)

    def test_status_vocabulary_is_consistent_and_safe_for_unknown_values(self) -> None:
        self.assertEqual(management_presentation.status_label("planned"), "Planned")
        self.assertEqual(management_presentation.status_label("failed"), "Failed")
        self.assertEqual(management_presentation.status_label(None), "Unknown")

    def test_cli_tui_no_longer_exposes_raw_operation_json_prompt(self) -> None:
        source = (ROOT / "lib" / "terminal_ui.py").read_text()
        self.assertNotIn("JSON arguments", source)
        self.assertNotIn("Operation ID", source)

    def test_noninteractive_launch_fails_with_usage_message(self) -> None:
        with mock.patch.object(terminal_ui.sys, "stdin", mock.Mock(isatty=lambda: False)):
            self.assertEqual(terminal_ui.main(), 2)


if __name__ == "__main__":
    unittest.main()
