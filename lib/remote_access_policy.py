#!/usr/bin/env python3
"""Offline validator and non-applying preview for optional remote-access policy."""
from __future__ import annotations

import re
from typing import Any


class RemoteAccessPolicyError(ValueError):
    """The desired remote-access policy is malformed or unsafe."""


_OPAQUE_REF = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
_CREDENTIAL_REF = re.compile(r"^credential_ref_[A-Za-z0-9_-]{8,128}$")
_TOP_LEVEL = {
    "schema_version", "mode", "public_ingress", "transport", "allowed_client_refs",
    "allowed_targets", "capability_refs", "session_ttl_seconds",
}
_TARGETS = {"native_termux"}
_TRANSPORTS = {"vpn_overlay", "authenticated_outbound_tunnel"}


def _refs(value: object, name: str, *, required_nonempty: bool, maximum: int = 64) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum or (required_nonempty and not value):
        raise RemoteAccessPolicyError(f"{name} must be a bounded non-empty list")
    if any(not isinstance(item, str) or not _OPAQUE_REF.fullmatch(item) for item in value):
        raise RemoteAccessPolicyError(f"{name} must contain opaque references, not credentials")
    if len(set(value)) != len(value):
        raise RemoteAccessPolicyError(f"{name} must not contain duplicates")
    return value


def validate_policy(value: object) -> dict[str, Any]:
    """Validate the secret-free v1 desired policy without resolving references."""
    if not isinstance(value, dict) or set(value) - _TOP_LEVEL:
        raise RemoteAccessPolicyError("remote-access policy fields are invalid")
    required = {"schema_version", "mode", "public_ingress"}
    if required - set(value):
        raise RemoteAccessPolicyError("remote-access policy is missing required fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 2:
        raise RemoteAccessPolicyError("remote-access schema version is unsupported")
    mode = value["mode"]
    if not isinstance(mode, str) or mode not in {"disabled", "private_transport"}:
        raise RemoteAccessPolicyError("remote-access mode is unsupported")
    if value["public_ingress"] is not False:
        raise RemoteAccessPolicyError("public ingress is prohibited")

    if "transport" in value:
        transport = value["transport"]
        if not isinstance(transport, dict) or set(transport) != {"kind", "provider_id", "credential_ref"}:
            raise RemoteAccessPolicyError("transport fields are invalid")
        if not isinstance(transport["kind"], str) or transport["kind"] not in _TRANSPORTS:
            raise RemoteAccessPolicyError("transport kind is unsupported")
        if not isinstance(transport["provider_id"], str) or not _PROVIDER_ID.fullmatch(transport["provider_id"]):
            raise RemoteAccessPolicyError("transport provider ID is invalid")
        if not isinstance(transport["credential_ref"], str) or not _CREDENTIAL_REF.fullmatch(transport["credential_ref"]):
            raise RemoteAccessPolicyError("credential_ref must use the credential_ref_ ID format")

    clients = None
    if "allowed_client_refs" in value:
        clients = _refs(value["allowed_client_refs"], "allowed_client_refs", required_nonempty=mode == "private_transport", maximum=32)
    targets = None
    if "allowed_targets" in value:
        raw_targets = value["allowed_targets"]
        if not isinstance(raw_targets, list) or len(raw_targets) > 2 or (mode == "private_transport" and not raw_targets):
            raise RemoteAccessPolicyError("allowed_targets must be a bounded non-empty list")
        if any(not isinstance(item, str) or item not in _TARGETS for item in raw_targets):
            raise RemoteAccessPolicyError("allowed_targets contains an unsupported provider")
        if len(set(raw_targets)) != len(raw_targets):
            raise RemoteAccessPolicyError("allowed_targets must not contain duplicates")
        targets = raw_targets
    capabilities = None
    if "capability_refs" in value:
        capabilities = _refs(value["capability_refs"], "capability_refs", required_nonempty=mode == "private_transport")

    if mode == "private_transport":
        required_private = {"transport", "allowed_client_refs", "allowed_targets", "capability_refs", "session_ttl_seconds"}
        if required_private - set(value):
            raise RemoteAccessPolicyError("private transport policy is incomplete")
    ttl = value.get("session_ttl_seconds")
    if ttl is not None and (type(ttl) is not int or not 60 <= ttl <= 3600):
        raise RemoteAccessPolicyError("session TTL must be between 60 and 3600 seconds")

    # Return a detached JSON-shaped copy so callers cannot mutate the caller's input.
    return {
        "schema_version": 2,
        "mode": mode,
        "public_ingress": False,
        **({"transport": dict(value["transport"])} if "transport" in value else {}),
        **({"allowed_client_refs": list(clients)} if clients is not None else {}),
        **({"allowed_targets": list(targets)} if targets is not None else {}),
        **({"capability_refs": list(capabilities)} if capabilities is not None else {}),
        **({"session_ttl_seconds": ttl} if ttl is not None else {}),
    }


def preview(value: object | None = None) -> dict[str, object]:
    """Return policy readiness only; never enables or probes a transport."""
    if value is None:
        value = {"schema_version": 2, "mode": "disabled", "public_ingress": False}
    policy = validate_policy(value)
    private = policy["mode"] == "private_transport"
    blockers = (["private transport adapter is not implemented", "transport route and client identity are not verified"]
                if private else [])
    transport = policy.get("transport", {})
    return {
        "schema_version": 1,
        "component": "remote_access_policy_preview",
        "mode": policy["mode"],
        "public_ingress": False,
        "remote_access_active": False,
        "transport_state": "not_probed",
        "readiness": "unavailable" if private else "disabled",
        "transport_kind": transport.get("kind") if isinstance(transport, dict) else None,
        "allowed_client_count": len(policy.get("allowed_client_refs", [])),
        "allowed_target_count": len(policy.get("allowed_targets", [])),
        "capability_count": len(policy.get("capability_refs", [])),
        "blockers": blockers,
        "safety": {"network_accessed": False, "credentials_resolved": False, "files_changed": False,
                   "services_changed": False, "public_ingress_enabled": False},
    }
