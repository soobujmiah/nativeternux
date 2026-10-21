from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import retire_legacy_guest_cli as legacy


class LegacyGuestCliRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-legacy-cli-")
        self.base = Path(self.temp.name)
        self.rootfs = self.base / "rootfs"
        self.target = self.rootfs / legacy.TARGET_RELATIVE
        self.target.parent.mkdir(parents=True)
        self.target.write_text("#!/usr/bin/env bash\n# ternux guest companion\nTERNUX_GUEST_VERSION=1.4.0\n", encoding="utf-8")
        self.target.chmod(0o755)
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_apply_and_rollback_move_only_exact_target(self):
        original = self.target.stat()
        plan = legacy.preview(self.rootfs, self.state)
        self.assertTrue(plan["confirmation_required"])
        result = legacy.apply(self.rootfs, self.state, plan["plan_id"])
        self.assertFalse(self.target.exists())
        backup = Path(result["backup_path"])
        self.assertEqual(backup.stat().st_ino, original.st_ino)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o755)
        restored = legacy.rollback(self.rootfs, self.state, result["backup_id"])
        self.assertTrue(restored["restored"])
        self.assertEqual(self.target.stat().st_ino, original.st_ino)
        self.assertEqual(self.target.read_text(), "#!/usr/bin/env bash\n# ternux guest companion\nTERNUX_GUEST_VERSION=1.4.0\n")

    def test_apply_rejects_stale_content_without_moving_target(self):
        plan = legacy.preview(self.rootfs, self.state)
        self.target.write_text(self.target.read_text() + "# changed\n", encoding="utf-8")
        with self.assertRaisesRegex(legacy.RetirementError, "stale"):
            legacy.apply(self.rootfs, self.state, plan["plan_id"])
        self.assertTrue(self.target.exists())

    def test_unexpected_target_is_refused(self):
        self.target.write_text("#!/bin/sh\necho unrelated\n", encoding="utf-8")
        with self.assertRaisesRegex(legacy.RetirementError, "do not identify"):
            legacy.preview(self.rootfs, self.state)
        self.assertTrue(self.target.exists())

    def test_preview_rejects_symlinked_rootfs_parent_component(self):
        outside = self.base / "outside"
        outside.mkdir()
        shutil.rmtree(self.rootfs / "usr" / "local")
        (self.rootfs / "usr" / "local").symlink_to(outside, target_is_directory=True)
        external_target = outside / "bin" / "ternux"
        external_target.parent.mkdir()
        external_target.write_text("#!/bin/sh\n# ternux guest companion\nTERNUX_GUEST_VERSION=1\n")
        with self.assertRaisesRegex(legacy.RetirementError, "unsafe component"):
            legacy.preview(self.rootfs, self.state)
        self.assertTrue(external_target.exists())

    def test_rollback_refuses_to_overwrite_new_target(self):
        plan = legacy.preview(self.rootfs, self.state)
        result = legacy.apply(self.rootfs, self.state, plan["plan_id"])
        self.target.write_text("replacement", encoding="utf-8")
        with self.assertRaisesRegex(legacy.RetirementError, "already exists"):
            legacy.rollback(self.rootfs, self.state, result["backup_id"])
        self.assertEqual(self.target.read_text(), "replacement")


if __name__ == "__main__":
    unittest.main()
