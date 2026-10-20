"""Tests for isolated, preview-bound fresh Debian provisioning."""
from __future__ import annotations

import json
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
        def runner(args, **kwargs):
            calls.append(args)
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
                return SimpleNamespace(returncode=0, stdout="bash=5.2\\n")
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
                (root / "etc/os-release").write_text("ID=debian\\nVERSION_CODENAME=trixie\\n")
                (root.parent / "manifest.json").write_text(json.dumps({
                    "image_ref": "debian:trixie-20261005", "arch": "aarch64",
                    "manifest": {"config": {"digest": "sha256:4bb08c595249772893799a9189839e5a94900e8deaa14885896307e562b51e88", "size": 466},
                                 "layers": [{"digest": "sha256:df9831efb49cab24dec437e8482f2a9ddbd9e239131fa3ffe095dc1492081e1d", "size": 49761105}]},
                    "image_config": {"architecture": "arm64", "created": "2026-10-05T00:00:00Z"}}))
            elif "/usr/bin/dpkg-query" in args:
                return SimpleNamespace(returncode=0, stdout="bash=1\\n")
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
