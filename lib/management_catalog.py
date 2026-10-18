"""Canonical inventory of shared management domains and provider maturity."""
from __future__ import annotations

PROVIDERS = [
    {"id": "native-termux", "kind": "local-runtime", "status": "active", "secret_policy": "local state only"},
    {"id": "proot-debian", "kind": "guest-runtime", "status": "installed-adapt-first", "secret_policy": "guest credentials remain guest-owned"},
    {"id": "runit", "kind": "service-manager", "status": "active-for-managed-sshd", "secret_policy": "no credentials stored"},
    {"id": "cloud-api", "kind": "remote-backend", "status": "planned-disabled", "secret_policy": "future secret references only; no credentials or network calls"},
]

DOMAINS = [
    {"id":"sshd-servers", "status":"implemented", "providers":["native-termux","runit"], "operations":["ssh.inspect","native.ssh.status","ssh.service.start","ssh.service.stop","ssh.service.deploy","ssh.service.deploy.rollback.preview","ssh.service.deploy.rollback.apply","remote.access.preview"]},
    {"id":"proot-runtime", "status":"partial-installed-debian-first", "providers":["native-termux","proot-debian"], "operations":["proot.status","proot.guest.verify","proot.app.launch","proot.shortcuts.list","proot.shortcuts.preview","proot.shortcuts.apply"], "planned":["guest.adapt","guest.install","guest.uninstall","guest.distro.select","desktop.install","desktop.select"], "targets":["installed Debian adaptation first","selectable Debian/Ubuntu/other distro adapters","selectable desktop environments including XFCE4 and alternatives"]},
    {"id":"doctor-diagnostics", "status":"implemented", "providers":["native-termux","proot-debian"], "operations":["doctor.report","management.catalog"]},
    {"id":"autoboot-background", "status":"implemented", "providers":["native-termux","runit"], "operations":["boot.status","boot.profile.status","boot.profile.preview","boot.enable","boot.disable","wakelock.status","wakelock.acquire","wakelock.release"]},
    {"id":"backup-recovery-continuity", "status":"implemented", "providers":["native-termux"], "operations":["backup.create","backup.list","backup.inspect","restore.preview","restore.apply","recovery.status","recovery.resolve","recovery.inspect","recovery.rollback.preview","recovery.rollback.apply","continuity.status","continuity.prepare","continuity.verify","continuity.prepare-reboot-test","continuity.verify-reboot-test","continuity.resume-info"]},
    {"id":"addons-plugins-tools", "status":"catalog-and-cli-tools-partial", "providers":["native-termux","proot-debian"], "operations":[], "planned":["addon.list","addon.preview","addon.apply","plugin.list","plugin.preview","plugin.apply","tool.catalog"]},
    {"id":"api-backends", "status":"planned-disabled", "providers":["cloud-api"], "operations":[], "planned":["backend.list","backend.health","backend.select","backend.credentials.reference"]},
]


def build_catalog(implemented_operations: set[str]) -> dict[str, object]:
    domains=[]
    for source in DOMAINS:
        item=dict(source)
        item["available_operations"]=[name for name in source.get("operations",[]) if name in implemented_operations]
        item["unavailable_operations"]=[name for name in source.get("operations",[]) if name not in implemented_operations]
        domains.append(item)
    return {"schema_version":1,"read_only":True,"providers":PROVIDERS,"domains":domains,
            "policy":{"mutations_require_preview_and_explicit_confirmation":True,
                      "external_cloud_calls_enabled":False,"credentials_in_catalog":False}}
