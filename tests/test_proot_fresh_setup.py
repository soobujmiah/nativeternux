"""Tests for isolated, preview-bound fresh Debian provisioning."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_fresh_setup


class FreshProotSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-fresh-proot-")
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.prefix = self.base / "prefix"
        self.containers = self.prefix / "var/lib/proot-distro/containers"
        self.containers.mkdir(parents=True)
        self.repo = self.base / "repo"
        (self.repo / "config/proot").mkdir(parents=True)
        shutil.copyfile(ROOT / "config/proot/debian-trixie.json",
                        self.repo / "config/proot/debian-trixie.json")
        self.state = self.home / ".local/share/ternuxx"
        self.state.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def _fixture_runner(self, calls):
        def run(args, **kwargs):
            calls.append(args)
            if args[1] == "install":
                alias = args[args.index("--name") + 1]
                root = self.containers / alias / "rootfs"
                (root / "etc").mkdir(parents=True)
                (root / "etc/os-release").write_text("ID=debian\nVERSION_CODENAME=trixie\n")
                spec = json.loads((self.repo / "config/proot/debian-trixie.json").read_text())["fresh_install"]
                (root.parent / "manifest.json").write_text(json.dumps({
                    "image_ref": spec["base_image"], "arch": "aarch64",
                    "manifest": {"config": {"digest": spec["config_digest"], "size": spec["config_size"]},
                                 "layers": [{"digest": spec["layer_digest"], "size": spec["layer_size"]}]},
                    "image_config": {"architecture": "arm64", "created": spec["image_created"]}}))
            if "/usr/bin/dpkg-query" in args:
                return SimpleNamespace(returncode=0, stdout=self._version_output())
            return SimpleNamespace(returncode=0)
        return run

    def _version_output(self):
        manifest = json.loads((self.repo / "config/proot/debian-trixie.json").read_text())
        return "".join("ii \t" + p + "=1.0\n" for p in proot_fresh_setup._packages(manifest))

    def test_unowned_destination_does_not_become_resumable_after_refusal(self):
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            plan = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
            (self.containers / "debian/rootfs").mkdir(parents=True)
            marker = self.containers / "debian/rootfs/owner-data"
            marker.write_text("preserve")
            with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
                 patch.object(proot_fresh_setup, "_verify_base_image"):
                for attempt in range(2):
                    with self.subTest(attempt=attempt), self.assertRaises(proot_fresh_setup.FreshSetupError):
                        proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                            home=str(self.home), state_dir=str(self.state), user="sbj",
                            plan_id=plan["plan_id"], confirmed=True,
                            runner=lambda *_a, **_k: self.fail("must never enter unowned guest"))
            self.assertEqual(marker.read_text(), "preserve")

    def test_apt_failure_cannot_fall_through_to_user_creation(self):
        calls = []
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False), \
             patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"):
            plan = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
            proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj",
                plan_id=plan["plan_id"], confirmed=True, runner=self._fixture_runner(calls))
        script = next(args[-1] for args in calls if "/bin/bash" in args)
        # Run only the package/user tail, with every external command stubbed.
        # The guest APT source edits are never executed on the host.
        tail = script[script.index("apt-get -o Acquire::Check-Valid-Until=false update"):]
        tail = tail.replace("/etc/locale.gen", str(self.base / "locale.gen"))
        stub = self.base / "stub"
        stub.mkdir()
        for command in ("apt-get", "getent", "useradd", "usermod", "update-locale", "locale-gen"):
            path = stub / command
            body = "#!/bin/sh\n"
            if command == "apt-get": body += "exit 37\n"
            elif command == "getent": body += "exit 1\n"
            elif command == "useradd": body += 'touch "$FRESH_TEST_MARKER"\n'
            else: body += "exit 0\n"
            path.write_text(body);path.chmod(0o700)
        marker = self.base / "user-created"
        result = subprocess.run(["bash", "-c", "set -eu\n" + tail],
            env=dict(os.environ, PATH=str(stub)+":"+os.environ["PATH"], FRESH_TEST_MARKER=str(marker)))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())

    def test_replay_alias_coexists_with_working_debian_and_rejects_arbitrary_names(self):
        existing = self.containers / "debian/rootfs"
        existing.mkdir(parents=True)
        marker = existing / "owner-data"
        marker.write_text("preserve")
        calls = []
        alias = "ternuxx-replay-test"
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False), \
             patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"):
            plan = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj", alias=alias)
            result = proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj", alias=alias,
                plan_id=plan["plan_id"], confirmed=True, runner=self._fixture_runner(calls))
        self.assertEqual(result["record"]["alias"], alias)
        self.assertEqual(marker.read_text(), "preserve")
        self.assertFalse((self.state / "proot-setup/fresh-provider.json").exists())
        for bad in ("ubuntu", "../debian", "ternuxx-replay-", "ternuxx-replay-../debian", "debian/other"):
            with self.subTest(alias=bad), self.assertRaises(proot_fresh_setup.FreshSetupError):
                proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj", alias=bad)

    def test_root_replacement_after_failed_packages_is_not_resumed(self):
        calls = []
        base_runner = self._fixture_runner(calls)
        def fail_packages(args, **kwargs):
            if args[1] == "login":
                return SimpleNamespace(returncode=1)
            return base_runner(args, **kwargs)
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False), \
             patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"):
            plan = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
            with self.assertRaises(proot_fresh_setup.FreshSetupError):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=plan["plan_id"], confirmed=True, runner=fail_packages)
            root = self.containers / "debian/rootfs"
            root.rename(self.containers / "debian/original-rootfs")
            root.mkdir()
            (root / "owner-data").write_text("preserve")
            with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "identity"):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=plan["plan_id"], confirmed=True,
                    runner=lambda *_a, **_k: self.fail("must not enter replacement"))

    def test_different_previews_for_same_alias_share_install_lock(self):
        calls = []
        base_runner = self._fixture_runner(calls)
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False), \
             patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"):
            first = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
            second = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="other")
            def runner(args, **kwargs):
                if args[1] == "install":
                    with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "another"):
                        proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                            home=str(self.home), state_dir=str(self.state), user="other",
                            plan_id=second["plan_id"], confirmed=True, runner=base_runner)
                return base_runner(args, **kwargs)
            proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj",
                plan_id=first["plan_id"], confirmed=True, runner=runner)

    def test_parent_symlink_is_refused_and_package_inventory_is_complete(self):
        for output in ("bash=1.0\n", "bash=1.0\\n", "bash=\n", "rc \tbash=1.0\nii \tlocales=2.41\n"):
            with self.subTest(output=output), self.assertRaises(proot_fresh_setup.FreshSetupError):
                proot_fresh_setup._version_inventory(output, ["bash", "locales"])
        proot_fresh_setup._version_inventory("ii \tbash=1:5.2-1+deb13u1\nhi \tlocales=2.41\n", ["bash", "locales"])
        outside = self.base / "outside"
        outside.mkdir(mode=0o700)
        (self.home / "linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "symbolic"):
            proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.home / "linked/state"), user="sbj")
        self.assertEqual(list(outside.iterdir()), [])

    def test_graphics_artifacts_never_follow_symlinks_or_overwrite_other_bytes(self):
        outside = self.base / "owner-data"
        outside.write_bytes(b"preserve")
        target = self.base / "artifact"
        target.symlink_to(outside)
        with self.assertRaises(proot_fresh_setup.FreshSetupError):
            proot_fresh_setup._store_artifact(target, b"replacement")
        self.assertEqual(outside.read_bytes(), b"preserve")
        target.unlink()
        proot_fresh_setup._store_artifact(target, b"verified")
        proot_fresh_setup._store_artifact(target, b"verified")
        with self.assertRaises(proot_fresh_setup.FreshSetupError):
            proot_fresh_setup._store_artifact(target, b"different")
        self.assertEqual(proot_fresh_setup._artifact_bytes(target), b"verified")

    def test_preview_is_private_and_targets_separate_alias(self):
        preview = proot_fresh_setup.preview(
            repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
            state_dir=str(self.state), user="sbj")
        self.assertEqual(preview["operation"]["alias"], "debian")
        self.assertFalse(preview["operation"]["existing_debian_rootfs_changed"])
        self.assertEqual(preview["operation"]["image_pin"], "sha256:913f6706df59a68922d1dd08f78c2476560a8d367897200a6005b00e5f67c2d5")
        self.assertEqual(preview["operation"]["image"], "debian:trixie-20261005")
        saved = self.state / "proot-setup/previews" / f"fresh-{preview['plan_id']}.json"
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.containers / "debian/rootfs").exists())

    def test_apply_creates_only_new_alias_and_records_package_evidence(self):
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            preview = proot_fresh_setup.preview(
                repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                state_dir=str(self.state), user="sbj")
        calls = []
        call_options = []
        def runner(args, **kwargs):
            calls.append(args)
            call_options.append(kwargs)
            if args[1] == "install":
                root = self.containers / "debian/rootfs"
                (root / "etc").mkdir(parents=True)
                (root / "etc/os-release").write_text(
                    "ID=debian\nVERSION_CODENAME=trixie\n")
                (root.parent / "manifest.json").write_text(json.dumps({
                    "image_ref": "debian:trixie-20261005", "arch": "aarch64",
                    "manifest": {"config": {"digest": "sha256:4bb08c595249772893799a9189839e5a94900e8deaa14885896307e562b51e88",
                                              "size": 466},
                                 "layers": [{"digest": "sha256:df9831efb49cab24dec437e8482f2a9ddbd9e239131fa3ffe095dc1492081e1d",
                                             "size": 49761105}]},
                    "image_config": {"architecture": "arm64", "created": "2026-10-05T00:00:00Z"}}))
                return SimpleNamespace(returncode=0)
            if "/usr/bin/dpkg-query" in args:
                return SimpleNamespace(returncode=0, stdout=self._version_output())
            return SimpleNamespace(returncode=0)
        with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
             patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            result = proot_fresh_setup.apply(
                repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                state_dir=str(self.state), user="sbj", plan_id=preview["plan_id"],
                confirmed=True, runner=runner)
        self.assertEqual(result["status"], "installed")
        self.assertTrue(result["record"]["package_versions_recorded"])
        self.assertFalse(result["record"]["turnip_runtime_verified"])
        self.assertTrue(result["record"]["package_versions_file"].endswith("debian-package-versions.txt"))
        self.assertEqual(calls[0][0:6], ["/prefix/bin/proot-distro", "install", "--name",
                                         "debian", "--architecture", "aarch64"])
        self.assertIn("--isolated", calls[1])
        self.assertIn("apt-get install -y --no-install-recommends", calls[1][-1])
        self.assertIn("snapshot.debian.org/archive/debian/20261020T000000Z", calls[1][-1])
        self.assertEqual(calls[1][-3:], ["/bin/bash", "-lc", calls[1][-1]])
        self.assertEqual(call_options[1]["timeout"], proot_fresh_setup.FRESH_CONFIGURATION_TIMEOUT_SECONDS)
        syntax = subprocess.run(["bash", "-n", "-c", calls[1][-1]], check=False)
        self.assertEqual(syntax.returncode, 0)

    def test_failed_package_setup_can_resume_only_with_matching_journal(self):
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            preview = proot_fresh_setup.preview(
                repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                state_dir=str(self.state), user="sbj")
        install_count = 0
        fail_once = True
        def runner(args, **kwargs):
            nonlocal install_count, fail_once
            if args[1] == "install":
                install_count += 1
                root = self.containers / "debian/rootfs"
                (root / "etc").mkdir(parents=True)
                (root / "etc/os-release").write_text("ID=debian\nVERSION_CODENAME=trixie\n")
                (root.parent / "manifest.json").write_text(json.dumps({
                    "image_ref": "debian:trixie-20261005", "arch": "aarch64",
                    "manifest": {"config": {"digest": "sha256:4bb08c595249772893799a9189839e5a94900e8deaa14885896307e562b51e88", "size": 466},
                                 "layers": [{"digest": "sha256:df9831efb49cab24dec437e8482f2a9ddbd9e239131fa3ffe095dc1492081e1d", "size": 49761105}]},
                    "image_config": {"architecture": "arm64", "created": "2026-10-05T00:00:00Z"}}))
            elif "/usr/bin/dpkg-query" in args:
                return SimpleNamespace(returncode=0, stdout=self._version_output())
            elif fail_once:
                fail_once = False
                return SimpleNamespace(returncode=1)
            return SimpleNamespace(returncode=0)
        with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
             patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "package setup failed"):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=preview["plan_id"], confirmed=True, runner=runner)
            result = proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj",
                plan_id=preview["plan_id"], confirmed=True, runner=runner)
        self.assertEqual(install_count, 1)
        self.assertEqual(result["status"], "installed")

    def test_turnip_package_selection_is_previewed_and_hardware_drift_is_rejected(self):
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=True):
            plan = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
        operation = plan["operation"]
        self.assertTrue(operation["graphics"]["kgsl_accessible_at_preview"])
        self.assertTrue(operation["graphics"]["turnip_install_planned"])
        manifest = json.loads(self.repo.joinpath("config/proot/debian-trixie.json").read_text())
        self.assertTrue(set(manifest["graphics"]["hold_packages"]).issubset(set(operation["packages"])))
        with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
             patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "KGSL capability changed"):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=plan["plan_id"], confirmed=True, runner=lambda *_a, **_k: self.fail("must not execute"))

    def test_image_content_mismatch_stops_before_package_configuration(self):
        with patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            preview = proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            if args[1] == "install":
                root = self.containers / "debian/rootfs"
                (root / "etc").mkdir(parents=True)
                (root / "etc/os-release").write_text("ID=debian\nVERSION_CODENAME=trixie\n")
                (root.parent / "manifest.json").write_text(json.dumps({
                    "image_ref": "debian:trixie-20261005", "arch": "aarch64",
                    "manifest": {"config": {"digest": "sha256:4bb08c595249772893799a9189839e5a94900e8deaa14885896307e562b51e88",
                                              "size": 466},
                                 "layers": [{"digest": "sha256:wrong",
                                             "size": 49761105}]},
                    "image_config": {"architecture": "arm64", "created": "2026-10-05T00:00:00Z"}}))
            return SimpleNamespace(returncode=0)
        with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
             patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "does not match the pinned"):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=preview["plan_id"], confirmed=True, runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertIn("install", calls[0])

    def test_existing_debian_rootfs_is_never_overwritten(self):
        root = self.containers / "debian/rootfs"
        root.mkdir(parents=True)
        marker = root / "preserve-me"
        marker.write_text("legacy")
        with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "already exists"):
            proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")
        self.assertEqual(marker.read_text(), "legacy")

    def test_changed_manifest_and_existing_unowned_alias_fail_closed(self):
        preview = proot_fresh_setup.preview(
            repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
            state_dir=str(self.state), user="sbj")
        manifest = self.repo / "config/proot/debian-trixie.json"
        manifest.write_text(manifest.read_text() + " ")
        with patch.object(proot_fresh_setup.shutil, "which", return_value="/prefix/bin/proot-distro"), \
             patch.object(proot_fresh_setup, "_kgsl_accessible", return_value=False):
            with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "differs"):
                proot_fresh_setup.apply(repo_root=str(self.repo), prefix=str(self.prefix),
                    home=str(self.home), state_dir=str(self.state), user="sbj",
                    plan_id=preview["plan_id"], confirmed=True)
        occupied = self.containers / "debian/rootfs"
        occupied.mkdir(parents=True)
        with self.assertRaisesRegex(proot_fresh_setup.FreshSetupError, "already exists"):
            proot_fresh_setup.preview(repo_root=str(self.repo), prefix=str(self.prefix),
                home=str(self.home), state_dir=str(self.state), user="sbj")


if __name__ == "__main__":
    unittest.main()
