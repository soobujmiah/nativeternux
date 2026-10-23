from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_setup_present


class ProotSetupPresentationTests(unittest.TestCase):
    def test_preview_summary_distinguishes_file_presence_from_acceleration(self) -> None:
        result = {
            "status": "preview", "plan_id": "a" * 64,
            "operation": {
                "guest_release": {"VERSION_ID": "13", "VERSION_CODENAME": "trixie"},
                "guest_user": "sbj", "rootfs": "/guest/debian/rootfs",
                "observed_graphics_files": {
                    "turnip_driver": {"status": "present"},
                    "turnip_icd": {"status": "missing"},
                },
                "guest_mutations": [], "package_changes": [], "service_changes": [],
            },
        }
        summary = proot_setup_present.summarize(result)
        self.assertIn("Turnip files: driver present; ICD missing (file presence only)", summary)
        self.assertTrue(any("unchanged" in line for line in summary))
        self.assertFalse(any("acceleration verified" in line for line in summary))

    def test_invalid_user_plan_and_terminal_controls_are_rejected(self) -> None:
        base = {"status": "preview", "plan_id": "a" * 64,
                "operation": {"guest_release": {}, "guest_user": "sbj", "rootfs": "/guest"}}
        for mutate in (
            lambda obj: obj.update(plan_id="bad"),
            lambda obj: obj["operation"].update(guest_user="\x1b[31mroot"),
            lambda obj: obj["operation"].update(rootfs="/guest\nforged"),
        ):
            import copy
            invalid = copy.deepcopy(base)
            mutate(invalid)
            with self.assertRaises(ValueError):
                proot_setup_present.summarize(invalid)


if __name__ == "__main__":
    unittest.main()
