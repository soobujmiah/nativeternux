"""Read-only boot profile plan tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import boot_profiles  # noqa: E402


class BootProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"

    def test_cli_only_is_default_and_preview_is_read_only(self):
        result = boot_profiles.preview(
            "cli-only", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr",
        )
        self.assertEqual(result["configured_profile"], "cli-only")
        self.assertTrue(result["ready"])
        self.assertTrue(result["safety"]["read_only"])
        self.assertFalse(result["safety"]["script_installed"])
        self.assertEqual(result["generated_script"].encode("utf-8"), boot_profiles._managed_script("cli-only"))
        self.assertFalse(self.state.exists())

    def test_profile_status_distinguishes_configured_script_identity(self):
        profile_path = self.state / "boot/profile.json"
        script_path = self.home / ".termux/boot" / boot_profiles.BOOT_SCRIPT_NAME
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(json.dumps({
            "schema_version": 1, "owner": "ternuxx", "provider": "native", "profile": "native",
        }))
        profile_path.chmod(0o600)
        script_path.parent.mkdir(parents=True)
        script_path.write_bytes(boot_profiles._managed_script("native"))
        script_path.chmod(0o700)
        args = dict(home=self.home, state_dir=self.state, prefix="/data/data/com.termux/files/usr",
                    which=lambda name: f"/prefix/bin/{name}" if name in {"tx", "termux-x11", "xfce4-session"} else None)

        self.assertEqual(boot_profiles.status(**args)["managed_script_identity"], "match")
        script_path.write_bytes(boot_profiles._legacy_managed_script("native"))
        self.assertEqual(boot_profiles.status(**args)["managed_script_identity"], "legacy_match")
        script_path.write_text("#!/bin/sh\n# changed after configuration\n")
        script_path.chmod(0o700)
        self.assertEqual(boot_profiles.status(**args)["managed_script_identity"], "mismatch")
        script_path.unlink()
        self.assertEqual(boot_profiles.status(**args)["managed_script_identity"], "missing")

    def test_profile_status_marks_unsafe_managed_script_without_following_symlink(self):
        profile_path = self.state / "boot/profile.json"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(json.dumps({
            "schema_version": 1, "owner": "ternuxx", "provider": "native", "profile": "cli-only",
        }))
        profile_path.chmod(0o600)
        script_path = self.home / ".termux/boot" / boot_profiles.BOOT_SCRIPT_NAME
        script_path.parent.mkdir(parents=True)
        outside = self.home / "outside-script"
        outside.write_bytes(boot_profiles._managed_script("cli-only"))
        script_path.symlink_to(outside)
        result = boot_profiles.status(
            home=self.home, state_dir=self.state, prefix="/data/data/com.termux/files/usr",
        )
        self.assertEqual(result["managed_script_identity"], "unsafe")
        self.assertTrue(outside.exists())

    def test_profile_status_reads_default_without_creating_state(self):
        result = boot_profiles.status(
            home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr",
        )
        self.assertEqual(result["requested_profile"], "cli-only")
        self.assertEqual(result["configuration_source"], "default")
        self.assertEqual(result["managed_script_identity"], "not_configured")
        self.assertFalse(self.state.exists())

    def test_native_plan_checks_dependencies_and_separates_gui_visibility(self):
        available = {"tx": "/prefix/bin/tx", "termux-x11": "/prefix/bin/termux-x11",
                     "xfce4-session": "/prefix/bin/xfce4-session"}
        result = boot_profiles.preview(
            "native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", which=available.get,
        )
        self.assertTrue(result["ready"])
        self.assertIn("Termux:Boot delivery", result["readiness_scope"])
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as script:
            script.write(result["generated_script"])
            script.flush()
            syntax = subprocess.run(["bash", "-n", script.name], capture_output=True, text=True, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        self.assertIn('exec "/data/data/com.termux/files/usr/bin/tx" start', result["generated_script"])
        self.assertEqual(result["generated_script"].encode("utf-8"), boot_profiles._managed_script("native"))
        self.assertIn("desktop manager keeps Android Activity launch disabled by default", result["actions"][1])
        self.assertIn("open Termux:X11 manually", result["actions"][1])

        missing = boot_profiles.preview(
            "native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", which=lambda _name: None,
        )
        self.assertFalse(missing["ready"])
        self.assertEqual(len(missing["blockers"]), 3)

    def test_all_profile_previews_match_strict_response_schema(self):
        schema = json.loads((ROOT / "schemas/boot-profile-preview.schema.json").read_text())
        expected = set(schema["properties"])
        for profile in boot_profiles.PROFILES:
            result = boot_profiles.preview(
                profile, home=self.home, state_dir=self.state,
                prefix="/data/data/com.termux/files/usr",
                which=lambda name: f"/prefix/bin/{name}" if name in {"tx", "termux-x11", "xfce4-session"} else None,
            )
            self.assertEqual(set(result), expected)
            self.assertEqual(result["component"], "boot_profile_preview")
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["requested_profile"], profile)
            self.assertEqual(result["configured_profile"], "cli-only")
            self.assertIn(result["configuration_source"], schema["properties"]["configuration_source"]["enum"])
            self.assertIs(result["safety"]["read_only"], True)
            self.assertIs(result["safety"]["boot_config_changed"], False)
            self.assertIs(result["safety"]["existing_proot_touched"], False)

    def test_proot_and_hybrid_fail_closed_without_fallback(self):
        for profile in ("proot", "hybrid"):
            result = boot_profiles.preview(
                profile, home=self.home, state_dir=self.state,
                prefix="/data/data/com.termux/files/usr",
            )
            self.assertFalse(result["ready"])
            self.assertEqual(result["generated_script"], "")
            self.assertFalse(result["safety"]["silent_provider_fallback"])

    def test_invalid_profile_config_and_external_path_are_rejected(self):
        profile_file = self.state / "boot/profile.json"
        profile_file.parent.mkdir(parents=True)
        profile_file.write_text(json.dumps({
            "schema_version": 1, "owner": "other", "provider": "native", "profile": "native",
        }))
        with self.assertRaises(ValueError):
            boot_profiles.selected_profile(home=self.home, state_dir=self.state)
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(ValueError):
                boot_profiles.preview(
                    "cli-only", home=self.home, state_dir=outside,
                    prefix="/data/data/com.termux/files/usr",
                )

    def test_profile_config_symlink_cannot_escape_home(self):
        with tempfile.TemporaryDirectory() as outside:
            boot_dir = self.state / "boot"
            boot_dir.mkdir(parents=True)
            (boot_dir / "profile.json").symlink_to(Path(outside) / "profile.json")
            with self.assertRaises(ValueError):
                boot_profiles.preview(
                    "cli-only", home=self.home, state_dir=self.state,
                    prefix="/data/data/com.termux/files/usr",
                )

    def test_enable_requires_confirmed_boot_app_and_installs_only_owned_files(self):
        available = {"tx": "/prefix/bin/tx", "termux-x11": "/prefix/bin/termux-x11",
                     "xfce4-session": "/prefix/bin/xfce4-session"}
        preview = boot_profiles.enable(
            profile="native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", confirmed=False,
            boot_app_status="installed", which=available.get,
        )
        self.assertTrue(preview["requires_confirmation"])
        self.assertFalse(preview["changed"])
        self.assertFalse((self.home / ".termux").exists())
        self.assertFalse(self.state.exists())

        with self.assertRaisesRegex(ValueError, "Termux:Boot app"):
            boot_profiles.enable(
                profile="native", home=self.home, state_dir=self.state,
                prefix="/data/data/com.termux/files/usr", confirmed=True,
                boot_app_status="unknown", which=available.get,
            )
        self.assertFalse((self.home / ".termux").exists())

        enabled = boot_profiles.enable(
            profile="native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", confirmed=True,
            boot_app_status="installed", which=available.get,
        )
        script = self.home / ".termux/boot/10-ternuxx-profile"
        config = self.state / "boot/profile.json"
        self.assertTrue(enabled["changed"])
        self.assertFalse(enabled["safety"]["read_only"])
        self.assertTrue(enabled["safety"]["script_installed"])
        self.assertTrue(enabled["safety"]["boot_config_changed"])
        self.assertEqual(script.stat().st_mode & 0o777, 0o700)
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(config.read_text())["profile"], "native")
        self.assertEqual((self.home / ".termux/boot").stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads(next((self.state / "operations").glob("*.json")).read_text())["status"], "complete")

        repeated = boot_profiles.enable(
            profile="native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", confirmed=True,
            boot_app_status="installed", which=available.get,
        )
        self.assertFalse(repeated["changed"])
        self.assertEqual(len(list((self.state / "operations").glob("*.json"))), 1)

    def test_disable_is_preview_first_and_preserves_unrelated_boot_files(self):
        available = {"tx": "/prefix/bin/tx", "termux-x11": "/prefix/bin/termux-x11",
                     "xfce4-session": "/prefix/bin/xfce4-session"}
        boot_profiles.enable(
            profile="native", home=self.home, state_dir=self.state,
            prefix="/data/data/com.termux/files/usr", confirmed=True,
            boot_app_status="installed", which=available.get,
        )
        other = self.home / ".termux/boot/00-owner-script"
        other.write_text("# owner file\n")
        preview = boot_profiles.disable(home=self.home, state_dir=self.state, confirmed=False)
        self.assertTrue(preview["requires_confirmation"])
        self.assertFalse(preview["changed"])
        self.assertTrue((self.home / ".termux/boot/10-ternuxx-profile").exists())
        result = boot_profiles.disable(home=self.home, state_dir=self.state, confirmed=True)
        self.assertTrue(result["changed"])
        self.assertTrue(result["safety"]["script_removed"])
        self.assertTrue(other.exists())
        self.assertFalse((self.home / ".termux/boot/10-ternuxx-profile").exists())
        self.assertFalse((self.state / "boot/profile.json").exists())
        records = [json.loads(p.read_text()) for p in (self.state / "operations").glob("*.json")]
        self.assertEqual({record["kind"] for record in records}, {"boot.enable", "boot.disable"})
        self.assertEqual({record["status"] for record in records}, {"complete"})

    def test_enable_rolls_back_partial_write_and_records_failure(self):
        available = {"tx": "/prefix/bin/tx", "termux-x11": "/prefix/bin/termux-x11",
                     "xfce4-session": "/prefix/bin/xfce4-session"}
        real_write = boot_profiles._atomic_write
        def fail_script(path, data, mode):
            if path.name == boot_profiles.BOOT_SCRIPT_NAME:
                raise OSError("fixture write failure")
            real_write(path, data, mode)
        from unittest.mock import patch
        with patch.object(boot_profiles, "_atomic_write", side_effect=fail_script):
            with self.assertRaisesRegex(OSError, "fixture write failure"):
                boot_profiles.enable(
                    profile="native", home=self.home, state_dir=self.state,
                    prefix="/data/data/com.termux/files/usr", confirmed=True,
                    boot_app_status="installed", which=available.get,
                )
        self.assertFalse((self.home / ".termux/boot/10-ternuxx-profile").exists())
        self.assertFalse((self.state / "boot/profile.json").exists())
        record = json.loads(next((self.state / "operations").glob("*.json")).read_text())
        self.assertEqual(record["kind"], "boot.enable")
        self.assertEqual(record["status"], "failed")
        self.assertIn("rollback completed", record["detail"])

    def test_unrecognized_boot_entry_is_never_replaced_or_removed(self):
        boot_dir = self.home / ".termux/boot"
        boot_dir.mkdir(parents=True)
        managed_path = boot_dir / boot_profiles.BOOT_SCRIPT_NAME
        managed_path.write_text("# user script\n")
        available = {"tx": "/prefix/bin/tx", "termux-x11": "/prefix/bin/termux-x11",
                     "xfce4-session": "/prefix/bin/xfce4-session"}
        with self.assertRaisesRegex(ValueError, "unrecognized startup"):
            boot_profiles.enable(
                profile="native", home=self.home, state_dir=self.state,
                prefix="/data/data/com.termux/files/usr", confirmed=True,
                boot_app_status="installed", which=available.get,
            )
        with self.assertRaisesRegex(ValueError, "unrecognized startup"):
            boot_profiles.disable(home=self.home, state_dir=self.state, confirmed=True)
        self.assertEqual(managed_path.read_text(), "# user script\n")

    def test_prefix_injection_rejected(self):
        with self.assertRaises(ValueError):
            boot_profiles.preview(
                "native", home=self.home, state_dir=self.state,
                prefix='/data/data/com.termux/files/usr"; touch /tmp/pwn; echo "',
            )


if __name__ == "__main__":
    unittest.main()
