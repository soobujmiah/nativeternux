# P4 managed legacy ICD migration

Date: 2026-10-24
Phase: `P4`
Native checkout: $HOME/ternuxx
Base revision after syncing origin/main: 3258d25ecc96a3c32c7b8dc13835633c56e32a49
Status: implementation and fixture verification complete; disposable guest integration and live apply remain open.

## Change

The existing Debian Vulkan ICD filename migration is now exposed as typed shared management operations for preview, apply, rollback preview, and rollback apply. The preview binds the selected alias, rootfs device/inode, profile manifest hash, exact source and target paths, source inode/mode/size, and SHA-256. Apply requires the saved exact plan, checks that the guest is idle, takes the PRoot container lock, writes a private exact-byte backup and prepared receipt, then uses no-replace renameat2. It verifies that the moved file kept the same bytes and inode. Rollback requires the exact receipt, rootfs identity, unchanged file, matching backup, and an empty legacy source path.

The operations are registered with the shared authorization and session contracts and the authenticated Web mutation set. Source controls were added to CLI tx proot setup, TUI, Web, and the GTK management center/bridge. No package, account, service, or renderer changes are part of this operation.

## Account and installer scope

Fresh Debian setup already binds the user supplied with --user into its exact preview. Apply asks twice for a hidden sudo password, sends it to the guest through stdin, and does not place it in the plan. Native Termux uses its Android app UID and does not create a Ternuxx Linux user/password. The fresh setup profile and this credential flow still cover Debian only; other proot-distro distributions and their package-manager/account adapters remain unimplemented.

## Evidence

- bash scripts/repo_test.sh: 929 tests passed, 1 skipped; 137.746 seconds. This ran before the final CLI action wrapper and source-contract assertions were added.
- After the final CLI wrapper and source-contract assertions: 239 focused tests passed, 1 skipped, including management service, Web, TUI, GTK contract, desktop bridge, Debian setup, and ICD migration fixtures.
- GTK C source passed clang -Wall -Wextra -fsyntax-only with GTK4/VTE4 headers.
- bash -n lib/proot.sh lib/help.sh and git diff --check passed.
- python3 -m tools.repo_knowledge verify: 0 findings.
- ./tx proot setup icd-migrate-preview --alias debian returned plan d06b8b6b1106c545f4807ee3faab078212ca4a98c679da1617063878d5324d23. It observed source hash 6e03d879305dcae3371a212bc7e9dcb23a5e42e9bf741966fe455972baa0b145, size 205 bytes, and an absent canonical target. The preview wrote Native private plan state only; no guest file was changed.
- ./tx proot status observed host PRoot PIDs 590 and 32668 with ownership unverified. No guest apply was attempted.
- Before updating GTK, the installed binary, launcher, identity, and desktop entry matched their recorded SHA-256 values; an exact private rollback copy was retained under TERNUXX_STATE_DIR/upgrade-backups/management-center-20261024T0358Z. No management-center process was running. The installer rebuilt and replaced the client. Installed binary SHA-256 is 71eceb0810c152d65ff93937fe17c399b8e4bb0b0426d5696f71971999e1b591; source and bridge hashes match the current checkout. The installed binary reported GTK 4.24.1 and VTE 0.84.1 under --self-check. No GUI was opened, so visible rendering and interactive dialog behavior remain unverified.

## Remaining P4 work

The migration still needs disposable full-guest integration and injected interruption/rollback checks before any live apply. The existing default Debian guest remains untouched. GTK source and installed binary match; visible rendering and interactive dialog behavior remain unverified. Continue the distro onboarding/account work after this gate: separate fresh installs, distro-specific package and user setup, and install parity across CLI/TUI/Web/GTK are not yet implemented.
