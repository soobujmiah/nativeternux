import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import management_authorization
import management_catalog
import management_service
import management_sessions


class ManagementCatalogTests(unittest.TestCase):
    def test_catalog_distinguishes_implemented_and_planned_providers(self):
        catalog = management_catalog.build_catalog(set(management_service.OPERATIONS))
        domains = {domain["id"]: domain for domain in catalog["domains"]}
        self.assertIn("doctor.report", domains["doctor-diagnostics"]["available_operations"])
        proot = domains["proot-runtime"]
        self.assertEqual(proot["status"], "partial-installed-debian-first")
        self.assertIn("guest.install", proot["planned"])
        self.assertIn("desktop.select", proot["planned"])
        cloud = next(provider for provider in catalog["providers"] if provider["id"] == "cloud-api")
        self.assertEqual(cloud["status"], "planned-disabled")
        self.assertFalse(catalog["policy"]["external_cloud_calls_enabled"])
        self.assertFalse(catalog["policy"]["credentials_in_catalog"])

    def test_catalog_and_doctor_are_read_only_shared_operations(self):
        for operation in ("management.catalog", "doctor.report"):
            self.assertEqual(management_authorization.required_capability(operation), "diagnostics.read")
            self.assertIn(operation, management_sessions.READ_ONLY_OPERATIONS)
            self.assertNotIn(operation, management_sessions.MUTATING_OPERATIONS)
            self.assertIn(operation, management_service.OPERATIONS)


if __name__ == "__main__":
    unittest.main()
