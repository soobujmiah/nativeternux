# Native entrypoints and SSH/continuity contract audit — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Evidence

[Read-only entrypoint inventory](2026-10-22-native-entrypoint-inventory.json) verifies all three checked-in Runit definitions, all three checked-in Termux:Boot helpers, the installed tx shim and every Python module currently in the canonical installed recovery directory (three modules). Files are same-user regular files with safe permissions and exact source/installed hashes. Isolated Native Python imports resolve all three recovery modules from the installed path.

This is complete for that named entrypoint set, not for every package, profile, shortcut, runtime config, driver or supported fresh installation. GTK identities were separately verified in [monitor follow-up](2026-10-22-monitor-service-registration.md).

Native managed SSH was inspected through the real GTK bridge. The effective 8023 service policy reports loopback bind, valid config, verified definition/process, publickey authentication method and a protocol banner. Kernel listener ownership remains unknown because procfs and netlink are denied. No authenticated login or lifecycle/authentication mutation was performed in this audit.

## Documentation reconciliation

SSH and continuity architecture contained obsolete current-sounding claims: no GUI/Web, only one enabled service, stopped development SSH, old password flow, old CLI name and RB03 as the current checkpoint. The complete original documents are preserved as dated history with relocated links. Link normalization was round-tripped against each original before replacement; original content was not discarded.

Current documents distinguish actual shared status/lifecycle, desired credential/setup/recovery work, live observations, historical boot evidence and unknowns. The existing fixture link to the SSH-01–SSH-15 contract remains valid through its original anchor and a history link. No proposed API or command is presented as implemented.

The credential contract explicitly identifies the shared Termux principal: changing an account password or shared authorized_keys can affect both 8022 and 8023. Future controls must preview that impact and preserve working development access.

P1 research, P2 completion and P3 RB08 records were read. P2's original full pre-consent package preview remains unrecoverable; later package closure and intercepted apply checks do not recreate it. RB08 manual service/auth readiness does not overwrite its NOT_READY checkpoint, and the later canonical module copy has no new cold-boot evidence. The full requirement-by-requirement phase requalification is still open.

## Checks and preservation

This increment changes documents/evidence only. Native code remains the source state verified by the preceding 715/715 suite and two successful CI workflows. New runtime observations are read-only. Documentation link/inventory, history preservation, generated phase, diff and deterministic-state checks are run after edits.

No package, SSH key/config, service lifecycle, boot execution, desktop, rootfs or active Codex guest was changed. The complete [repository audit](../audit/REPOSITORY-AUDIT.md) remains active.
