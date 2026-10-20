import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import termux_boot_cron
import boot_state_path


class TermuxBootCronTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        (self.home / "ternuxx").mkdir()
        tx = self.home / "ternuxx/tx"
        tx.write_text("#!/bin/sh\nexit 0\n")
        tx.chmod(0o700)
        self.state = self.home / ".local/share/ternuxx"
        self.boot = self.home / ".termux/boot"
        self.app_installed = lambda **_kwargs: {"app": "installed"}
        self.app_unknown = lambda **_kwargs: {"app": "unknown"}

    def test_preview_names_exact_owned_file_and_never_writes(self):
        owner = self.boot / "00-owner-script"
        owner.parent.mkdir(parents=True)
        owner.write_text("preserve me\n")
        result = termux_boot_cron.preview("enable", home=self.home, boot_inspector=self.app_installed)
        self.assertTrue(result["ready"])
        self.assertEqual(result["changes"][0]["path"], str(self.boot / termux_boot_cron.SCRIPT_NAME))
        self.assertEqual(result["changes"][0]["mode"], "0700")
        self.assertFalse((self.boot / termux_boot_cron.SCRIPT_NAME).exists())
        self.assertEqual(owner.read_text(), "preserve me\n")

    def test_enable_requires_confirmed_exact_plan_and_preserves_other_scripts(self):
        self.boot.mkdir(parents=True)
        owner = self.boot / "00-owner-script"
        owner.write_text("keep\n")
        plan = termux_boot_cron.preview("enable", home=self.home, boot_inspector=self.app_installed)
        denied = termux_boot_cron.apply("enable", home=self.home, state_dir=self.state,
                                        confirmed=False, plan_id=plan["plan_id"], boot_inspector=self.app_installed)
        self.assertFalse(denied["changed"])
        self.assertFalse((self.boot / termux_boot_cron.SCRIPT_NAME).exists())
        with self.assertRaisesRegex(termux_boot_cron.BootIntegrationError, "not confirmed"):
            termux_boot_cron.apply("enable", home=self.home, state_dir=self.state,
                                   confirmed=True, plan_id=plan["plan_id"], boot_inspector=self.app_unknown)
        applied = termux_boot_cron.apply("enable", home=self.home, state_dir=self.state,
                                         confirmed=True, plan_id=plan["plan_id"], boot_inspector=self.app_installed)
        target = self.boot / termux_boot_cron.SCRIPT_NAME
        self.assertTrue(applied["changed"])
        self.assertEqual(target.read_bytes(), termux_boot_cron.script_bytes())
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertEqual(owner.read_text(), "keep\n")
        repeated = termux_boot_cron.preview("enable", home=self.home, boot_inspector=self.app_installed)
        self.assertFalse(repeated["requires_confirmation"])
        self.assertFalse(repeated["changes"])

    def test_unknown_package_visibility_is_not_reported_absent(self):
        result = termux_boot_cron.validate(home=self.home, state_dir=self.state,
                                           boot_inspector=self.app_unknown)
        self.assertEqual(result["companion_app"], "unknown")
        self.assertIn("not confirmed installed", result["blockers"][-1])
        self.assertFalse(result["valid"])

    def test_collision_and_symlink_are_never_replaced(self):
        self.boot.mkdir(parents=True)
        target = self.boot / termux_boot_cron.SCRIPT_NAME
        target.write_text("owner data\n")
        target.chmod(0o700)
        with self.assertRaisesRegex(termux_boot_cron.BootIntegrationError, "unrecognized"):
            termux_boot_cron.preview("enable", home=self.home, boot_inspector=self.app_installed)
        target.unlink()
        other = self.home / "private-script"
        other.write_bytes(termux_boot_cron.script_bytes())
        target.symlink_to(other)
        with self.assertRaisesRegex(termux_boot_cron.BootIntegrationError, "unrecognized"):
            termux_boot_cron.preview("disable", home=self.home, boot_inspector=self.app_installed)
        self.assertTrue(other.exists())

    def test_disable_removes_only_verified_managed_script_after_preview(self):
        self.boot.mkdir(parents=True)
        owner = self.boot / "another-user-script"
        owner.write_text("preserve\n")
        target = self.boot / termux_boot_cron.SCRIPT_NAME
        target.write_bytes(termux_boot_cron.script_bytes())
        target.chmod(0o700)
        plan = termux_boot_cron.preview("disable", home=self.home, boot_inspector=self.app_unknown)
        self.assertEqual(plan["changes"][0]["operation"], "remove")
        with self.assertRaisesRegex(termux_boot_cron.BootIntegrationError, "stale"):
            termux_boot_cron.apply("disable", home=self.home, state_dir=self.state,
                                   confirmed=True, plan_id="wrong", boot_inspector=self.app_unknown)
        result = termux_boot_cron.apply("disable", home=self.home, state_dir=self.state,
                                        confirmed=True, plan_id=plan["plan_id"], boot_inspector=self.app_unknown)
        self.assertTrue(result["changed"])
        self.assertFalse(target.exists())
        self.assertEqual(owner.read_text(), "preserve\n")

    def test_status_reports_distinct_configuration_app_and_delivery_states(self):
        result = termux_boot_cron.status(home=self.home, state_dir=self.state,
            boot_inspector=self.app_unknown, scheduler_inspector=lambda _path: {"status": "stopped", "process_alive": False})
        self.assertEqual(result["integration_state"], "integration_not_configured")
        self.assertEqual(result["companion_app"], "unknown")
        self.assertEqual(result["scheduler_state"], "stopped")
        self.assertFalse(result["scheduler_started_by_script"])
        self.assertEqual(result["actual_device_boot_delivery"], "not_yet_verified")

    def test_dedicated_script_uses_only_supported_cron_cli_and_safe_test_guard(self):
        text = termux_boot_cron.script_bytes().decode()
        self.assertIn('"mng", "cron", "start", "--yes"', text)
        self.assertIn("subprocess.run", text)
        self.assertIn("timeout=20", text)
        self.assertIn("TERNUXX_BOOT_SAFE_TEST", text)
        self.assertNotIn('"ssh"', text)
        self.assertNotIn('"proot"', text)
        self.assertNotIn('"desktop"', text)


    def test_repository_boot_script_is_same_as_manager_template(self):
        source = ROOT / "scripts/termux-boot" / termux_boot_cron.SCRIPT_NAME
        self.assertEqual(source.read_bytes(), termux_boot_cron.script_bytes())
        self.assertEqual(source.stat().st_mode & 0o777, 0o700)

    def test_management_authorization_keeps_mutation_narrow(self):
        import management_authorization
        self.assertEqual(management_authorization.required_capability("boot.cron.status"), "diagnostics.read")
        self.assertEqual(management_authorization.required_capability("boot.cron.preview"), "diagnostics.read")
        self.assertEqual(management_authorization.required_capability("boot.cron.enable"), "boot.manage")
        self.assertFalse(management_authorization.authorize("boot.cron.enable", {"diagnostics.read"}))
        self.assertTrue(management_authorization.authorize("boot.cron.enable", {"boot.manage"}))



class BootStateContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-boot-path-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir(mode=0o700)
        self.outside = self.base / "home-extra"
        self.outside.mkdir(mode=0o700)

    def test_relative_absolute_and_missing_nested_state_paths(self):
        for configured in ("relative/state", str(self.home / "absolute" / "nested")):
            with self.subTest(configured=configured):
                home, state = boot_state_path.resolve_private_state(str(self.home), configured)
                fd = boot_state_path.ensure_private_tree(home, state)
                os.close(fd)
                self.assertTrue((state / "cron" / "boot").is_dir())
                self.assertEqual(state.stat().st_mode & 0o077, 0)

    def test_traversal_sibling_prefix_and_home_target_are_rejected(self):
        for configured in ("../home-extra/state", str(self.outside / "state"),
                           str(self.home) + "-extra/state", str(self.home)):
            with self.subTest(configured=configured), self.assertRaises(boot_state_path.StatePathError):
                boot_state_path.resolve_private_state(str(self.home), configured)
        self.assertFalse((self.outside / "state").exists())

    def test_symlink_parent_file_component_and_unsafe_permissions_are_rejected(self):
        (self.home / "link").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(boot_state_path.StatePathError):
            boot_state_path.resolve_private_state(str(self.home), "link/state")
        (self.home / "file").write_text("fixture")
        with self.assertRaises(boot_state_path.StatePathError):
            boot_state_path.resolve_private_state(str(self.home), "file/state")
        unsafe = self.home / "unsafe"
        unsafe.mkdir(mode=0o755)
        unsafe.chmod(0o755)
        with self.assertRaises(boot_state_path.StatePathError):
            boot_state_path.resolve_private_state(str(self.home), "unsafe")

    def test_path_becoming_symlink_after_validation_fails_before_external_write(self):
        home, state = boot_state_path.resolve_private_state(str(self.home), "new/state")
        (self.home / "new").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(boot_state_path.StatePathError):
            boot_state_path.ensure_private_tree(home, state)
        self.assertFalse((self.outside / "state").exists())
        self.assertFalse((self.outside / "cron").exists())

    def test_empty_malformed_and_symlinked_home_are_rejected(self):
        for configured in ("", chr(0) + "bad"):
            with self.subTest(configured=repr(configured)), self.assertRaises(boot_state_path.StatePathError):
                boot_state_path.resolve_private_state(str(self.home), configured)
        alias = self.base / "home-link"
        alias.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(boot_state_path.StatePathError):
            boot_state_path.resolve_private_state(str(alias), "state")



    def test_entrypoint_uses_fixture_only_and_rejects_outside_override(self):
        import shutil
        marker = self.home / ".ternuxx-termux-boot-safe-test"
        marker.write_text("isolated-empty-cron-state-v1\n")
        marker.chmod(0o600)
        (self.home / "ternuxx" / "lib").mkdir(parents=True)
        shutil.copyfile(ROOT / "lib/boot_state_path.py",
                        self.home / "ternuxx/lib/boot_state_path.py")
        tx = self.home / "ternuxx" / "tx"
        tx.write_text("#!" + sys.executable + "\nimport json\nprint(json.dumps({"
            + "'ok': True, 'data': {'started': True, 'status': {'instance_id': 'fixture'}}}))\n")
        tx.chmod(0o700)
        script = ROOT / "scripts/termux-boot" / termux_boot_cron.SCRIPT_NAME
        env = dict(os.environ)
        env.update({"HOME": str(self.home), "TERNUXX_BOOT_SAFE_TEST": "1",
                    "TERNUXX_STATE_DIR": "new/nested/state"})
        env.pop("PREFIX", None)
        result = subprocess.run([sys.executable, str(script)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        private_log = self.home / "new/nested/state/cron/boot/termux-boot-cron.jsonl"
        self.assertTrue(private_log.is_file())
        self.assertEqual((self.home / "new/nested/state").stat().st_mode & 0o077, 0)
        external = self.outside / "escape"
        env["TERNUXX_STATE_DIR"] = str(external)
        result = subprocess.run([sys.executable, str(script)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(external.exists())
        self.assertFalse((self.outside / "cron").exists())
if __name__ == "__main__":
    unittest.main()
