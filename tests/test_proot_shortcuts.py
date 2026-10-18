from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_service  # noqa: E402
import proot_shortcuts  # noqa: E402


class ProotShortcutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-proot-shortcuts-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.repo = Path(self.temp.name) / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        (self.repo / "scripts" / "proot-x11-app.sh").touch()
        (self.repo / "scripts" / "proot-x11-shortcut-manager.sh").touch()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def preview(self, action="add", app_id="terminal"):
        return proot_shortcuts.preview(
            action, app_id, home=str(self.home), prefix="/termux",
            repo_root=str(self.repo), path="/bin",
        )

    def test_list_reports_provider_and_does_not_claim_guest_app_availability(self) -> None:
        result = proot_shortcuts.list_shortcuts(home=str(self.home), prefix="/termux", repo_root=str(self.repo))
        self.assertEqual(result["resource_id"], "proot.x11.shortcuts")
        terminal = next(item for item in result["items"] if item["id"] == "terminal")
        self.assertEqual(terminal["provider"], "proot_debian")
        self.assertEqual(terminal["shortcut_owner"], "native_termux")
        self.assertEqual(terminal["shortcut_state"], "absent")
        self.assertEqual(terminal["application_availability"], "unknown")
        self.assertTrue(result["read_only"])

    def test_add_preview_requires_exact_confirmation_then_writes_owned_file(self) -> None:
        with patch.object(proot_shortcuts, "_available", return_value=True):
            plan = self.preview()
            self.assertTrue(plan["requires_confirmation"])
            self.assertEqual(plan["provider"], "proot_debian")
            self.assertEqual(plan["storage_provider"], "native_termux")
            self.assertEqual(proot_shortcuts.apply(
                "add", "terminal", home=str(self.home), prefix="/termux",
                repo_root=str(self.repo), confirmed=False, plan_id=None,
                path="/bin",
            )["status"], "confirmation_required")
            with self.assertRaisesRegex(proot_shortcuts.ShortcutError, "plan ID"):
                proot_shortcuts.apply(
                    "add", "terminal", home=str(self.home), prefix="/termux",
                    repo_root=str(self.repo), confirmed=True, plan_id="wrong",
                    path="/bin",
                )
            applied = proot_shortcuts.apply(
                "add", "terminal", home=str(self.home), prefix="/termux",
                repo_root=str(self.repo), confirmed=True, plan_id=plan["plan_id"],
                path="/bin",
            )
        self.assertEqual(applied["status"], "complete")
        target = self.home / ".local" / "share" / "applications" / "ternuxx-proot-terminal.desktop"
        text = target.read_text()
        self.assertIn("X-Ternuxx-Managed=true", text)
        self.assertIn("X-Ternuxx-App-ID=terminal", text)
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)
        self.assertIn('management app launch terminal', text)
        self.assertNotIn('proot-x11-app.sh', text)

    def test_stale_preview_is_rejected_and_existing_unowned_file_is_preserved(self) -> None:
        with patch.object(proot_shortcuts, "_available", return_value=True):
            plan = self.preview()
        target = self.home / ".local" / "share" / "applications" / "ternuxx-proot-terminal.desktop"
        target.parent.mkdir(parents=True)
        target.write_text("[Desktop Entry]\nName=My launcher\n")
        with self.assertRaisesRegex(proot_shortcuts.ShortcutError, "non-Ternuxx"):
            proot_shortcuts.apply(
                "add", "terminal", home=str(self.home), prefix="/termux",
                repo_root=str(self.repo), confirmed=True, plan_id=plan["plan_id"],
                path="/bin",
            )
        self.assertEqual(target.read_text(), "[Desktop Entry]\nName=My launcher\n")

    def test_exact_legacy_launcher_is_adopted_but_edits_are_not(self) -> None:
        app_dir = self.home / ".local" / "share" / "applications"
        app_dir.mkdir(parents=True)
        target = app_dir / "ternuxx-proot-shortcut-manager.desktop"
        target.write_bytes(proot_shortcuts._legacy_entry(
            "shortcut-manager", prefix="/termux", repo_root=str(self.repo),
        ))
        listed = proot_shortcuts.list_shortcuts(home=str(self.home), prefix="/termux", repo_root=str(self.repo))
        item = next(row for row in listed["items"] if row["id"] == "shortcut-manager")
        self.assertEqual(item["shortcut_state"], "installed")
        with patch.object(proot_shortcuts, "_available", return_value=True):
            plan = self.preview(app_id="shortcut-manager")
        self.assertTrue(plan["changed"])
        target.write_bytes(target.read_bytes() + b"# user edit\n")
        item = next(row for row in proot_shortcuts.list_shortcuts(
            home=str(self.home), prefix="/termux", repo_root=str(self.repo),
        )["items"] if row["id"] == "shortcut-manager")
        self.assertEqual(item["shortcut_state"], "conflict")
        with self.assertRaises(proot_shortcuts.ShortcutError):
            self.preview(app_id="shortcut-manager")

    def test_remove_only_deletes_owned_shortcut_and_never_stops_apps(self) -> None:
        with patch.object(proot_shortcuts, "_available", return_value=True):
            add = self.preview()
            proot_shortcuts.apply(
                "add", "terminal", home=str(self.home), prefix="/termux",
                repo_root=str(self.repo), confirmed=True, plan_id=add["plan_id"], path="/bin",
            )
        remove = self.preview("remove")
        with self.assertRaises(proot_shortcuts.ShortcutError):
            proot_shortcuts.apply(
                "remove", "terminal", home=str(self.home), prefix="/termux",
                repo_root=str(self.repo), confirmed=True, plan_id="stale", path="/bin",
            )
        result = proot_shortcuts.apply(
            "remove", "terminal", home=str(self.home), prefix="/termux",
            repo_root=str(self.repo), confirmed=True, plan_id=remove["plan_id"], path="/bin",
        )
        self.assertFalse((self.home / ".local" / "share" / "applications" / "ternuxx-proot-terminal.desktop").exists())
        self.assertFalse(result["safety"]["running_apps_stopped"])

    def test_symlinked_target_and_external_xdg_directory_fail_closed(self) -> None:
        app_dir = self.home / ".local" / "share" / "applications"
        app_dir.mkdir(parents=True)
        outside = Path(self.temp.name) / "owned-by-user.desktop"
        outside.write_text("keep")
        (app_dir / "ternuxx-proot-files.desktop").symlink_to(outside)
        with self.assertRaisesRegex(proot_shortcuts.ShortcutError, "symbolic link"):
            proot_shortcuts.list_shortcuts(home=str(self.home), prefix="/termux")
        with self.assertRaisesRegex(proot_shortcuts.ShortcutError, "inside"):
            proot_shortcuts.list_shortcuts(home=str(self.home), prefix="/termux", xdg_data_home=self.temp.name)
        self.assertEqual(outside.read_text(), "keep")

    def test_launch_uses_only_named_catalog_entries_and_reports_visibility_unknown(self) -> None:
        with patch.object(proot_shortcuts.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()) as run:
            result = proot_shortcuts.launch(
                "files", prefix="/termux", repo_root=str(self.repo), env={"DISPLAY": ":1"},
            )
        self.assertEqual(result["resource_id"], "proot.x11.app.files")
        self.assertEqual(result["provider"], "proot_debian")
        self.assertEqual(result["gui_visible"], "unknown")
        self.assertEqual(run.call_args.args[0][1], str(self.repo / "scripts" / "proot-x11-app.sh"))
        with self.assertRaisesRegex(proot_shortcuts.ShortcutError, "unknown"):
            proot_shortcuts.launch("../../shell", prefix="/termux", repo_root=str(self.repo), env={})

    def test_management_service_exposes_shortcut_operations_with_typed_provider_data(self) -> None:
        env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr", "HOME": str(self.home), "PATH": "/bin"}
        request = {"api_version": 1, "request_id": "request-shortcuts-01",
                   "operation": "proot.shortcuts.list", "args": {}}
        result = management_service.dispatch(request, env=env)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["resource_id"], "proot.x11.shortcuts")
        self.assertEqual({item["provider"] for item in result["data"]["items"]}, {"proot_debian"})


if __name__ == "__main__":
    unittest.main()
