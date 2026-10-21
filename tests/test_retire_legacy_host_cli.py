from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import retire_legacy_host_cli as legacy


class LegacyHostCliRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-legacy-host-cli-")
        self.base = Path(self.temp.name)
        self.prefix = self.base / "prefix"
        self.command = self.prefix / "bin/ternux"
        self.library = self.prefix / "lib/ternux"
        self.command.parent.mkdir(parents=True)
        self.library.mkdir(parents=True)
        self.command.write_text("#!/usr/bin/env bash\n# ternux — Linux desktop CLI\n_TNX_LIB_DIR=\"\"\n", encoding="utf-8")
        self.command.chmod(0o755)
        (self.library / "core.sh").write_text("TERNUX_VERSION=1\n", encoding="utf-8")
        (self.library / "desktop.sh").write_text("tnx_cmd_start() { :; }\n", encoding="utf-8")
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_apply_and_rollback_preserve_original_inodes(self):
        command_inode = self.command.stat().st_ino
        library_inode = self.library.stat().st_ino
        core_inode = (self.library / "core.sh").stat().st_ino
        plan = legacy.preview(self.prefix, self.state)
        result = legacy.apply(self.prefix, self.state, plan["plan_id"])
        self.assertFalse(self.command.exists())
        self.assertFalse(self.library.exists())
        backup = Path(result["backup_path"])
        self.assertEqual((backup / "ternux").stat().st_ino, command_inode)
        self.assertEqual((backup / "library/ternux").stat().st_ino, library_inode)
        self.assertEqual((backup / "library/ternux/core.sh").stat().st_ino, core_inode)
        restored = legacy.rollback(self.prefix, self.state, result["backup_id"])
        self.assertTrue(restored["restored"])
        self.assertEqual(self.command.stat().st_ino, command_inode)
        self.assertEqual(self.library.stat().st_ino, library_inode)
        self.assertEqual((self.library / "core.sh").stat().st_ino, core_inode)

    def test_stale_plan_refuses_to_move_legacy_cli(self):
        plan = legacy.preview(self.prefix, self.state)
        self.command.write_text(self.command.read_text() + "# changed\n", encoding="utf-8")
        with self.assertRaisesRegex(legacy.RetirementError, "stale"):
            legacy.apply(self.prefix, self.state, plan["plan_id"])
        self.assertTrue(self.command.exists())
        self.assertTrue(self.library.exists())

    def test_unexpected_links_in_library_are_refused(self):
        (self.library / "linked.sh").symlink_to(self.library / "core.sh")
        with self.assertRaisesRegex(legacy.RetirementError, "link or unsupported"):
            legacy.preview(self.prefix, self.state)

    def test_rollback_never_overwrites_replacement_command(self):
        plan = legacy.preview(self.prefix, self.state)
        result = legacy.apply(self.prefix, self.state, plan["plan_id"])
        self.command.write_text("replacement\n", encoding="utf-8")
        with self.assertRaisesRegex(legacy.RetirementError, "refusing to overwrite"):
            legacy.rollback(self.prefix, self.state, result["backup_id"])
        self.assertEqual(self.command.read_text(), "replacement\n")
        self.assertTrue((Path(result["backup_path"]) / "ternux").exists())


if __name__ == "__main__":
    unittest.main()
