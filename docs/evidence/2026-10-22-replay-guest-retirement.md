# Replay guest retirement and restore — 2026-10-22

Phase: `P4`
Gate: `PARTIAL`

## Evidence

The Native shared management service now exposes exact-preview retirement and rollback operations to the CLI, authenticated Web client, TUI, and GTK client. The CLI routes through that service. The same operations are recorded in the typed capability catalog. All existing ownership, receipt, lock, process, inode, and no-delete safeguards described here remain in force.

Live Native replay on `ternuxx-replay-p4` passed:

- Retire preview: `e00190569b8a31e8436e72efb260daf83142d5e999ab1840e3a1edaa7a84f26d`
- Retirement/restore backup ID: `3dfdd42c1c7a4df5b57375935c45cdb7`
- Restore preview: `ef07ae61be2b0e24366464419ad7c3c95cb811d1e02c22fd3f2b89a74fd49c19`
- Result: `retired` then `restored`; container inode `101280` and rootfs inode `5078478` were preserved.
- `files_deleted: false`; the replay alias is installed again.
- Default Debian rootfs device/inode and `etc/profile.d/termux-profile.sh` SHA-256 matched before and after. The pre-existing PRoot PID with unverified ownership was not targeted.
- Native terminal broker remained `not_connected` after cleanup.

Reproduction:

```sh
./tx proot setup retire-preview --alias ternuxx-replay-p4
./tx proot setup retire --alias ternuxx-replay-p4 --yes --plan-id PLAN_ID
./tx proot setup restore-preview --alias ternuxx-replay-p4 --backup-id BACKUP_ID
./tx proot setup restore --alias ternuxx-replay-p4 --backup-id BACKUP_ID --yes --plan-id PLAN_ID
```

The current full Native suite passed 842/842 in 107.102 seconds. Six focused retirement tests cover exact inode/data preservation, default-alias/path-traversal rejection, live-session/process refusal, stale plans, confirmation, and recovery after interruption between rename and journal update. `bash -n lib/proot.sh`, Python compilation, and `git diff --check` passed.

## Shared client integration and installed GTK identity

The shared service validates exact arguments, uses the proot.guest.manage capability, and classifies preview/apply operations as CSRF-protected mutations. The catalog gives replay guests a separate resource from the existing Debian guest. Web exposes action-specific alias/backup inputs, preview and confirmation. TUI offers the same two operations through the replay-guest resource and existing PRoot workflow. GTK has a dedicated dialog, calls the typed Native bridge, and applies only the exact confirmed plan.

The Native GTK management center was rebuilt and installed. source_c, source_bridge, installed binary, launcher and desktop-entry hashes in the private identity record matched their current checkout/artifact hashes. The application menu desktop entry exists. The exact installed Native tx shim returned a fresh preview for ternuxx-replay-p4; it confirmed container inode 101280 and rootfs inode 5078478. That latest preview did not apply retirement.

## Remaining qualification

The live retire/restore apply cycle was previously exercised through the CLI and preserved the exact guest inode/data and default Debian. This continuation verified a fresh shared-service CLI preview, Web runtime policy loading, catalog availability, and source implementation for all four clients. It did not exercise an authenticated Web request or interact with the new GTK dialog; visual/runtime interaction for those controls remains unverified. The private journal and preview metadata stay under $HOME/.local/share/ternuxx/proot-setup/retired/; the full guest directory remains at its original PRoot-Distro path.
