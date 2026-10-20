"""Phase evidence workflow validation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import phase_docs  # noqa: E402


class PhaseDocsTests(unittest.TestCase):
    def test_incremental_evidence_can_record_a_blocked_gate(self):
        path = "docs/evidence/2026-10-19-native-ui-management-audit.md"
        recorded, resolved = phase_docs.evidence_path(path, "P3", completion=False)
        self.assertEqual(recorded, path)
        self.assertTrue(resolved.is_file())
        with self.assertRaises(ValueError):
            phase_docs.evidence_path(path, "P3", completion=True)

    def test_optional_phase_skip_advances_to_next_planned_phase(self):
        state = {
            "active_phase": "P9",
            "phases": [
                {"id": "P8", "status": "completed"},
                {"id": "P9", "status": "in_progress", "optional": True},
                {"id": "P10", "status": "planned"},
            ],
        }
        phase_docs.skip_optional_phase(
            state, "P9", "No owner-approved workload gap remains.",
            ["docs/evidence/2026-10-20-phase-roadmap-audit.md"], skipped_on="2026-10-20",
        )
        self.assertEqual(state["phases"][1]["status"], "skipped")
        self.assertEqual(state["phases"][1]["skipped_on"], "2026-10-20")
        self.assertEqual(state["phases"][2]["status"], "in_progress")
        self.assertEqual(state["active_phase"], "P10")

    def test_only_active_optional_phase_can_be_skipped(self):
        state = {"active_phase": "P8", "phases": [
            {"id": "P8", "status": "in_progress"},
            {"id": "P9", "status": "planned", "optional": True},
        ]}
        with self.assertRaisesRegex(ValueError, "active phase explicitly marked optional"):
            phase_docs.skip_optional_phase(state, "P8", "skip", [])

    def test_skip_evidence_requires_explicit_skip_gate(self):
        invalid = "Phase: \x60P9\x60\n## Acceptance criteria\n## Evidence\n"
        valid = "Phase: \x60P9\x60\nGate: SKIP\n## Acceptance criteria\n## Evidence\n"
        with self.assertRaisesRegex(ValueError, "Gate: SKIP"):
            phase_docs.validate_evidence_content(invalid, "P9", completion=False, skip=True)
        phase_docs.validate_evidence_content(valid, "P9", completion=False, skip=True)

    def test_phase_order_requires_all_prior_gates_to_resolve(self):
        phases = [
            {"id": "P3", "status": "in_progress"},
            {"id": "P4", "status": "planned"},
        ]
        with self.assertRaisesRegex(ValueError, "earlier phase"):
            phase_docs.validate_phase_order(phases, "P4")
        phase_docs.validate_phase_order([
            {"id": "P3", "status": "completed"},
            {"id": "P4", "status": "in_progress"},
            {"id": "P5", "status": "planned"},
        ], "P4")

    def test_skipped_phase_must_be_marked_optional(self):
        phases = [
            {"id": "P3", "status": "skipped"},
            {"id": "P4", "status": "in_progress"},
        ]
        with self.assertRaisesRegex(ValueError, "Only explicitly optional"):
            phase_docs.validate_phase_order(phases, "P4")
        phases[0]["optional"] = True
        phase_docs.validate_phase_order(phases, "P4")


if __name__ == "__main__":
    unittest.main()
