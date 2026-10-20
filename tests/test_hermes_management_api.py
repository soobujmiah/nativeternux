from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import hermes_adapter
import management_authorization
import management_catalog
import management_service
import management_sessions


class HermesManagementApiTests(unittest.TestCase):
    def setUp(self):
        self.env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr",
                    "HOME": "/tmp/home", "TERNUXX_STATE_DIR": "/tmp/state"}

    def test_status_is_explicit_read_only_api_capability(self):
        operation = "agent.hermes.status"
        self.assertIn(operation, management_service.OPERATIONS)
        self.assertEqual(management_authorization.required_capability(operation), "diagnostics.read")
        self.assertIn(operation, management_sessions.READ_ONLY_OPERATIONS)
        self.assertNotIn(operation, management_sessions.MUTATING_OPERATIONS)

    def test_dispatch_uses_adapter_and_returns_typed_status(self):
        expected = {"provider_id": "hermes", "availability": "unknown",
                    "scheduler": {"state": "unknown", "profile": "unknown", "health": "unknown"}}
        with patch.object(hermes_adapter, "inspect", return_value=expected) as inspect:
            result = management_service.dispatch({"api_version": 1, "request_id": "hermes-status-0001",
                "operation": "agent.hermes.status", "args": {}}, env=self.env)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], expected)
        inspect.assert_called_once_with(prefix=self.env["PREFIX"], home=self.env["HOME"])

    def test_catalog_advertises_only_status_not_task_execution(self):
        catalog = management_catalog.build_catalog(set(management_service.OPERATIONS), category="ai-providers")
        resource = next(item for item in catalog["resources"] if item["id"] == "agent.hermes")
        self.assertEqual(resource["supported_operations"], ["agent.hermes.status"])
        self.assertIn("agent.hermes.execution.run", resource["planned_operations"])

    def test_invalid_arguments_are_rejected(self):
        result = management_service.dispatch({"api_version": 1, "request_id": "hermes-status-0002",
            "operation": "agent.hermes.status", "args": {"task": "run"}}, env=self.env)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_arguments")


if __name__ == "__main__":
    unittest.main()
