# Managed SSH Wake Lock policy evidence — 2026-10-22

## Behavior

The shared native.sshd service now has a preview-confirmed persistent Wake Lock preference in CLI, TUI, authenticated Web and GTK. It controls whether the service acquires its owner-scoped persistent lease on its next managed Runit start. It does not restart SSH or alter the running process lease. An absent preference means enabled, preserving prior behavior. Android platform-global Wake Lock state remains unknown.

The service wrapper accepts policy_disabled while still starting SSH, and releases a lease only when it acquired one. Unknown outcomes fail closed. Policy storage is private, schema-checked, symlink-resistant and atomically replaced; apply requires the exact preview plan identity. No preference was applied.

## Verification

- Full Native suite: bash scripts/repo_test.sh — exit 0; 824 tests passed in 93.800 seconds.
- Focused feature suite — 105 tests passed.
- Changed Python compile checks, bash -n on lib/reboot.sh and the service wrapper, and git diff --check — passed.
- python3 -m tools.repo_knowledge verify — 0 findings.
- Native read-only status: enabled=true, configured=false, default=true, current lease unchanged, platform lock state unknown.
- Native wrapper source and installed run definition SHA-256 both 50efdce270fbc46566df0c0e83bd8cd520567aa9cdd8c18f1622dc0d07fcf59c. sv status reports existing PID 21035; no restart occurred.
- GTK source hash 85887331ddbb965f3450c0d8e5cc26e71bea924733bffc8ab1b43d739b82132a matches install identity. Installed binary hash 8ff68ed3abbe30508ceba3e45e08236931f6d7ff498b7378381a284698c91eb5, launcher, desktop entry, and checkout bridge hash match identity records.
- Read-only screenshot confirms GTK Management Center on :1, showing Graphics. UI was not navigated; the new Wake Lock dialog/flow remains visually unverified.

## Limits

No preference mutation, service restart, SSH credential/config change, Android-global lock operation, or rootfs change occurred. Evidence does not prove a future start with disabled policy or Android lock behavior. GTK interaction visual review and cold-boot observation remain open. P4 remains in progress.
