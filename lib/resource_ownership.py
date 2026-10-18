"""Small ownership model for shared resources such as Android Wake Lock.

This module models leases only. It does not acquire or release a platform
Wake Lock; the Termux adapter will be added only after the device mechanism
and ownership semantics are verified.
"""

from __future__ import annotations


class ResourceOwnership:
    def __init__(self) -> None:
        self._owners: dict[str, set[str]] = {}

    def acquire(self, resource: str, owner: str) -> bool:
        if not resource or not owner:
            raise ValueError("resource and owner are required")
        leases = self._owners.setdefault(resource, set())
        before = len(leases)
        leases.add(owner)
        return len(leases) != before

    def release(self, resource: str, owner: str) -> bool:
        leases = self._owners.get(resource)
        if not leases or owner not in leases:
            return False
        leases.remove(owner)
        if not leases:
            del self._owners[resource]
        return True

    def is_required(self, resource: str) -> bool:
        return bool(self._owners.get(resource))

    def owners(self, resource: str) -> tuple[str, ...]:
        return tuple(sorted(self._owners.get(resource, ())))
