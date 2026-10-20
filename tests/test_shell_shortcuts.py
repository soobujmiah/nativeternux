"""Retirement fixtures for the obsolete bare-gui shell function."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import termux_shell_shortcuts as shortcuts  # noqa: E402


class ShellShortcutRetirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-shell-shortcut-")
        self.home = Path(self.temp.name)
        self.rc = self.home / ".bashrc"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_preview_does_not_add_shortcut_to_new_or_unmanaged_rc(self) -> None:
        self.rc.write_text("export KEEP_ME=yes\n")
        plan = shortcuts.preview(home=self.home)
        self.assertFalse(plan["changed"])
        self.assertEqual(self.rc.read_text(), "export KEEP_ME=yes\n")

    def test_apply_removes_only_managed_gui_block(self) -> None:
        before = ("export KEEP_ME=yes\n\n" + shortcuts.BEGIN + "\n"
                  + 'gui() { command tx start "$@"; }\n' + shortcuts.END
                  + "\n\nexport ALSO_KEEP=yes\n")
        self.rc.write_text(before)
        plan = shortcuts.preview(home=self.home)
        self.assertTrue(plan["changed"])
        with self.assertRaises(shortcuts.ShortcutError):
            shortcuts.apply(home=self.home, confirmed=True, plan_id="wrong")
        result = shortcuts.apply(home=self.home, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(result["status"], "removed")
        self.assertEqual(self.rc.read_text(), "export KEEP_ME=yes\n\n\nexport ALSO_KEEP=yes\n")
        self.assertNotIn("gui()", self.rc.read_text())

    def test_unmanaged_gui_alias_is_preserved(self) -> None:
        self.rc.write_text('gui() { echo owner-function; }\n')
        plan = shortcuts.preview(home=self.home)
        self.assertFalse(plan["changed"])
        self.assertEqual(self.rc.read_text(), 'gui() { echo owner-function; }\n')


if __name__ == "__main__":
    unittest.main()
