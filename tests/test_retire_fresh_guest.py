from __future__ import annotations

from contextlib import nullcontext
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tools"))
import proot_fresh_setup
import retire_fresh_guest


class RetireFreshGuestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-retire-guest-")
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.prefix = self.base / "prefix"
        self.containers = self.prefix / "var/lib/proot-distro/containers"
        self.containers.mkdir(parents=True)
        self.state = self.home / ".local/share/ternuxx"
        self.state.mkdir(parents=True, mode=0o700)
        self.alias = "ternuxx-replay-fixture"
        self.container = self.containers / self.alias
        self.rootfs = self.container / "rootfs"
        (self.rootfs / "etc").mkdir(parents=True)
        self.payload = self.rootfs / "etc/owner-data"
        self.payload.write_text("must survive retirement and rollback")
        (self.container / "manifest.json").write_text('{"image_ref":"debian:trixie"}\n')
        setup_state = self.state / "proot-setup"
        (setup_state / "previews").mkdir(parents=True, mode=0o700)
        receipt = {
            "schema_version": 1, "alias": self.alias, "guest_user": "sbj",
            "release": "Debian Trixie", "origin": "fresh-preview-confirmed-install",
            "package_versions_recorded": True,
            "requested_packages_verified_installed": True,
            "rootfs_identity": proot_fresh_setup._root_identity(self.container, self.rootfs),
        }
        proot_fresh_setup._private_write(
            setup_state / f"fresh-provider-{self.alias}.json", receipt)
        self.common = {"prefix": str(self.prefix), "home": str(self.home),
                       "state_dir": str(self.state), "alias": self.alias}

    def tearDown(self):
        self.temp.cleanup()

    def _no_activity(self):
        return patch.object(retire_fresh_guest, "_assert_idle", return_value=None)

    def _no_proot_lock(self):
        return patch.object(retire_fresh_guest, "_container_lock",
                            return_value=nullcontext())

    def test_preview_apply_and_restore_keep_exact_directory_and_guest_files(self):
        original_container = self.container.stat()
        original_rootfs = self.rootfs.stat()
        with self._no_activity(), self._no_proot_lock():
            preview = retire_fresh_guest.retire_preview(**self.common)
            retired = retire_fresh_guest.retire_apply(
                **self.common, plan_id=preview["plan_id"], confirmed=True)
        backup = Path(retired["backup_path"])
        self.assertFalse(self.container.exists())
        self.assertEqual((backup.stat().st_dev, backup.stat().st_ino),
                         (original_container.st_dev, original_container.st_ino))
        self.assertTrue((backup / "rootfs/etc/owner-data").is_file())
        self.assertFalse(retired["files_deleted"])
        with self._no_activity(), self._no_proot_lock():
            restore = retire_fresh_guest.restore_preview(
                **self.common, backup_id=retired["backup_id"])
            result = retire_fresh_guest.restore_apply(
                **self.common, backup_id=retired["backup_id"],
                plan_id=restore["plan_id"], confirmed=True)
        self.assertEqual(result["status"], "restored")
        self.assertEqual((self.container.stat().st_dev, self.container.stat().st_ino),
                         (original_container.st_dev, original_container.st_ino))
        self.assertEqual((self.rootfs.stat().st_dev, self.rootfs.stat().st_ino),
                         (original_rootfs.st_dev, original_rootfs.st_ino))
        self.assertEqual(self.payload.read_text(), "must survive retirement and rollback")

    def test_restore_recovers_after_interruption_between_rename_and_journal_write(self):
        with self._no_activity(), self._no_proot_lock():
            retire = retire_fresh_guest.retire_preview(**self.common)
            retired = retire_fresh_guest.retire_apply(
                **self.common, plan_id=retire["plan_id"], confirmed=True)
            restore = retire_fresh_guest.restore_preview(
                **self.common, backup_id=retired["backup_id"])
            original_rename = os.rename

            def rename_then_interrupt(source, destination, *args, **kwargs):
                original_rename(source, destination, *args, **kwargs)
                raise RuntimeError("simulated interruption after atomic rename")

            with patch.object(retire_fresh_guest.os, "rename", side_effect=rename_then_interrupt):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    retire_fresh_guest.restore_apply(
                        **self.common, backup_id=retired["backup_id"],
                        plan_id=restore["plan_id"], confirmed=True)
            result = retire_fresh_guest.restore_apply(
                **self.common, backup_id=retired["backup_id"],
                plan_id=restore["plan_id"], confirmed=True)
        self.assertEqual(result["status"], "restored")
        self.assertTrue(result["reconciled_interrupted_apply"])
        self.assertEqual(self.payload.read_text(), "must survive retirement and rollback")

    def test_default_and_path_traversal_aliases_are_refused(self):
        for alias in ("debian", "ternuxx-replay-../../debian"):
            with self.subTest(alias=alias), self.assertRaises(retire_fresh_guest.RetirementError):
                retire_fresh_guest.retire_preview(**{**self.common, "alias": alias})

    def test_running_managed_session_refuses_retirement(self):
        with patch.object(retire_fresh_guest.proot_sessions, "list_sessions",
                          return_value=[{"rootfs": str(self.rootfs), "state": "running"}]):
            with self.assertRaisesRegex(retire_fresh_guest.RetirementError, "still owns"):
                retire_fresh_guest._assert_idle(self.state / "proot-setup", self.rootfs)

    def test_live_matching_proot_process_refuses_retirement(self):
        cmdline = self.base / "proc/123/cmdline"
        cmdline.parent.mkdir(parents=True)
        cmdline.write_bytes(b"/usr/bin/proot\0-r\0" + os.fsencode(self.rootfs) + b"\0/bin/bash\0")
        with patch.object(retire_fresh_guest.proot_sessions, "list_sessions", return_value=[]):
            with self.assertRaisesRegex(retire_fresh_guest.RetirementError, "still uses"):
                retire_fresh_guest._assert_idle(self.state / "proot-setup", self.rootfs,
                                                self.base / "proc")

    def test_stale_plan_and_unconfirmed_apply_leave_guest_present(self):
        with self._no_activity(), self._no_proot_lock():
            preview = retire_fresh_guest.retire_preview(**self.common)
            with self.assertRaisesRegex(retire_fresh_guest.RetirementError, "confirmation"):
                retire_fresh_guest.retire_apply(
                    **self.common, plan_id=preview["plan_id"], confirmed=False)
            moved = self.containers / (self.alias + "-changed")
            self.container.rename(moved)
            self.container.mkdir()
            (self.container / "rootfs").mkdir()
            with self.assertRaisesRegex(retire_fresh_guest.RetirementError, "identity"):
                retire_fresh_guest.retire_apply(
                    **self.common, plan_id=preview["plan_id"], confirmed=True)
        self.assertTrue((moved / "rootfs/etc/owner-data").is_file())


if __name__ == "__main__":
    unittest.main()
