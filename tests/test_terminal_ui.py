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

    def test_stop_preview_preserves_signal_name_for_people(self):
        report=management_presentation.format_report({"ok":True,"data":{
            "signal":"SIGHUP","impact":"Hang up one owned terminal."}})
        self.assertIn("Signal: SIGHUP",report)

    def test_choose_supports_arrow_and_number_selection(self) -> None:
        class MenuScreen:
            def __init__(self, keys): self.keys = iter(keys)
            def erase(self): pass
            def getmaxyx(self): return (12, 60)
            def addnstr(self, row, col, value, limit): pass
            def refresh(self): pass
            def getch(self): return next(self.keys)
        self.assertEqual(terminal_ui._choose(MenuScreen([terminal_ui.curses.KEY_DOWN, 10]),
                         "Choose", [("a", "Alpha"), ("b", "Beta")]), "b")
        self.assertEqual(terminal_ui._choose(MenuScreen([ord("1")]),
                         "Choose", [("a", "Alpha"), ("b", "Beta")]), "a")

    def test_choose_scrolls_to_actions_below_small_screen_and_wraps(self):
        class Screen:
            def __init__(self, keys): self.keys=iter(keys)
            def erase(self): pass
            def getmaxyx(self): return (5, 60)
            def addnstr(self, *args): pass
            def refresh(self): pass
            def getch(self): return next(self.keys)
        options=[(str(i), "Action " + str(i)) for i in range(12)]
        self.assertEqual(terminal_ui._choose(Screen([terminal_ui.curses.KEY_DOWN]*11+[10]), "Choose", options), "11")
        self.assertEqual(terminal_ui._choose(Screen([terminal_ui.curses.KEY_UP,10]), "Choose", options), "11")
        self.assertEqual(terminal_ui._choose(Screen([ord("9")]), "Choose", options), "8")





    def test_compact_branding_is_available_in_tui_header(self) -> None:
        self.assertEqual(terminal_ui.BRANDING_TAGLINE, "Workstation in your pocket — by Sobuj Miah")
        self.assertEqual(terminal_ui.BRANDING_URL, "soobujmiah.github.io")













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

    def test_curated_directory_tree_handoff_uses_one_read_only_shared_operation(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "software.curated-apps")
        self.assertIn("browse curated Native apps", terminal_ui._available_action_labels(resource))
        self.assertIn("software.app.run", resource["supported_operations"])
        apps = {"ok": True, "data": {"apps": [{"id": "directory-tree", "name": "Directory tree",
                "package": "tree", "status": "installed", "installed": True}]}}
        result = {"ok": True, "data": {"output": "folder\n"}}
        with mock.patch.object(terminal_ui, "_call", side_effect=[apps, result]) as dispatch, \
             mock.patch.object(terminal_ui, "_choose", side_effect=["directory-tree", "run"]), \
             mock.patch.object(terminal_ui, "_prompt", return_value="Documents"), \
             mock.patch.object(terminal_ui, "_show_details"):
            self.assertIs(terminal_ui._software_action(object(), resource), result)
        dispatch.assert_has_calls([mock.call("software.apps.list"),
            mock.call("software.app.run", {"app_id": "directory-tree", "path": "Documents"})])

    def test_cpu_inference_resource_has_only_implemented_guided_actions(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "inference.cpu.local")
        labels = terminal_ui._available_action_labels(resource)
        self.assertIn("check CPU inference status", labels)
        self.assertIn("preview pinned model setup", labels)
        self.assertIn("run a bounded CPU prompt", labels)
        self.assertIn("inference.cpu.status", terminal_ui.READ_WITHOUT_ARGUMENTS)

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
        self.assertIn("restart SSH 8023 (preview)", managed_actions)
        self.assertIn("public-key login only; password login is disabled", managed_actions)
        self.assertFalse(any("start" in item or "stop" in item for item in manual_actions))
        self.assertTrue(any("status" in item for item in manual_actions))

    def test_graphics_action_labels_are_native_only(self) -> None:
        native = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "graphics.native")
        labels = terminal_ui._available_action_labels(native)
        self.assertIn("select backend (KGSL experimental)", labels)
        self.assertIn("verify Vulkan", labels)
        self.assertFalse(any("Debian" in label or "PRoot" in label for label in labels))

    def test_cron_resource_exposes_preview_apply_action_and_shared_reads(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "automation.cron-registry")
        self.assertIn("check status", terminal_ui._available_action_labels(resource))
        self.assertIn("list persisted job definitions", terminal_ui._available_action_labels(resource))
        self.assertIn("preview and apply Cron job changes", terminal_ui._available_action_labels(resource))
        self.assertIn("view Cron execution history", terminal_ui._available_action_labels(resource))
        result = {"ok": True, "data": {"jobs": []}}
        with mock.patch.object(terminal_ui, "_call", return_value=result) as dispatch:
            self.assertIs(terminal_ui._cron_jobs(), result)
        dispatch.assert_called_once_with("cron.jobs.list")
        history = {"ok": True, "data": {"executions": []}}
        with mock.patch.object(terminal_ui, "_call", return_value=history) as dispatch:
            self.assertIs(terminal_ui._cron_executions(), history)
        dispatch.assert_called_once_with("cron.executions.list", {"limit": 20})

    def test_cron_guided_create_supports_all_schedule_types_through_shared_preview(self) -> None:
        cases = [
            (["create", "job", "diagnostics.doctor", "cron", "0 8 * * *", "Asia/Dhaka", "yes"],
             "cron", {"expression": "0 8 * * *", "timezone": "Asia/Dhaka"}),
            (["create", "job", "diagnostics.doctor", "interval", "3600", "2026-10-24T00:00:00Z", "yes"],
             "interval", {"interval_seconds": 3600, "anchor_at": "2026-10-24T00:00:00Z"}),
            (["create", "job", "diagnostics.doctor", "calendar", "daily", "08:30", "Asia/Dhaka", "yes"],
             "calendar", {"mode": "daily", "time": "08:30", "timezone": "Asia/Dhaka"}),
            (["create", "job", "diagnostics.doctor", "calendar", "specific", "2099-01-01T08:30:00+06:00", "yes"],
             "calendar", {"mode": "specific", "datetime": "2099-01-01T08:30:00+06:00"}),
            (["create", "job", "diagnostics.doctor", "one_time", "2099-01-01T08:30:00+06:00", "yes"],
             "one_time", {"at": "2099-01-01T08:30:00+06:00"}),
        ]
        preview = {"ok": True, "data": {"plan": {"plan_id": "a" * 32}}}
        applied = {"ok": True, "data": {"applied": True}}
        for prompts, schedule_type, schedule in cases:
            with self.subTest(schedule_type=schedule_type, schedule=schedule), \
                    mock.patch.object(terminal_ui, "_prompt", side_effect=prompts), \
                    mock.patch.object(terminal_ui, "_call", side_effect=[preview, applied]) as dispatch, \
                    mock.patch.object(terminal_ui, "_show_details"):
                self.assertIs(terminal_ui._cron_mutation(object()), applied)
                self.assertEqual(dispatch.call_args_list[0], mock.call("cron.jobs.mutation.preview", {
                    "action": "create", "name": "job", "action_id": "diagnostics.doctor",
                    "schedule_type": schedule_type, "schedule": schedule}))

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
        self.assertIn("Action: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", rendered)
        self.assertIn("Service stop", rendered)
        self.assertIn("Complete", rendered)

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
        with mock.patch.object(terminal_ui, "_choose", return_value="stop"), \
             mock.patch.object(terminal_ui, "_prompt", return_value="no"), \
             mock.patch.object(terminal_ui, "_call") as dispatch:
            result = terminal_ui._desktop_action(object(), resource)
        self.assertEqual(result["error"]["code"], "cancelled")
        dispatch.assert_not_called()
        success = {"ok": True, "data": {"state": "running"}}
        with mock.patch.object(terminal_ui, "_choose", return_value="start"), \
             mock.patch.object(terminal_ui, "_prompt", return_value="yes"), \
             mock.patch.object(terminal_ui, "_call", return_value=success) as dispatch:
            self.assertIs(terminal_ui._desktop_action(object(), resource), success)
        dispatch.assert_called_once_with("desktop.start")

    def test_managed_ssh_action_previews_and_confirms_only_8023(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "network.ssh.managed-8023")
        preview = {"ok": True, "data": {"requires_confirmation": True,
                   "plan_id": "a" * 64, "impact": "Stops only ternuxx-sshd."}}
        result = {"ok": True, "data": {"status": "stopped"}}
        with mock.patch.object(terminal_ui, "_choose", return_value="restart"), \
             mock.patch.object(terminal_ui, "_prompt", return_value="yes"), \
             mock.patch.object(terminal_ui, "_call", side_effect=[preview, result]) as dispatch:
            self.assertIs(terminal_ui._managed_ssh_action(object(), resource), result)
        self.assertEqual(dispatch.call_args_list, [
            mock.call("ssh.service.restart", {"confirmed": False, "plan_id": None}),
            mock.call("ssh.service.restart", {"confirmed": True, "plan_id": "a" * 64}),
        ])

    def test_managed_ssh_action_labels_include_only_supported_key_controls(self) -> None:
        import terminal_ui
        resource = {"id": "network.ssh.managed-8023", "supported_operations": [
            "ssh.keys.list", "ssh.keys.add.preview", "ssh.keys.remove.preview",
            "ssh.service.start"]}
        labels = terminal_ui._available_action_labels(resource)
        self.assertIn("public-key login only; password login is disabled", labels)
        self.assertIn("start SSH 8023 (preview)", labels)

    def test_managed_ssh_key_inventory_is_read_only(self) -> None:
        resource = next(item for item in management_service.management_catalog.RESOURCES
                        if item["id"] == "network.ssh.managed-8023")
        expected = {"ok": True, "data": {"key_count": 0}}
        with mock.patch.object(terminal_ui, "_choose", return_value="keys"), \
             mock.patch.object(terminal_ui, "_call", return_value=expected) as call:
            self.assertIs(terminal_ui._managed_ssh_action(object(), resource), expected)
        call.assert_called_once_with("ssh.keys.list")

    def test_managed_ssh_cancel_does_not_apply_and_manual_8022_stays_read_only(self) -> None:
        managed = next(item for item in management_service.management_catalog.RESOURCES
                       if item["id"] == "network.ssh.managed-8023")
        manual = next(item for item in management_service.management_catalog.RESOURCES
                      if item["id"] == "network.ssh.manual-8022")
        preview = {"ok": True, "data": {"requires_confirmation": True,
                   "plan_id": "b" * 64, "impact": "Client connections may close."}}
        with mock.patch.object(terminal_ui, "_choose", return_value="stop"), \
             mock.patch.object(terminal_ui, "_prompt", return_value="no"), \
             mock.patch.object(terminal_ui, "_call", return_value=preview) as dispatch:
            self.assertEqual(terminal_ui._managed_ssh_action(object(), managed)["error"]["code"], "cancelled")
        dispatch.assert_called_once_with("ssh.service.stop", {"confirmed": False, "plan_id": None})
        with mock.patch.object(terminal_ui, "_prompt") as prompt, mock.patch.object(terminal_ui, "_call") as dispatch:
            self.assertEqual(terminal_ui._managed_ssh_action(object(), manual)["error"]["code"],
                             "externally_managed_resource")
        prompt.assert_not_called(); dispatch.assert_not_called()



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
        self.assertIn("implemented", rendered)
        self.assertIn("check status", rendered)
        rows = {row: value for row, _col, value in screen.rows}
        self.assertTrue(rows[3].startswith("─"))
        self.assertIn("Desktop & multimedia", rows[4])
        self.assertTrue(rows[5].startswith("Available:"))
        self.assertTrue(rows[6].startswith("Search:"))
        self.assertTrue(rows[7].startswith("─"))
        self.assertTrue(rows[8].startswith("Actions ·"))
        self.assertIn("Audio server", rows[9])

    def test_tui_action_and_feedback_changes_keep_resource_list_anchor_fixed(self) -> None:
        class Screen:
            def __init__(self): self.rows = []
            def erase(self): self.rows.clear()
            def getmaxyx(self): return (24, 100)
            def attron(self, _attr): pass
            def attroff(self, _attr): pass
            def addnstr(self, row, col, value, _limit): self.rows.append((row, value))
            def refresh(self): pass
        screen = Screen()
        category = [{"id": "x", "name": "System"}]
        resource = {"id": "native.system.health", "category_id": "x", "name": "Health",
                    "status": "implemented", "description": "Health", "supported_operations": ["management.logs.list"]}
        with mock.patch.object(terminal_ui.curses, "color_pair", return_value=0):
            terminal_ui._draw(screen, category, 0, [resource], 0, "", None)
            first = min(row for row, text in screen.rows if "Health" in text)
            terminal_ui._draw(screen, category, 0, [resource], 0, "", {"ok": True, "data": {"details": "x" * 300}}, 0)
            second = min(row for row, text in screen.rows if "Health" in text)
        self.assertEqual(first, second)

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
        self.assertTrue(any("Make the terminal wider or reduce zoom" in value
                            for _row, _col, value in screen.rows))

    def test_narrow_tui_wraps_resource_text_and_uses_colored_footer_groups(self) -> None:
        class NarrowScreen:
            def __init__(self): self.rows = []
            def erase(self): self.rows.clear()
            def getmaxyx(self): return (30, 40)
            def attron(self, _attr): pass
            def attroff(self, _attr): pass
            def addnstr(self, row, col, value, _limit): self.rows.append((row, col, value))
            def refresh(self): pass
        screen = NarrowScreen()
        category = [{"id": "desktop-audio", "name": "Desktop & multimedia"}]
        name = "Very long graphics and desktop management resource name wraps safely"
        resources = [{"id": "long-resource", "category_id": "desktop-audio", "name": name,
                      "status": "implemented", "description": "A long item", "supported_operations": []}]
        with mock.patch.object(terminal_ui.curses, "color_pair", return_value=0):
            terminal_ui._draw(screen, category, 0, resources, 0, "", None)
        rendered = " ".join(value for _row, _col, value in screen.rows)
        for word in name.split():
            self.assertIn(word, rendered)
        footer = terminal_ui._footer_layout(40)
        self.assertGreater(len(footer), 1)
        self.assertGreaterEqual(len({color for line in footer for _text, color in line}), 4)
        source = (ROOT / "lib" / "terminal_ui.py").read_text()
        draw_source = source.split("def _draw(", 1)[1].split("def _detail_lines", 1)[0]
        self.assertNotIn("A_BOLD", draw_source)

    def test_status_vocabulary_is_consistent_and_safe_for_unknown_values(self) -> None:
        self.assertEqual(management_presentation.status_label("planned"), "Planned")
        self.assertEqual(management_presentation.status_label("failed"), "Failed")
        self.assertEqual(management_presentation.status_label(None), "Unknown")

    def test_human_report_labels_states_and_hides_credential_material(self) -> None:
        report = management_presentation.format_report({
            "ok": True,
            "data": {"status": "running", "boot_status": "disabled-by-default",
                     "private_key": "never show this", "nested": [{"ownership": "ternuxx_verified"}]},
        })
        self.assertIn("Status: Running", report)
        self.assertIn("Boot status: Off by default", report)
        self.assertIn("Verified as managed by Ternuxx", report)
        self.assertNotIn("never show this", report)

    def test_human_report_preserves_paths_and_labels_lists_and_operations(self) -> None:
        path = "/home/example/.local/share/ternuxx/log/gui-monitoring.log"
        url = "https://example.test/one-time_code"
        report = management_presentation.format_report({
            "operation": "desktop.monitor.status",
            "data": {"log_path": path, "url": url, "interval_bounds_seconds": [30, 86400]}})
        self.assertIn(path, report)
        self.assertIn(url, report)
        self.assertIn("Operation: Activity monitoring policy", report)
        self.assertIn("Interval bounds seconds:", report)

    def test_human_report_explains_status_unavailable_without_machine_code(self) -> None:
        report = management_presentation.format_report({
            "ok": False, "error": {"code": "live_status_unavailable"},
        })
        self.assertIn("Result: Needs attention", report)
        self.assertIn("No live status check is available for this item.", report)
        self.assertNotIn("live_status_unavailable", report)

    def test_boot_enable_previews_profile_and_requires_explicit_confirmation(self) -> None:
        calls = []
        preview = {"ok": True, "data": {"ready": True, "profile": "native"}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["enable", "native", "yes"]), \
             mock.patch.object(terminal_ui, "_call", side_effect=lambda op, args=None:
                               calls.append((op, args)) or (preview if op.endswith("preview") else {"ok": True})), \
             mock.patch.object(terminal_ui, "_show_details"):
            result = terminal_ui._boot_action(mock.Mock())
        self.assertTrue(result["ok"])
        self.assertEqual(calls, [
            ("boot.profile.preview", {"profile": "native"}),
            ("boot.enable", {"profile": "native", "confirmed": True}),
        ])

    def test_boot_enable_does_not_apply_profile_when_preview_is_not_ready(self) -> None:
        calls = []
        preview = {"ok": True, "data": {"ready": False, "blockers": ["Termux:X11 unavailable"]}}
        with mock.patch.object(terminal_ui, "_prompt", side_effect=["enable", "native"]), \
             mock.patch.object(terminal_ui, "_call", side_effect=lambda op, args=None: calls.append(op) or preview):
            result = terminal_ui._boot_action(mock.Mock())
        self.assertEqual(result, preview)
        self.assertEqual(calls, ["boot.profile.preview"])

    def test_cli_tui_no_longer_exposes_raw_operation_json_prompt(self) -> None:
        source = (ROOT / "lib" / "terminal_ui.py").read_text()
        self.assertNotIn("JSON arguments", source)
        self.assertNotIn("Operation ID", source)

    def test_noninteractive_launch_fails_with_usage_message(self) -> None:
        with mock.patch.object(terminal_ui.sys, "stdin", mock.Mock(isatty=lambda: False)):
            self.assertEqual(terminal_ui.main(), 2)


if __name__ == "__main__":
    unittest.main()
