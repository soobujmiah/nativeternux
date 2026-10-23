# P4 terminal broker recovery and package preview UX

Phase: `P4`

## Scope

This evidence records the Native terminal broker stale-socket recovery and the concise Native package preview changes in the 2026-10-24 working checkout. It does not close P4 or qualify a clean-device installation.

## Terminal broker recovery

- The Native Runit service `ternuxx-terminal-broker` was installed from matching source but repeatedly restarted because its private Unix socket already existed.
- The exact socket was `$HOME/.local/share/ternuxx/terminal-broker.sock`, owned by the Termux UID with mode `0600`; a local connect probe returned `ECONNREFUSED`. No matching listener was found with the permitted socket inspection. `/proc/net/unix` was not readable in this context.
- Recovery preview ID: `29f7722396182e2af1778c417641be7b4db2cf7034b91a7256d20b87770eb2f9`.
- Apply rechecked the socket identity and refused connection, then removed only the unchanged socket inode. Runit created a new private socket and returned to `running`; `tx terminal status` returned `ok`, with `pty_relay=not_connected`.
- The broker service was restarted once after the lifecycle-lock change while no broker PTY was attached. No PRoot guest was started. The active Debian PRoot PID 590 and Native desktop processes remained alive.
- Source changes add exact preview/recovery commands and serialize socket creation/recovery with one private lifecycle lock. Recovery fails closed on an active listener, unknown probe result, or identity drift.

## Package preview UX

- `tx install preview` and `tx install update preview` now print a short summary: requested-package count, resolved-change count, safety scope, preview ID, and exact apply command.
- Append `--verbose` to show the candidate versions and full APT simulation. Both modes persist the complete preview record and use the same exact-plan apply check.
- `python3 -m unittest discover -s tests -p test_package_plan.py -v`: 16 tests passed in this checkout.
- `bash -n lib/phases.sh` and `git diff --check` passed.
- A desktop lifecycle fixture test attempted from this non-Termux shell timed out during its first mock desktop startup; it is not counted as passed. Its test cleanup was corrected to stop its exact second fixture supervisor before temporary mock binaries are removed. Fourteen previously orphaned fixture mock processes were verified by exact command, UID, parent, and process group and then cleaned; no fixture process remained afterward.
- Authenticated Native repo access uses configured `ssh termux` on port 8022. Read-only installed `tx install update preview` returned a concise summary and exact apply plan; no packages were applied.

## Evidence

- Read-only runtime status and socket recovery were observed in Native Termux on 2026-10-24; the existing guest and Native display were preserved.
- Focused package-plan tests cover concise and verbose output and preserve the full exact transaction flow.
- P4 remains active. Full Native suite and installed Debian adoption preview now pass; next implement preview-bound guest package/config adaptation and expose the same operation through all management clients. All-provider distro discovery, optional groups, and selectable Native/guest desktop profiles remain open.


## Existing Debian integration CLI preview

On 2026-10-24, `./tx install debian preview` on Native Termux resolved the current rootfs as Debian 13/Trixie, guest user `sbj`, and the existing rootfs device/inode. The preview recorded both expected Turnip driver files as present and reported `guest_mutations: []`, `package_changes: []`, and `service_changes: []`. Plan ID: `f72a37a34569ddcc50d8e790fc18386205ed7bf9ca1976b86f6e684cf73b0b66`. No apply was run. This verifies profile adoption only; it does not qualify package installation, desktop selection, or cross-client parity.


## Verification after Debian CLI integration preview

`bash scripts/repo_test.sh` ran in Native Termux on 2026-10-24: 908 tests passed, 1 skipped, in 119.225 seconds. This included the four new CLI adapter tests. Focused results: `test_proot_setup.py` 7/7, `test_package_plan.py` 16/16, and `test_debian_install_cli.py` 4/4. `python3 -m tools.repo_knowledge verify` reported 0 findings; `bash -n lib/phases.sh` and `git diff --check` passed. The existing guest preview was run twice with identical plan ID `f72a37a34569ddcc50d8e790fc18386205ed7bf9ca1976b86f6e684cf73b0b66`; no apply occurred. Full guest package migration, optional groups, desktop choices, all-distro recipes, and shared TUI/Web/GTK install parity remain open.
