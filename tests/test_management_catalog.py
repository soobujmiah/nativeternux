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


    def test_typed_resource_catalog_has_unique_ids_and_truthful_ownership(self):
        catalog = management_catalog.build_catalog(set(management_service.OPERATIONS))
        categories = {item["id"] for item in catalog["categories"]}
        resources = catalog["resources"]
        ids = [item["id"] for item in resources]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item["category_id"] in categories for item in resources))
        self.assertEqual(catalog["schema_version"], 2)
        by_id = {item["id"]: item for item in resources}
        self.assertEqual(by_id["network.ssh.manual-8022"]["status"], "external")
        self.assertEqual(by_id["network.ssh.manual-8022"]["supported_operations"], ["ssh.inspect"])
        self.assertEqual(by_id["network.ssh.managed-8023"]["configuration"]["defaults"]["port"], 8023)
        audio = by_id["native.audio.pulseaudio"]
        self.assertEqual(audio["status"], "partial")
        self.assertEqual(audio["ownership"]["authority"], "ternuxx-native-pulse-lifecycle")
        self.assertEqual(audio["supported_operations"], ["doctor.report"])
        self.assertIn("audible output remain unqualified", audio["description"])
        self.assertEqual(by_id["server.generic-deployment"]["status"], "planned")
        accelerator = by_id["native.acceleration.qualification"]
        self.assertEqual(accelerator["status"], "partial")
        self.assertEqual(accelerator["supported_operations"], ["doctor.report"])
        self.assertTrue(accelerator["security"]["read_only"])
        self.assertIn("Native Termux and Debian PRoot remain separate", accelerator["description"])
        for resource in resources:
            self.assertTrue(set(resource["supported_operations"]).issubset(management_service.OPERATIONS))
            self.assertEqual(set(resource["operation_capabilities"]), set(resource["supported_operations"]))

    def test_proot_session_health_is_catalogued_as_read_only(self):
        catalog = management_catalog.build_catalog(set(management_service.OPERATIONS))
        resource = next(item for item in catalog["resources"] if item["id"] == "proot.debian.workloads")
        self.assertIn("proot.sessions.health", resource["supported_operations"])
        self.assertEqual(resource["operation_capabilities"]["proot.sessions.health"], "diagnostics.read")
        self.assertFalse(resource["security"]["read_only"])

    def test_catalog_category_query_and_status_filters(self):
        operations = set(management_service.OPERATIONS)
        service = management_catalog.build_catalog(operations, category="services")
        self.assertEqual({item["category_id"] for item in service["resources"]}, {"services"})
        filtered = management_catalog.build_catalog(operations, query="8022")
        self.assertEqual([item["id"] for item in filtered["resources"]], ["network.ssh.manual-8022"])
        planned = management_catalog.build_catalog(operations, status="planned")
        self.assertTrue(planned["resources"])
        self.assertTrue(all(item["status"] == "planned" for item in planned["resources"]))
        with self.assertRaises(ValueError):
            management_catalog.build_catalog(operations, category=[])
        with self.assertRaises(ValueError):
            management_catalog.build_catalog(operations, query="x" * 121)

    def test_catalog_api_accepts_filters_without_live_probes(self):
        env = {"TERMUX_VERSION":"test", "PREFIX":"/data/data/com.termux/files/usr", "HOME":"/tmp", "TERNUXX_STATE_DIR":"/tmp/state"}
        response = management_service.dispatch({"api_version":1,"request_id":"catalog-filter-1234","operation":"management.catalog","args":{"category":"networking"}}, env=env)
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["filters"]["category"], "networking")
        self.assertTrue(all(item["category_id"] == "networking" for item in response["data"]["resources"]))
        bad = management_service.dispatch({"api_version":1,"request_id":"catalog-filter-5678","operation":"management.catalog","args":{"category":[]}}, env=env)
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"]["code"], "invalid_arguments")


if __name__ == "__main__":
    unittest.main()
