# Native recovery inspection client parity — 2026-10-24

## Change

Added guided read-only backup and recovery inspection to the TUI, Web, and GTK clients. Users can list/inspect backups, preview a restore, inspect operation records, preview eligible restore rollback, and check reboot-continuity status. Every action dispatches through the existing typed management service. The GTK bridge accepts only fixed operation names and constrained backup/operation identifiers. No mutation capability or scope was added to the Web session.

The TUI action menu selects records from service results. Web prompts validate entered IDs against the current result set. GTK displays an identifier entry with separate typed read/preview buttons; invalid references are refused by the bridge and validated again by the shared service.

## Verification

- Focused TUI, Web, GTK bridge, and recovery contracts passed.
- Full `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: **730 tests passed** in 93.780 seconds.
- GTK4 `clang -fsyntax-only -Wall -Wextra` passed.
- `git diff --check`, `python3 -m tools.repo_knowledge verify`, and document inventory/link checks passed; 0 broken links and current path/hash coverage.
- Live Native `tx backup list` returned no saved backups. `tx recovery status` found 64 operation records and 0 unresolved records. `continuity.status` reports two historical checkpoints `NOT_READY`, with automatic resume disabled. All are read-only observations.
- The Native desktop, audio, SSH, and Termux app were not stopped or restarted.

## Remaining limits

Backup creation, restore and rollback apply, recovery resolution, and continuity checkpoint preparation/verification remain CLI-only. No test checkpoint was created and no reboot was requested. Broader client parity, accessible/visual acceptance, clean-device and boot qualification, and the documented public-release decisions remain open.
