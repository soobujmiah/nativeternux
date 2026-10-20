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


if __name__ == "__main__":
    unittest.main()
