"""Offline remote-access policy contract; it never contacts a transport."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import remote_access_policy


class RemoteAccessPolicyTests(unittest.TestCase):
    def private_policy(self):
        return {
            "schema_version": 2,
            "mode": "private_transport",
            "public_ingress": False,
            "transport": {"kind": "vpn_overlay", "provider_id": "owner_selected", "credential_ref": "credential_ref_00000001"},
            "allowed_client_refs": ["client_ref_001"],
            "allowed_targets": ["native_termux"],
            "capability_refs": ["capability_001"],
            "session_ttl_seconds": 900,
        }

    def test_default_preview_is_disabled_and_has_no_network_or_file_effects(self):
        result = remote_access_policy.preview()
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["readiness"], "disabled")
        self.assertFalse(result["remote_access_active"])
        self.assertFalse(result["public_ingress"])
        self.assertEqual(result["transport_state"], "not_probed")
        self.assertEqual(result["safety"], {"network_accessed": False, "credentials_resolved": False,
                         "files_changed": False, "services_changed": False, "public_ingress_enabled": False})

    def test_preview_outputs_match_declared_response_schema_shape_and_constants(self):
        import json
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "remote-access-policy-preview.schema.json").read_text())
        properties = schema["properties"]
        for result in (remote_access_policy.preview(), remote_access_policy.preview(self.private_policy())):
            with self.subTest(mode=result["mode"]):
                self.assertEqual(set(result), set(schema["required"]))
                for key, definition in properties.items():
                    if "const" in definition:
                        self.assertEqual(result[key], definition["const"])
                    if "enum" in definition:
                        self.assertIn(result[key], definition["enum"])
                self.assertEqual(set(result["safety"]), set(schema["properties"]["safety"]["required"]))
                self.assertTrue(all(value is False for value in result["safety"].values()))
                self.assertEqual(result["readiness"], "disabled" if result["mode"] == "disabled" else "unavailable")

    def test_remote_access_schema_matches_credential_reference_contract(self):
        import json
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "remote-access-config.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["public_ingress"]["const"], False)
        self.assertEqual(schema["$defs"]["credentialRef"]["pattern"], "^credential_ref_[A-Za-z0-9_-]{8,128}$")
        self.assertEqual(schema["$defs"]["transport"]["properties"]["credential_ref"]["$ref"], "#/$defs/credentialRef")

    def test_private_transport_is_desired_only_and_never_claimed_active(self):
        result = remote_access_policy.preview(self.private_policy())
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["readiness"], "unavailable")
        self.assertFalse(result["remote_access_active"])
        self.assertEqual(result["allowed_client_count"], 1)
        self.assertEqual(result["allowed_target_count"], 1)
        self.assertIn("private transport adapter is not implemented", result["blockers"])
        self.assertEqual(result["transport_kind"], "vpn_overlay")
        rendered = str(result)
        self.assertNotIn("credential_ref_00000001", rendered)
        self.assertNotIn("client_ref_001", rendered)

    def test_schema_version_one_and_boolean_version_are_rejected(self):
        for version in (1, True):
            policy = {"schema_version": version, "mode": "disabled", "public_ingress": False}
            with self.subTest(version=version), self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
                remote_access_policy.validate_policy(policy)

    def test_public_ingress_and_non_reference_credential_are_rejected(self):
        policy = self.private_policy()
        policy["public_ingress"] = True
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)
        policy = self.private_policy()
        policy["transport"]["credential_ref"] = "raw-secret-token"
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)

    def test_private_policy_requires_clients_targets_capabilities_and_transport(self):
        for field in ("transport", "allowed_client_refs", "allowed_targets", "capability_refs", "session_ttl_seconds"):
            policy = self.private_policy()
            del policy[field]
            with self.subTest(field=field), self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
                remote_access_policy.validate_policy(policy)

    def test_policy_rejects_unknown_fields_duplicates_and_unbounded_ttl(self):
        policy = self.private_policy()
        policy["arbitrary_shell"] = "id"
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)
        policy = self.private_policy()
        policy["allowed_client_refs"] *= 2
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)
        policy = self.private_policy()
        policy["allowed_client_refs"] = [f"client_{index:08d}" for index in range(33)]
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)
        policy = self.private_policy()
        policy["session_ttl_seconds"] = 3601
        with self.assertRaises(remote_access_policy.RemoteAccessPolicyError):
            remote_access_policy.validate_policy(policy)


if __name__ == "__main__":
    unittest.main()
