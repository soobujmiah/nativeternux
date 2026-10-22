# P3 Doctor implementation progress

- Phase: P3 implementation progress after P2 completion; not a completion record
- Reviewed: 2026-10-18
- Evidence type: source implementation, disposable lifecycle fixtures, and read-only device observations
- Device/runtime actions: read-only checks; no live lifecycle mutation

## Source now present

- `lib/doctor_report.py` collects read-only host, package, Android companion, graphics-node, storage, and Ternuxx session findings.
- Findings use stable IDs, severity, scope, observed value, and suggested action. JSON reports declare schema version 1 and are specified by `schemas/doctor-report.schema.json`.
- `doctor` skips renderer/Vulkan probes by default. `doctor --graphics` explicitly queries tools in the current `DISPLAY`; it does not start a display or workload.
- Findings distinguish native Termux context from non-Termux/PRoot execution. Device nodes and Vulkan summary output are not reported as proof of workload acceleration.
- The report never repairs state, starts/stops services, installs packages, scans shared storage, or signals processes. It now inspects the private native operation journal and reports unresolved/invalid records without changing them.
- Native start/stop writes an atomic, fsynced, mode-0600 operation record before launching or signaling owned processes. Unresolved prior journal entries block a new lifecycle mutation; Doctor reports active records for manual recovery. The JSON schema is `schemas/operation-journal.schema.json`.
- The base native package plan now includes the official Termux `python` package because lifecycle/state code requires Python 3; the exact current candidate is checked against signed package indexes during each package preview.

## Read-only target-device observation

On 2026-10-17, `bin/ternuxx doctor --json` ran over the authorized native Termux SSH connection. It reported Termux `0.119.0-beta.3`, Android 16, `arm64-v8a`, Termux:X11 package `1.03.01-6`, D-Bus `1.16.2-3`, Python `3.14.6-1`, and PulseAudio `17.0-4`. The five checked XFCE packages (`xfce4-session`, panel, window manager, Thunar, and terminal) were absent. `/dev/kgsl-3d0` and the `Adreno825` model string were visible; no Ternuxx session record existed; HOME's filesystem had 88.1 GiB free. Doctor returned `overall=warning`, five warnings, and no errors.

An Android `pm path com.termux.x11` query returned exit 2 because the package service query failed. Doctor now reports companion-app presence as `unknown` on query failure; it does not label the app absent. The owner separately reports that the Termux:X11 GUI is open. The Doctor run did not start or stop a display/session and did not change packages or settings.

## Not established

- The native Termux `pm` wrapper cannot establish Android companion-app presence, signature compatibility, or permissions, so Doctor leaves those fields unknown when that route fails. The direct native `cmd package path` route now confirms Termux:Boot package presence; a PRoot-side ADB query independently confirmed the same. Package presence does not prove signature/permission policy or visible GUI startup.
- Package and Android add-on status depend on commands exposed by the current Termux environment; inaccessible values remain unknown.
- `doctor --graphics` is a diagnostic probe only. It cannot prove a specific application used the renderer or accelerator.
- Doctor reports the installed `proot-distro` container inventory without entering a guest, but this does not establish Ternux ownership or running-session identity. Full PRoot provider lifecycle/workload management remains unavailable pending an ownership-aware adapter. Doctor also does not correlate the managed SSH service with a listener. Backup integrity and Runit service/config status are reported; listener correlation remains explicitly unverified. Native profile selection and enable/disable code are fixture-tested, but target device apply and post-reboot delivery are not qualified. Source/fixture recovery covers every journal kind currently declared in `lib/operation_journal.py` through an operation-specific `recovery resolve`; compensating rollback remains limited to profile restore, and generic task resume is unsupported.
- The broader P3 management and recovery phase remains in progress; this file does not complete P3.

## Next P3 gates (reviewed 2026-10-18)

- Source/fixture gate: `recovery.resolve` now dispatches every kind currently declared by `lib/operation_journal.py` (desktop start/stop, boot enable/disable, native SSH service start/stop, backup create, profile restore/rollback). Keep new operation kinds blocked until a matching bounded handler and fixture exist. Current suite: 183/183.
- Native device gate: existing desktop `:1` is running, while CLI GUI visibility remains `unknown`; owner-visible GUI confirmation is separate evidence. Do not restart it for this check.
- Boot gate: Termux:Boot package and script directory are present, but startup delivery policy is `unknown`; the configured profile is `cli-only`. A fresh read-only preview says the native profile prerequisites are ready, but Android GUI visibility and actual cold-boot delivery remain unverified. PRoot/hybrid previews remain blocked by absent ownership/routing adapters. No profile was applied because no profile selection was present. Obtain a selected profile and disposable/authorized test profile before any apply/reboot test. Preview details: [boot-profile preview recheck](2026-10-18-p3-boot-profile-preview-recheck.json).
- PRoot handoff gate: Debian is inventoried as installed, but guest owner/session identity, launch environment parity, and display/audio handoff remain unverified. Do not enter or manage the guest as Ternuxx until the fixed ownership contract is implemented and validated.
- SSH gate: fixed managed Runit service `ternuxx-sshd` is running with matching definition/config and a loopback banner at 8023. Listener PID correlation remains `unknown` because Android denies `/proc/net/tcp*` and NETLINK_SOCK_DIAG (EACCES); native package-default SSH remains wildcard-bound with password authentication enabled and is flagged by Doctor. Do not infer external reachability from bind configuration or the ADB listener observation.
- Reboot checkpoints: RB03 remains `boot_observed`, RB02 `inconclusive`, RB01 `prepared`; all remain `NOT_READY` and automatic resume is false. Resolve/close only through their explicit verification workflow after reviewing their evidence; do not delete checkpoints to make the gate appear clean.
- A fresh read-only native snapshot and detailed per-command outputs are recorded in [current P3 gate snapshot](2026-10-18-p3-current-readonly-gate-snapshot.json). No device mutation was performed for that snapshot.


## 2026-10-18 P3 Doctor integration update

- The stable-finding Python Doctor report is now the implementation behind `ternuxx doctor`; `check` remains the quick prerequisite check. `doctor --graphics` explicitly probes the current `DISPLAY`, and `--json` emits the versioned report contract. The Doctor accepts both current `ternuxx` and legacy `ternuxx` session-owner identifiers during the existing state-path transition.
- The report code remains read-only and a missing/failed Android package-manager query stays `unknown`; it does not start/stop desktop services or infer GUI visibility from process health.
- On 2026-10-18, the native CLI `doctor --json` returned a structured report on the attached Termux target. The CLI's `DISPLAY=:1 doctor --graphics --json` additionally selected `llvmpipe (LLVM 21.1.8, 128 bits)`; default Doctor skips graphics probes. No package/service/session changes were made by either read-only call.
- The full native Termux repository suite passed 59/59 after Doctor integration and before operation-journal work. The journal and follow-up changes are recorded in the 2026-10-18 evidence section below. P3 is still incomplete; boot, backup/recovery, and cross-provider ownership gates remain.


### 2026-10-18 Doctor integration verification

- `python3 -m unittest tests.test_doctor_report -v` passed 6/6 after wiring the report into the public CLI. The tests cover stable IDs/schema, package-query unknown state, private-path handling, current and legacy owner identifiers, supervisor identities without recorded process groups, and strict group/session checks for child processes.
- `./ternuxx doctor --json` on the attached Termux target returned `overall=pass`, 13 pass findings, 10 informational findings, and no warnings/errors. It verified session `:1`, supervisor PID/start-time/command identity, X11 and XFCE process-group identities, and reported inaccessible Android add-on queries as unknown.
- `DISPLAY=:1 ./ternuxx doctor --graphics --json` returned the expected warnings for native `llvmpipe (LLVM 21.1.8, 128 bits)` and native Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER`. This is correctly separate from the PRoot Zink/Turnip evidence and proves no native acceleration claim. Both reports were read-only.
- `bash tests/test_cli_help.sh`, the full repo suite, shell syntax checks, JSON parsing, and `git diff --check` are run again after the current integration changes; exact results are recorded in the session handoff.


### 2026-10-18 durable lifecycle journal

- Added `lib/operation_journal.py` and its schema. Records are atomically replaced and fsynced, protected by a private per-journal lock, stored below the private Termux state directory at mode 0600 (directory mode 0700), and restricted to paths inside HOME.
- Native desktop start/stop writes a `starting`/`stopping` record before launching the supervisor or signaling the verified supervisor. Confirmed outcomes become `complete`/`failed`; uncertain startup or stop outcomes become `needs_recovery`. A new start/stop refuses an unresolved earlier journal entry. Restart records the stop and start separately.
- Doctor reports unresolved operation kind/status and asks for manual review of the journal, session record, and log; it does not resume, repair, or mutate. Tests cover private modes, atomic lifecycle transitions, path and status rejection, unresolved-operation guard, Doctor read-only finding, and fixture start/idempotency/stop/repeat record counts.
- Verification: targeted journal/Doctor tests 10/10 across both modules; lifecycle fixture 6/6 after asserting journal behavior; full repository suite 63/63.
- Read-only target check: `./ternuxx status --json` still reported `:1` with supervisor/X11/XFCE alive. `./ternuxx doctor --json` returned `overall=pass` with 13 pass, 11 info, 0 warning, 0 error; journal reported no prior records. We did not stop/restart the live GUI to create a device journal record.

P2 is complete; P3 remains the active roadmap phase. Native lifecycle journaling, Doctor inventory, boot-profile previews, bounded profile backup/restore, and operation-linked profile rollback are implemented. Ownership-aware PRoot/hybrid integration, broader recovery, and separate cold-boot/retry qualification remain open.


### 2026-10-18 boot profile status and preview

- Added a read-only profile planner behind the same allowlisted local management API as boot status: ternuxx boot profile status and ternuxx boot profile preview <cli-only|native|proot|hybrid>. The status/preview report contract is schemas/boot-profile-preview.schema.json, the enable/disable contract is schemas/boot-profile-action.schema.json, and the private profile config contract is schemas/boot-profile.schema.json.
- cli-only is the non-writing default. Native preview checks the ternuxx, termux-x11, and xfce4-session commands and prints the exact startup command without installing it. Its readiness is limited to command prerequisites; it does not claim Termux:Boot delivery or Android background policy, and GUI activity visibility remains unverified.
- PRoot and hybrid profiles return blocked plans with no generated startup script until their ownership-aware adapters exist. No provider fallback occurs. The status/preview commands do not install scripts, persist a profile, start services, or touch the existing Ternux environment. Enable/disable code exists but was exercised only with disposable HOME fixtures, not on the attached device.
- Read-only native Termux results on 2026-10-18: current profile cli-only (default); native preview reported command prerequisites ready; hybrid preview reported its adapter missing; ./ternuxx status --json still showed the desktop on :1 with supervisor/X11/XFCE alive.
- Tests cover default/read-only status, native prerequisite pass and fail, unsupported PRoot/hybrid blocking, schema-identity rejection, HOME/symlink escape rejection, shell-prefix injection rejection, preview-first enable/disable, positive app detection, exact-owned-file scope, idempotency, rollback, journaling, and management API integration. Targeted profile/management/journal tests passed 26/26 with generated-shell syntax validation; the complete Native Termux repo suite passed 77/77 with the same assertion.
- Profile selection is now applied only through enable --profile after explicit --yes. The implementation requires a positive Termux:Boot package query and native command prerequisites, writes only the Ternuxx-marked 10-ternuxx-profile script plus a private profile record, and journals before mutation. Disable previews first and removes only that exact recognized script and profile record; unrelated files are preserved. The file is named 10-ternuxx-profile so it runs after the existing 00-ternuxx-services entry under Termux:Boot's sorted execution order, documented in the [official Termux:Boot README](https://github.com/termux/termux-boot). Ordinary failure rolls back; a process interruption leaves an unresolved journal entry for Doctor.
- The attached target's read-only enable preview returned boot_app_status=unknown because Android package-manager querying from the Termux process failed. It made no changes and correctly blocks applying enable. Disable preview reported no Ternuxx profile script present. Read-only boot status reports Termux:Boot app unknown, startup directory present with 2 regular files (0 non-executable), and termux-boot command unavailable; script contents were not read. Current profile is the cli-only default.
- After the CLI previews, ./ternuxx doctor --json returned overall=pass (13 pass, 11 info, 0 warning/error), and ./ternuxx status --json still reported :1 with supervisor, X11, and XFCE alive.
- Remaining controls/gates: Termux:Boot must be opened once by the owner; no device enable/disable or post-reboot profile test was performed. Native boot does not request the Android X11 activity or prove visible GUI state. PRoot and hybrid profiles remain blocked pending ownership-aware adapters. This is not a P3 completion record.

### 2026-10-18 boot operation journal regression fix

- A source audit found `operation_journal.begin()` computed the initial status for all four operation types but serialized a separate desktop-only conditional. As a result, `boot.enable` was incorrectly journaled as `stopping`.
- The record now writes the validated operation-specific initial status. Added a fixture test that creates a boot-enable record (`starting`), completes it, then creates a boot-disable record (`stopping`).
- `python3 -m unittest tests.test_operation_journal -v` passed 5/5. The first full suite invocation passed 76 tests but could not import the documented development-only PyYAML dependency in the base Termux Python. Re-running with `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` passed 78/78. No product package was installed and no device state was mutated for this test run.
- This was fixture/source verification; target `:1` GUI, PRoot, SSH, and boot state were not changed. At that point, P2 still lacked its final install-preview evidence. P2 later completed after the target-native saved-preview validation; the original pre-consent capture gap and exact applied dependency closure remain documented in [P2 phase completion](P2-phase-completion-2026-10-18.md).

### P2 installer approval binding follow-up (2026-10-18)

- Installer `--yes` now requires a user-reviewed saved preview ID. The complete current APT simulation and closure must exactly match the 0700/0600 private saved record before any package mutation. Outside-HOME or symlinked state paths fail closed. Preview JSON includes the hash ID and has a dedicated schema.
- Verification: targeted package-plan tests passed 11/11, including the pinned-closure apply helper; `bash -n lib/phases.sh` and `bash tests/test_cli_help.sh` passed. After the final pinned-closure helper, `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` passed 83/83. No device package mutation was performed.

### 2026-10-18 bounded configuration backup and restore slice

- Added a versioned JSON archive format with per-entry SHA-256, canonical whole-manifest checksum, timestamp, software/schema version, and explicit exclusions. The initial allowlist is intentionally one file: the schema-validated Ternuxx native boot profile at state/boot/profile.json; archives record an explicit absent marker when the profile has never been configured. It excludes SSH config/credentials, runtime session data, logs/journals/nonces, Termux:Boot scripts, PRoot/rootfs, shared storage, and all other home paths.
- Added allowlisted local management operations and CLI routes for backup preview/create/list/inspect and restore preview/apply. Create and restore use explicit plan IDs; restore binds the plan to archive integrity and current destination state, makes a rollback snapshot, writes atomically to the fixed profile path, and records the operation in the journal.
- The reader rejects unknown archive fields/schema/software version, corrupt checksums/base64, duplicate/unowned paths, oversized entries, symlink/outside-HOME paths, and changed restore targets. The archive and backup directory are constrained to 0600/0700.
- Fixture verification: tests.test_config_recovery 7/7, tests.test_management_service 12/12 (includes backup and journal APIs), tests.test_recovery_cli 4/4, and tests.test_operation_journal 7/7 passed. Full Native Termux suite passed 99/99. Python compilation, Bash syntax, CLI help, and JSON syntax checks passed.
- Target read-only smoke on 2026-10-18: ./ternuxx backup list --json returned an empty list without creating the state/backups directory; backup create preview returned a read-only absent marker because no boot profile is configured; restore preview against a missing archive failed closed; recovery status returned zero journal records and zero unresolved operations. No target backup was created and no restore/config mutation was run.
- Scope remaining: only boot profile is included; managed SSH settings and other safe application preferences need a separately reviewed schema/allowlist. Generic operation resume/rollback beyond profile restore, PRoot ownership, Termux:Boot delivery, cold-boot/retry, and ownership-checked service actions remain open. P3 is in progress.

### 2026-10-18 Doctor backup-integrity integration

- Doctor now calls the existing allowlisted read-only backup inventory. It reports no backups as `info`, all valid archives as `pass`, corrupt archives as `warning` (`NTX-BACKUP-002`), and inaccessible/unsafe state as `warning`; it never creates a directory or repairs/removes an archive. No backup identifiers, archive contents, or absolute paths are exposed in these findings.
- Added fixture coverage for empty state without directory creation, invalid integrity, and an outside-HOME state path. `python3 -m unittest tests.test_doctor_report -v` passed 9/9. Full Native Termux suite passed 102/102 with the private audit venv's PyYAML on `PYTHONPATH`.
- Target read-only validation on 2026-10-18 Asia/Dhaka (2026-10-17 UTC): `./ternuxx doctor --json` returned `overall=pass`, 13 pass / 12 info / 0 warning / 0 error, including `NTX-BACKUP-001` no-backup info. `./ternuxx status --json` still reported display `:1`, supervisor/X11/XFCE running; `backup list` was empty and `recovery status` showed zero unresolved operations. `git diff --check` passed. No backup directory or archive was created, and no desktop, package, boot, PRoot, or SSH state was mutated.
- This is a read-only observability improvement; it does not close the remaining P3 gates for service-manager interoperability, ownership-aware PRoot/hybrid adapters, broader reviewed backup allowlists, operation recovery actions, or separate cold-boot/retry qualification.

### 2026-10-18 read-only desktop process inventory

- Doctor now inventories only a fixed set of desktop process `comm` names from visible `/proc`; it does not read command arguments. A Ternuxx root is counted only when its session record matches PID, start time, command marker, and recorded process-group/session identity. Matching root PIDs are reported by role so a differently named executable such as the recorded X11 process (`comm=main` on this target) is not missed. Other known desktop names sharing a verified recorded session ID are grouped separately; the remaining candidates stay owner-unverified. None are called “external” from name alone or become eligible for management.
- Visible procfs does not prove Android/other-app process completeness, and same-session association is not standalone lifecycle ownership. Hidden processes may not appear. Current evidence leaves one `dbus-daemon` candidate owner-unverified; no claim was made about its origin.
- Fixture verification covers exact owned-root identity, same-session grouping, owner-unverified classification, and redaction of PIDs/arguments. `python3 -m unittest tests.test_doctor_report -v` passed 11/11; the full Native Termux repo suite passed 104/104.
- Target read-only Doctor on 2026-10-18 Asia/Dhaka reported overall `pass` (13 pass / 13 info / 0 warning / 0 error): verified roots `supervisor=1`, `x11=1`, `desktop=1`; same-session XFCE candidates `xfce4-panel=1`, `xfdesktop=1`, `xfwm4=1`; `dbus-daemon=1` owner-unverified. `./ternuxx status --json` continued to show `:1` and supervisor/X11/XFCE running. No processes were signaled and desktop/PRoot/package state was not changed.
- P3 still needs ownership-aware service-manager adapters and a supported way to identify candidate process origin beyond visible procfs; this inventory is diagnostic only.

### 2026-10-18 native service-manager Doctor integration

- Doctor now summarizes the existing read-only `ssh_diagnostics.inspect_native` adapter as stable finding `NTX-SVC-001`: Termux Runit availability, the fixed `ternuxx-sshd` unit status, and managed configuration syntax. It reports unavailable/unknown without silently selecting another manager. It does not start/stop services, return raw configuration, inspect credentials, or claim that a running service proves a reachable listener.
- Fixture tests cover a valid running Runit service while retaining `listener correlation=unverified`, and the missing-manager no-fallback case. `python3 -m unittest tests.test_doctor_report -v` passed 13/13. Full Native Termux suite passed 106/106.
- Target read-only validation on 2026-10-18 Asia/Dhaka: `doctor --json` returned overall `pass` (14 pass / 13 info / 0 warning / 0 error), with `manager=runit`, `service=ternuxx-sshd`, `status=running`, `config syntax=valid`, and listener correlation unverified. Separate `ssh inspect --json` agreed: `runit_available`, service running, syntax valid. `status --json` still showed `:1`, supervisor/X11/XFCE running. No service, desktop, PRoot, boot, or package state changed; `git diff --check` passed.
- This is inventory/status interoperability only. Ownership-checked service actions, general service tooling integration, authenticated remote-access exposure, GUI/Web parity, and post-reboot qualification remain outside the verified gate.

### 2026-10-18 explicit rollback for journaled profile restores

- Added `ternuxx recovery rollback OPERATION_ID` as a read-only preview and `... --yes --plan-id PLAN_ID` as the confirmed apply form. It accepts only journaled `recovery.restore.apply` or `recovery.restore.rollback` operations in `complete` or `needs_recovery` state and resolves the deterministic, integrity-checked pre-change snapshot for the fixed native boot-profile path. No other operation kind or file path can be selected.
- The plan ID binds the rollback archive and current destination hash. Apply creates a fresh rollback snapshot before replacement/removal, including a tombstone when the profile was absent, validates the result, and writes a `recovery.restore.rollback` journal record linked to its parent operation. Successful compensation changes a `needs_recovery` parent restore to `failed`; completed parents stay complete. A rollback itself can be rolled back. Unresolved unrelated operations block the action; the journal permits only a matching restore ancestry chain.
- Failure-injection fixtures interrupt after the target replacement, then preview/apply the snapshot and verify the prior profile is restored and the parent journal becomes failed. Other fixtures cover rollback of a completed restore, reversing a rollback, nested unresolved recovery, wrong/absent parent IDs, refusal when unrelated work is pending, and rolling back a restore that added a previously absent profile (using an explicit absence marker). Target data was not used for rollback tests.
- Verification: configuration recovery 11/11, operation journal 11/11, recovery CLI 5/5, management service 13/13; full Native Termux suite 116/116. Python compilation, shell syntax, CLI help contract, JSON schema parsing, and `git diff --check` passed.
- Target read-only state on 2026-10-18: `recovery status` showed no operation records/unresolved operations; `backup list` was empty. There was no target restore record or rollback archive to apply. No target profile, desktop, SSH, boot, PRoot, or package state was changed. The existing `:1` desktop remained running.
- Scope remains deliberately explicit: only the boot profile is backed up/restored/rolled back. Other lifecycle journal kinds are still inspection-only; generic operation resume/rollback and PRoot/hybrid recovery are not implemented.


### 2026-10-18 native Termux:Boot package-query correction

- Read-only target comparison showed `pm path com.termux.boot` exits 2 in the native shell while `cmd package path com.termux.boot` returns the installed package path. `runtime_diagnostics.inspect_boot` now prefers the fixed `cmd package path` query and falls back to `pm path`. It reports `not_installed` only for an explicit package-not-found response; empty or failed output remains `unknown`. No command input is derived from user data.
- Fixture verification: `python3 -m unittest tests.test_runtime_diagnostics -v` passed 7/7, covering direct `cmd`, `pm` fallback, explicit absence, and ambiguous empty/failing responses.
- Read-only target smoke: `boot status --json` reported `app=installed`; native profile preview returned `ready=true`; `boot enable --profile native` returned a preview with `requires_confirmation=true` and `changed=false`. The configured profile remained `cli-only`, the boot directory still had two scripts, and no `--yes` apply was run. Earlier reboot evidence proves the Termux:Boot observer script ran once, but it does not qualify native XFCE startup or GUI visibility at boot. The updated complete Native Termux suite passed 119/119 after this change.


### 2026-10-18 read-only PRoot inventory

- Added `proot_diagnostics.inspect_installed()` and stable Doctor finding `NTX-PROOT-001`. It runs only the fixed `proot-distro list` command, parses only the installed-container section, strips terminal control codes, suppresses command errors, and never enters, starts, stops, or edits a guest. The result explicitly keeps Ternux ownership and guest/session state unverified.
- Fixture tests cover ANSI-colored installed names, an empty inventory, unavailable manager, malformed output, command failure, and Doctor wording that does not claim Ternux ownership. They assert the exact fixed command.
- Native Termux read-only `proot-distro list` found one installed container (`debian`). The first Doctor attempt returned unknown because this command writes the listing to stderr; the adapter now merges output streams and suppresses failure text. The rerun returned `NTX-PROOT-001` with the `debian` inventory, while leaving ownership/session unverified. No guest login was started; the existing PRoot/rootfs and `:1` desktop were not changed. The complete Native Termux suite passed 123/123 after this change.
- A live Doctor report contract check found three pre-existing session finding IDs had two-digit suffixes despite the schema requiring three. They now emit `NTX-SESSION-020/021/022`; the fixture asserts every finding ID matches the schema pattern. The target report passes structural checks for required fields, types, stable ID shape, summary totals, and date-time. Full Native Termux suite passed 123/123 after the correction.


### 2026-10-18 consistent Android package presence reporting

- The native `pm path` wrapper fails its PackageManager transaction on this device, while `cmd package path` succeeds. Boot status already used the direct command; Doctor's separate add-on finder still used only `pm`, producing inconsistent results. Doctor now prefers the same fixed direct query and falls back to `pm`. It reports present only for a returned package path, absent only for an explicit not-found response, and unknown for failures or ambiguous empty output.
- Fixture coverage verifies direct-command preference, fallback ordering, and unknown handling for ambiguous output. `python3 -m unittest tests.test_doctor_report -v` passed 16/16.
- Target read-only results agree: Doctor reports Termux:Boot present; boot status reports installed. The default profile remains `cli-only`; no `--yes` apply ran and the two existing boot entries remain. Doctor reports overall `pass` (14 pass / 14 info / 0 warning / 0 error). The live `:1` desktop remains running; recovery journal and backup list are empty.
- The complete Native Termux suite passed 125/125 after the package-query and schema-ID corrections. No Android settings, package, boot script, desktop, SSH service, or PRoot state was changed.

### 2026-10-18 P3 regression-suite recheck

- Re-ran `scripts/repo_test.sh` from the current Ternuxx checkout after reboot/session continuation. The complete repository suite passed 125/125 in 67.437 seconds. The command runner identifies as outside the native Termux host (`doctor` returned `NTX-HOST-001`), so this is local fixture/unit evidence only; it is not a native Termux target run and does not qualify PRoot ownership, cold boot, listener reachability, or GUI visibility.
- `git diff --check` passed. `project/phase-state.json` still identifies P3 as `in_progress`; no phase transition, commit, or push was made.
- Earlier in this session, the authenticated native Termux shell returned read-only `status --json` with display `:1`, supervisor/X11/XFCE running, GUI visibility unknown, and audio owner external. A later local runner check reported the desktop stopped because that shell is outside native Termux; do not treat its runtime status as device evidence. No package, service, desktop, boot profile, or PRoot state was changed during this recheck.
- Native Termux recheck at 2026-10-18 03:24 +06: `status --json` still reported `:1`, supervisor/X11/XFCE running, GUI visibility unknown, and audio owner external. `doctor --json` returned `overall=pass` (14 pass / 14 info / 0 warning / 0 error): Termux:Boot present; owned roots `desktop=1`, `supervisor=1`, `x11=1`; same-session XFCE candidates; `dbus-daemon` owner-unverified; Runit `ternuxx-sshd` running with valid config but listener correlation unverified; installed `debian` with PRoot guest/session ownership unverified. Native `git diff --check` passed. All commands were read-only; no service, package, boot profile, desktop, or PRoot state changed.

### 2026-10-18 native Termux regression-suite recheck

- Ran `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` through the authenticated native Termux shell. All **125/125** fixture/unit tests passed in 31.509 seconds. This is a native-shell test run, while the tests themselves use fixtures/mocks and do not qualify Android GUI visibility, PRoot ownership, listener ownership, or cold boot.
- No APT transaction, service action, desktop start/stop, boot-profile apply, or PRoot login was run. The existing native desktop stayed running on `:1` in the immediately preceding read-only status/Doctor check.

### 2026-10-18 postboot resume guidance correction

- Native RB03 status showed `boot_observed`, but `resume-info` still returned the baseline instruction to perform the reboot. Running the verifier produced `verified_reboot_partial` because the boot observer's sshd/service fields were unknown. A separate live Doctor/SSH inspection later saw the managed Runit service running with valid loopback config, and a bounded password-authenticated loopback probe to `127.0.0.1:8023` returned its harmless success marker. The probe proves current postboot reachability but does not backfill the observer record or prove automatic service start. These observations are kept separate in [postboot verification evidence](2026-10-18-postboot-native-ssh-verification.json); no boot IDs, nonce, or password are copied into the repository.
- Updated `resume_info()` so `boot_observed` checkpoints direct the owner to review the recorded verification and manually confirm required service/connection evidence; an unverified observation points to `reboot verify`, and an inconclusive test no longer suggests continuing the old reboot action. `NOT_READY` and `automatic_resume=false` remain unchanged.
- Added a fixture covering the observed-but-unverified and verified-partial cases. `python3 -m unittest tests.test_reboot_recovery -v` passed 8/8 on native Termux; the full native Termux suite passed 126/126 in 31.795 seconds. Live native `reboot resume-info TERN-20261017-RB03 --json` now reports the partial outcome and manual-review action without changing the checkpoint or resuming a task.

### 2026-10-18 managed SSH loopback banner fallback

- Native target inventory found no `ss` command, and its `netstat` reports no IPv4 TCP support; `/proc/net/tcp*` listener enumeration remains unavailable. Added a bounded fallback that reads at most one SSH banner from the first valid, explicitly configured loopback `ListenAddress` in the managed `ternuxx-sshd` effective policy. It never probes a non-loopback address, reads credentials, authenticates, or claims PID/listener ownership. `NTX-SVC-001` warns if the managed unit says running but the expected SSH banner is unreachable or is another protocol.
- Fixture tests cover SSH banner success, refusal to probe wildcard/non-loopback policies, unreachable endpoints, unexpected protocol, and the Doctor warning path. Targeted native tests passed 22/22.
- Native `ssh inspect --json` at 2026-10-18 03:42 +06 reported Runit service running, valid config, endpoint `127.0.0.1:8023`, and `loopback_ssh_probe=ssh_banner`; socket-table status stayed `unavailable` and listener correlation stayed `not_performed`. Doctor returned `overall=pass` (14 pass / 14 info / 0 warning / 0 error). `status --json` remained `:1`, supervisor/X11/XFCE running, GUI visibility unknown, audio owner external. Full native Termux suite passed 129/129 in 32.295 seconds. Details are in [loopback probe evidence](2026-10-18-native-ssh-banner-probe.json).
- No package, service, desktop, boot profile, or PRoot state was changed. This improves reachability diagnosis only; ownership-checked service actions remain unimplemented.
- After adding a defensive type check for malformed Doctor adapter results, reran the full suite from native Termux: **129/129 passed** in 32.290 seconds. Static compilation, shell syntax, CLI help, JSON parsing, whitespace, and repository-knowledge verification also pass for this worktree.


### 2026-10-18 managed SSH service-definition identity check

- ssh inspect now hashes only the fixed installed $PREFIX/var/service/ternuxx-sshd/run file and the corresponding checked-out scripts/termux-services/ternuxx-sshd/run definition. It rejects symlinked/non-regular unit paths, a service root/unit directory or script not owned by the current Termux UID, group/world-writable paths, and non-executable scripts. It reports only status and SHA-256 values; it never reads SSH configuration or credential files for this check.
- Initial read-only inspection found a source/deployed mismatch. After reviewing the complete script diff, the checked-out definition was aligned with the already-installed wrapper's timestamped log routing and explicit fixed Bash invocation for Ternuxx Wake Lock calls. The live service directory was not written, and no service was restarted.
- Recheck: installed and checked-out run-script SHA-256 both equal ec59008a2cbe3a8b7d5e13c72e0a8274d28ae238cd02ff1750a5901a683efb69. Runit still reports ternuxx-sshd running; a one-second loopback probe to 127.0.0.1:8023 reads an SSH banner. Doctor returned overall pass (14 pass / 14 info / 0 warning / 0 error), with listener ownership still explicitly unverified.
- Fixture checks cover exact definition match, content mismatch, symlink refusal, service-wrapper lease acquire/release, and log output. Targeted SSH/Doctor tests passed 24/24; the service-wrapper test passed 2/2 after aligning its fake Termux Bash path. After this source change the full native Termux repository suite passed 131/131 in 31.565 seconds.
- At the time of this identity-check slice, service actions had not yet been implemented. A matching script proves only fixed service-definition identity; it does not correlate the supervised process with the listener. Evidence: [2026-10-18-managed-ssh-definition-identity.json](2026-10-18-managed-ssh-definition-identity.json). P3 remains in progress; process/listener ownership, authorized service controls, recovery action completeness, PRoot ownership, and cold-boot/retry gates remain open.


### 2026-10-18 fixed native SSH Runit lifecycle controls

- Added CLI ssh start and ssh stop previews/apply through the allowlisted local management backend. Apply requires --yes and the exact preview plan ID. The plan binds current state, requested transition, checkout/installed run-script hashes, and the native sv binary hash; any state or identity drift fails closed.
- Apply controls only sv up ternuxx-sshd or sv down ternuxx-sshd. The service definition and manager path must be regular, owned by the Termux UID, executable where applicable, and not group/world writable. A fixed-unit definition mismatch, unknown Runit status, missing manager, invalid confirmation, or wrong/stale plan prevents action. No process-name killing or alternate service-manager fallback exists.
- A service.start / service.stop journal record is written before invoking sv. Success requires observed target Runit state. Timeout is recorded as needs_recovery, which blocks retry until reviewed. Stop preview explicitly warns that clients using the managed SSH port may disconnect.
- Fixture tests cover start, stop, no-op preview, wrong plan, status race, definition mismatch, journal completion, timeout, and retry blocking. Management API allowlist, journal kinds/schema, CLI help contract, and response schema were updated. Focused service tests passed 6/6; management/journal integration tests passed 32/32 before the response-schema assertion was added.
- Native target checks were read-only: the fixed script and sv command identities matched; ssh start preview found the service already running and required no confirmation; ssh stop produced a confirmation-bound preview. No --yes action was run. status --json still reported display :1, supervisor/X11 active; Doctor returned 14 pass / 14 info / 0 warning / 0 error. PRoot and desktop processes were not changed.
- Evidence: [2026-10-18-native-ssh-service-control.json](2026-10-18-native-ssh-service-control.json). This remains a partial P3 implementation: no authenticated post-action test, external listener correlation, boot/cold-start test, SSH config setup/migration, Web/X11 parity, or target service action is established.

- Final verification: native Termux `bash scripts/repo_test.sh` passed **138/138** in 31.807 seconds after installing the already-declared `requirements-dev.txt` dependency PyYAML 6.0.3 into the Termux user Python site. The first run exposed this missing local test dependency (135 passed, 1 import error); no application/system package or service action was performed. `bash tests/test_cli_help.sh` and `git diff --check` passed. Read-only `recovery status` reported zero unresolved operations. The test dependency install is recorded in the linked evidence JSON; it is not a product installer dependency.
- Additional read-only ownership audit on the attached Termux target: `ss` is absent and both `/proc/net/tcp` and `/proc/net/tcp6` return permission denied. `ssh inspect` consequently reports listener observation unavailable; the loopback 8023 SSH banner proves reachability only, not that the Runit-owned `sshd` owns that socket. This is an environment capability gap, not a passing correlation check. See the updated service-control evidence JSON. No privileged workaround or extra package was installed.


### 2026-10-18 SSH service journal reconciliation

- Closed a recovery dead-end for fixed native SSH start/stop operations: when a bounded action times out and records `needs_recovery`, `recovery resolve OPERATION_ID` now previews the exact journal timestamp, checked-out and installed run-script hashes, Runit binary hash, current Runit state, requested state, and terminal resolution.
- Apply requires `--yes` and the exact preview ID, re-observes the unit, and atomically resolves only the matching `needs_recovery` service record. It marks `complete` only when current Runit status equals the requested target; otherwise an explicit owner-confirmed review records `failed`. It never invokes `sv up/down`. The journal refuses stale timestamps, inconsistent outcomes, unrelated pending operations, and records of other kinds.
- Management API, CLI help, OPERATIONS and roadmap contracts, typed response schema, and fixture tests were updated. No device journal was resolved and no target service action was run.
- Focused service-recovery/management/journal tests passed **38/38**; full native Termux suite passed **143/143** in 31.110 seconds. CLI help, compileall, shell syntax, schema JSON, diff check, and repo-knowledge verify (0 findings) passed. Read-only target checks found SSH running, start no-op, stop confirmation preview, zero unresolved operations, Doctor 14 pass / 14 info / 0 warnings/errors, and desktop :1 active. No recovery or service apply was performed. Evidence: [service recovery evidence](2026-10-18-service-journal-recovery.json).


### 2026-10-18 native boot-profile journal reconciliation

- Extended `recovery resolve OPERATION_ID` to interrupted `boot.enable` and `boot.disable` journal records, including both crash-left `starting`/`stopping` records and `needs_recovery` records.
- Resolution is read-only until exact confirmation. It validates bounded paths, regular-file identity, owner/mode, recognized Ternuxx script bytes, profile JSON, and hashes; it then updates only the one matching journal record. Unknown scripts, symlinks, unsafe modes, corrupt profile data, stale plans, or unrelated active operations fail closed. It never edits files, launches the boot script, or changes Android settings.
- Enable intent is retained in the journal detail across ordinary rollback failure, so a later resolution can identify the requested profile. Old interrupted enable records without recoverable intent fail closed for manual review.
- Generic operation recovery now dispatches only service start/stop and boot-profile enable/disable. Desktop session, restore, and other journal operations remain outside this resolver.
- Fixture and management/journal tests passed **39/39**; the full native Termux suite passed **150/150** in 31.812 seconds. CLI help, compileall, shell syntax, schema parsing, and `git diff --check` passed. Read-only target check: profile is still default `cli-only`, recovery unresolved count is zero, and desktop :1 remains active. An invalid-ID CLI preview was refused without journal change. No target profile, service, desktop, or PRoot action was applied. Evidence: [boot-profile recovery record](2026-10-18-boot-profile-recovery.json).


### 2026-10-18 read-only PRoot inventory API

- Added `proot status` as a CLI/management-service entry point to the existing `proot-distro list` inventory probe. It never enters the guest, executes guest commands, changes packages, or claims Ternuxx ownership of Debian.
- The response preserves `ownership: unverified`, `guest_entered: false`, and read-only scope; this is an inventory surface only. PRoot workload launch, display/audio handoff, GPU proof from a same-process workload, and lifecycle ownership remain future gates.
- Native Termux fixture/management tests passed **21/21** in 0.133 seconds; the full native suite passed **151/151** in 32.918 seconds. CLI help, `compileall`, shell syntax, `git diff --check`, and repo-knowledge validation passed. Live `proot status` reports Debian installed, ownership unverified, guest not entered, read-only. Evidence: [read-only PRoot inventory API](2026-10-18-proot-inventory-api.json).


### 2026-10-18 native desktop-session journal recovery

- Added generic `recovery resolve OPERATION_ID` support for interrupted `desktop.start` and `desktop.stop` records. Preview validates the private session file, exact Ternuxx schema/provider, recorded process start ticks, fixed command markers, and process group/session identity; it binds the session hash and journal timestamp into the plan ID.
- A live session lock, active/ambiguous lifecycle result, unsafe state file, stale plan, or unrelated pending operation fails closed. The preview lists the exact journal file path that is the only affected path. Confirmed recovery updates only that record. It never sends signals, deletes the session lock, or edits `session.json`. `stop_incomplete` resolves to failed even if a child remains, leaving any later stop as a separate reviewed operation.
- All supported SSH service, boot-profile, and desktop-session recovery previews now return the exact single journal path that an approved resolution may update. Their service definitions, boot files, and desktop session state remain inspection-only; no desktop processes are signaled.
- Fixture tests passed **47/47** in 1.077 seconds; the full native Termux suite passed **158/158** in 32.471 seconds. CLI help, compileall, shell syntax, schema parsing, diff check, and repo-knowledge verification passed. Target read-only status: recovery unresolved 0; desktop :1 supervisor/X11/XFCE running; PRoot Debian installed, ownership unverified, guest not entered. No journal resolution or lifecycle action was applied. Evidence: [desktop-session recovery](2026-10-18-desktop-session-recovery.json).


### 2026-10-18 dependency and capability fallback matrix

- Added [DEPENDENCY-FALLBACK-MATRIX.md](../DEPENDENCY-FALLBACK-MATRIX.md) against the current package planner, desktop lifecycle, Doctor, SSH Runit adapter, boot-profile checks, PRoot inventory, Wake Lock manager, and recorded native/guest graphics evidence.
- The matrix separates package/app presence from service readiness and process ownership; keeps native and PRoot renderer evidence in their own contexts; and records “unknown/unavailable” rather than switching providers or installing a substitute. This is source-backed behavior documentation, not a fresh package-index scan or device mutation qualification.
- The full native Termux suite passed **158/158** in 32.378 seconds after the current CLI/help changes. Exact package candidates remain governed by the next preview against fresh signed indexes; no package plan was applied for this matrix.
### 2026-10-18 interrupted backup-create recovery

- Generic recovery now handles `recovery.backup.create` records. The preview parses only the constrained journaled backup ID, validates the exact archive and manifest checksum, and binds archive integrity plus journal timestamp into its plan. A valid archive resolves `complete`; an absent archive resolves `failed`; a corrupt, unsafe, or unrecognized archive remains unresolved. Explicit confirmation updates only the single operation-journal record; it never edits the archive.
- Added response schema and fixture coverage for valid archive completion, absent archive failure through the management API, corrupt archive refusal, changed-plan refusal, and invalid journal resolution input. Focused native tests `tests.test_backup_recovery`, `tests.test_operation_journal`, and `tests.test_management_service` passed **33/33**; Python compilation, JSON parsing, and `git diff --check` passed.
- No target operation was synthesized or resolved; no backup, desktop, SSH, boot, PRoot, package, or Android state was changed. Other unresolved operation kinds remain unsupported.
- Read-only target checks at 2026-10-17 23:06:33 UTC showed native XFCE still running on `:1`, Debian present but ownership unverified and guest not entered, zero unresolved journal records, and Doctor overall `pass` (14 pass, 14 info, no warnings/errors). Loopback SSH banner responded but listener ownership remains unverified; GUI visibility remains unknown. Structured snapshot: [post-suite read-only state](2026-10-18-post-suite-readonly-state.json).
- The final full native Termux `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` run passed **170/170** in 33.281 seconds. It used isolated fixtures and made no device changes.

### 2026-10-18 interrupted profile restore recovery

- Generic `recovery.resolve` now handles interrupted `recovery.restore.apply` and `recovery.restore.rollback` operations. Preview validates the journal intent, archive integrity, fixed profile path, current profile mode/owner, and—when current state is not the requested archive target—the operation-linked pre-restore snapshot. It resolves complete only when the archive target matches, failed only when the exact pre-restore state matches, and otherwise leaves the journal unresolved.
- A completed rollback that compensates a `needs_recovery` parent updates the child and parent journal records under the journal lock. The preview lists both journal paths when both records will change. Profile and archive files are always inspection-only; recovery never reapplies/undoes restore content.
- Fixtures cover completed restore, unapplied restore, nested rollback parent reconciliation, ambiguous outcome, corrupt archive, unsafe profile mode, stale recovery preview, and response schema keys. Focused `tests.test_restore_recovery`, `tests.test_backup_recovery`, and `tests.test_operation_journal` passed **21/21**; the full native Termux suite passed **170/170** in 33.281 seconds. Compilation, schema parsing, and `git diff --check` passed. The fixture-only run made no device changes.
- No target restore journal existed; no profile, backup, desktop, service, boot, PRoot, or Android state was changed.
- Post-suite read-only snapshot captured at 2026-10-17 23:14:20 UTC: Doctor `pass` (14 pass / 14 info / 0 warning / 0 error), zero unresolved operations, desktop session recorded running on `:1`, managed SSH service running with loopback banner and ownership unverified, Debian installed with guest ownership unverified. GUI visibility was not observed. See [post-suite P3 state](2026-10-18-p3-recovery-post-suite-state.json).
- Follow-up read-only profile checks at 2026-10-17 23:17:41 UTC show Termux:Boot app and startup directory present, but Android startup policy is `unknown` and the `termux-boot` command is unavailable. Ternuxx boot profile remains default `cli-only`; the PRoot boot preview is correctly blocked because its ownership-aware adapter does not exist. Debian remains inventory-only (`ownership=unverified`, guest not entered). These findings leave cold-boot and PRoot handoff gates open; no profile was enabled and no boot or guest files were touched. The exact API responses are preserved in the same [read-only state snapshot](2026-10-18-p3-recovery-post-suite-state.json).


### 2026-10-18 recovery-kind coverage and documentation audit

- A source audit found that `docs/OPERATIONS.md` still described only restore rollback as implemented, even though the current dispatcher supports operation-specific recovery for every current journal kind. Updated the operating contract and recovery command notes to distinguish `recovery resolve` from the narrower compensating `recovery rollback`; generic task resume remains unavailable.
- Exposed the journal's canonical `JOURNAL_KINDS` set and added `SUPPORTED_KINDS` for operation recovery. A regression test now requires these sets to match so future journal operations cannot silently ship without an explicit recovery route (or an explicit policy change).
- Focused journal/service/boot/desktop/backup/restore recovery tests passed **40/40** in 1.622 seconds. Full native Termux suite passed **172/172** in 32.455 seconds after adding the PRoot inventory response contract. Test fixtures only; no target state changed.
- `git diff --check`, `compileall`, schema/phase-state JSON parsing, CLI help, and repo-knowledge verification (`0 findings`) passed after documentation and source changes.


### 2026-10-18 PRoot inventory response contract

- Added a strict JSON Schema for the `proot status` inventory response. It fixes the supported status vocabulary and required fields while making the key safety claims (`ownership=unverified`, `guest_entered=false`, `read_only=true`) explicit; malformed or unavailable command outcomes remain distinguishable.
- Added fixture coverage across absent manager, empty inventory, installed Debian, and timeout outcomes. Focused PRoot/management tests passed **22/22** in 0.137 seconds. This test does not enter a guest or inspect Ternux state.
- At the PRoot inventory-schema milestone, the full native Termux suite passed **172/172** in 32.455 seconds. The later boot-schema milestone below records the then-current suite result.
- Post-test native read-only snapshot at 2026-10-17 23:24:01 UTC: Doctor `pass` (14 pass / 14 info / 0 warning / 0 error), unresolved operations 0, boot profile `cli-only`, Debian inventory present with ownership unverified. No guest entry or device mutation. See [captured state](2026-10-18-p3-recovery-post-suite-state.json).


### 2026-10-18 Boot diagnostic and profile response contracts

- Added strict schemas for read-only Termux:Boot capability diagnostics and boot-profile status/preview. The schemas encode unknown-versus-absent distinctions, exact safety flags, and the four supported profile names.
- Added fixture checks across boot app states and every boot profile preview, including the blocked PRoot/hybrid cases. Focused runtime/boot-profile tests passed **20/20** in 0.213 seconds. No Termux:Boot files or settings were changed.
- Full native Termux suite after adding both boot schemas passed **174/174** in 32.778 seconds. Compileall, shell syntax, all schema JSON parsing, phase-doc refresh, CLI help, diff check, and repo-knowledge verification (`0 findings`) passed.


### 2026-10-18 Wake Lock boot identity certainty

- Wake Lock status previously reported `boot_id_matches_state=true` when either boot ID was unavailable. Replaced that overconfident boolean with schema-backed `boot_id_relation` (`match`, `different`, or `unknown`); stale leases are classified only when both IDs are present and differ.
- Regression fixtures cover unavailable, matching, and changed boot IDs. Status remains read-only and does not invoke platform lock commands. A strict status schema covers output keys and the match/different/unknown vocabulary. The original tri-state focused run passed **7/7**; the full native Termux suite then passed **176/176** in 32.381 seconds before response-schema coverage was added. Fixtures use temporary state only.
- `compileall`, shell syntax, schema JSON parsing, `git diff --check`, phase-doc refresh, and repo-knowledge verification completed after the change.
- Follow-up schema coverage exercises all three boot-ID relations against the strict response contract. Wake Lock tests passed **8/8**; the full native Termux suite passed **177/177** in 32.257 seconds. Fixture runs use temporary state only; no device or package mutation occurred.


### 2026-10-18 post-reboot native read-only state refresh

- Captured a same-session read-only snapshot at 2026-10-18 05:37 +06 (`2026-10-17T23:37:33Z`). Doctor returned `pass` (14 pass / 14 info / 0 warning / 0 error); the native `:1` session was running with supervisor/X11/XFCE recorded live. GUI visibility is not inferred by the CLI; the earlier owner observation remains separate evidence.
- Debian remains listed but PRoot ownership is `unverified` and `guest_entered=false`. Termux:Boot app and directory are present, but startup policy remains `unknown`; no profile was enabled. Recovery has zero records/unresolved actions and backups are empty.
- The managed Runit `ternuxx-sshd` unit and checked-out definition are reported running/verified; config syntax is valid and a loopback SSH banner was received on port 8023. `/proc/net/tcp*` was unavailable in the initial snapshot, so listener inventory was unavailable and daemon correlation was `unknown`. No listener ownership is inferred. This does not prove external reachability or listener ownership.
- Structured fields and the no-mutation scope are preserved in [live P3 state snapshot](2026-10-18-live-p3-state.json). No package, desktop, service, boot, backup, or PRoot mutation occurred during this refresh.


### 2026-10-18 SSH listener ownership correlation

- The read-only SSH diagnostic now parses the exact fixed Runit unit PID, snapshots visible `/proc` PID/parent/start-time identities without reading command arguments, and correlates a descendant `sshd`/`sshd-session` socket FD inode with a listener inode/address/port from `/proc/net/tcp*` and the service's effective configured endpoints. It reports `verified` only on an exact tree+inode+endpoint match, `not_verified` only after a complete negative observation, `unknown` when procfs is incomplete, and `not_performed` when the fixed service is stopped. The response schema now constrains that vocabulary and distinguishes procfs permission denial from absent/unavailable listener tables.
- Fixtures verify exact positive correlation and fail-closed behavior for missing process identity or listener data; existing tests retain the rule that a global SSH banner alone never establishes process ownership. Focused SSH/procfs/Wake Lock tests passed **16/16** after permission-state coverage; the full native Termux repository suite passed **179/179** in 32.943 seconds after updating the CLI contract fixture.
- On the live target, the updated diagnostic still reports Runit running and a loopback SSH banner on 8023, but `/proc/net/tcp*` returned permission denied. The diagnostic now reports `permission_denied`; its correlation result is `unknown`; the code does not infer ownership from reachability. See [live correlation check](2026-10-18-p3-service-owner-correlation.json).


### 2026-10-18 live boot-profile gate revalidation

- Native read-only Termux:Boot check reports the app and startup directory present, Android startup policy unknown, and no `termux-boot` command. The configured profile remains default `cli-only`.
- `proot` preview stays blocked because the Ternux Debian ownership-aware adapter is absent; `hybrid` stays blocked because native XFCE workload routing is absent. `cli-only` preview is ready at command-prerequisite scope only. Every preview reports read-only and unchanged boot files/PRoot state; no enable/apply ran.
- Structured results are in [boot-profile gate snapshot](2026-10-18-p3-boot-profile-gate.json). This keeps cold-boot and guest ownership gates open rather than treating app presence or an installed distro as qualification.


### 2026-10-18 Android-shell listener-bind cross-check

- A filtered read-only ADB-shell `/system/bin/ss -ltnp` query showed port 8022 listening on `0.0.0.0` and wildcard `*`, while 8023 was bound to `127.0.0.1`. The command reported netlink permission denial and emitted no process/user attribution; Ternuxx's Termux-side `/proc/net/tcp*` remains permission-denied.
- This establishes observed bind addresses only. It does not identify which app/service owns 8022, prove remote reachability, or authorize changing/stopping any listener. Both listener owners remain unknown; no service or device state was changed. See [Android-shell listener-bind evidence](2026-10-18-p3-android-listener-bind-observation.json).


### 2026-10-18 native SSH wildcard-bind Doctor finding

- SSH diagnostics now classify the effective native SSH `ListenAddress` scope separately from the managed Ternuxx Runit service. The target's native config is `wildcard` on port 8022 with password authentication enabled; the managed `ternuxx-sshd` config remains loopback-only on port 8023.
- Doctor now emits `NTX-SSH-001` warning for wildcard native binds, including the authentication mode and explicit `process owner and external reachability=unknown` limitation. The live target returned overall `warning` (14 pass / 14 info / 1 warning / 0 error). This is an observation, not a configuration change or a claim of Internet reachability.
- The ADB socket snapshot independently observed a wildcard listener on 8022 but could not attribute it to a process; see [bind observation](2026-10-18-p3-android-listener-bind-observation.json). The current Doctor/diagnostic response is recorded in [SSH bind policy evidence](2026-10-18-p3-ssh-bind-policy-doctor.json).
- Focused SSH/Doctor fixtures cover wildcard, non-loopback, loopback-only, and unknown policy classes, plus the warning's non-claim of external reachability. The full native Termux suite passed **181/181** in 32.382 seconds after this implementation.


### 2026-10-18 reboot observer managed-service evidence

- Fixed `lib/reboot_recovery.py` so `native_service_health` is derived from the fixed managed Runit service evidence, not the unrelated generic `sshd` process and package-default configuration alone. The observer now records managed Runit status, fixed definition identity, managed config syntax, loopback SSH banner result, and listener-to-daemon correlation. Unknown values remain explicit.
- Managed service health is `ready_unqualified` only when Runit reports running, definition identity is verified, managed config syntax is valid, and the loopback endpoint returns an SSH banner. Known stopped/mismatched/failed evidence is `degraded`; incomplete evidence is `unknown`. Authenticated SSH remains `not_tested`, and successful banner evidence does not verify listener PID ownership.
- The checkpoint schema adds optional enum-constrained fields while preserving readability of existing schema-v1 checkpoints. Runtime checkpoint parsing validates these fields when present.
- Focused `tests.test_reboot_recovery` passed 10/10. Full `bash scripts/repo_test.sh` passed 183/183 in 33.022 seconds. The fixture suite establishes source behavior only; no boot script, profile, service, desktop, package, or PRoot state was changed, and physical cold-boot qualification remains open. Detailed run record: [reboot observer test evidence](2026-10-18-p3-reboot-observer-managed-service-tests.json).


### 2026-10-18 current read-only P3 gate snapshot

- Re-ran `doctor --json`, desktop `status --json`, `ssh inspect --json`, `proot status --json`, `boot status --json`, `recovery status --json`, `reboot status --json`, and `wakelock status --json` from native Termux. All outputs were recorded in [the structured snapshot](2026-10-18-p3-current-readonly-gate-snapshot.json); these commands did not apply a service, desktop, boot, package, Android setting, or PRoot operation.
- Doctor returned warning with 14 pass / 14 info / 1 warning / 0 errors. The sole warning is `NTX-SSH-001`: native SSH config is wildcard-bound and password authentication is enabled; owner and external reachability are unknown. Managed SSH remains Runit `running`, definition/config verified, and loopback banner observed on 8023; listener-to-daemon correlation remains unknown.
- Desktop status is running on `:1`; GUI visibility remains `unknown` to the CLI and audio owner is external. PRoot inventory reports Debian installed, ownership unverified, and guest not entered. Termux:Boot app/directory are present, two regular scripts are listed, startup policy is unknown, and the `termux-boot` command is unavailable.
- Recovery journal has zero unresolved operations. Reboot status still lists RB03 `boot_observed`, RB02 `inconclusive`, and RB01 `prepared`; all remain `NOT_READY`, with automatic resume disabled. Wake Lock coordinator reports one registered native SSH owner and boot ID match; Android platform lock state remains unknown and the query invoked no acquire/release command.
- P2 remains complete under its dated completion evidence. Its original pre-consent XFCE package preview gap remains historical and cannot be reconstructed; current preview and installed 77/77 package versions are separately corroborated. No P2 gate was reopened or represented as retroactively captured.


### 2026-10-18 boot-profile preview recheck

- Read-only `boot profile status` confirms the selected configuration remains the default `cli-only`. The native profile preview is ready at the command-prerequisite level and explicitly leaves Android activity visibility unknown. PRoot preview is blocked by the missing ownership-aware adapter; hybrid preview is blocked by the missing native-plus-workload-routing adapter. All previews report no script installation or boot-config changes.
- No profile was selected or enabled. Full outputs and limitations are in [the preview recheck evidence](2026-10-18-p3-boot-profile-preview-recheck.json). These are preview results, not boot-delivery or GUI-startup qualification.


### 2026-10-18 P3 exit-gate audit

- Mapped all seven roadmap exit criteria to current source, named fixtures, and the current read-only native snapshot. Source/fixture gates are separated from device-only qualification; P3 remains in progress and P4 remains gated on ownership/handoff. See [P3 exit-gate audit](2026-10-18-p3-exit-gate-audit.md).


### 2026-10-18 reboot checkpoint compatibility regression

- Added fixture coverage for the additive schema-v1 checkpoint contract: old observations without managed-service fields remain readable; malformed enum values are rejected with `RecoveryError` at API and persisted-record boundaries; a degraded managed service includes an explicit error marker.
- Focused reboot recovery suite passed **12/12**. Full native Termux suite passed **185/185** in 32.212 seconds. Evidence: [checkpoint compatibility test record](2026-10-18-p3-reboot-checkpoint-compatibility-tests.json). No device, package, boot, desktop, service, or PRoot state changed.


### 2026-10-18 explicit Shizuku capability disclosure

- Doctor now reports Android Shizuku package presence separately from Ternuxx provider support. Its finding says the Ternuxx provider is not implemented and upstream/custom release identity, service, and permission remain unknown; it also states no Ternuxx operation enables ADB-over-Wi-Fi.
- `tests.test_doctor_report` passed **19/19**; full repository suite passed **185/185** in 32.610 seconds. A fresh read-only target Doctor run returned the existing SSH policy warning (14 pass / 14 info / 1 warning / 0 error) and the updated Shizuku info finding. Detailed record: [Shizuku capability evidence](2026-10-18-p3-shizuku-capability-tests.json). The Shizuku gate remains partial because signature/build identity and service permission are not verified.


### 2026-10-18 off-home remote-access policy contract

- Implemented an offline validator and non-applying preview for the owner-approved private-access policy. Default mode is disabled; public ingress is rejected. A requested private transport stays unavailable until an adapter and owner-selected route/client authorization are verified. Preview does not read/write files, resolve credentials, inspect or contact a network, or change services, and it omits client/capability/credential references from output.
- The config schema is version 2: opaque credential reference IDs require the `credential_ref_...` prefix. This remains a preview-only integration: no VPN/tunnel setup, config persistence, router change, or device enablement is implemented. The ADR records these boundaries.
- Focused policy tests were 7/7 and the earlier full suite was 192/192 in 33.319 seconds; after CLI/API integration, focused policy/management tests passed 27/27, CLI help passed, and the full repository suite passed 194/194 in 32.778 seconds. Full evidence and exact runtime boundaries: [remote-access policy tests](2026-10-18-p3-private-remote-policy-tests.json). Off-home access remains unavailable pending transport selection, adapter security review, and explicitly authorized device/network qualification.


### 2026-10-18 remote policy shared-management and CLI preview

- Added the allowlisted local management operation `remote.access.preview` and `ternuxx remote access preview`. A supplied JSON policy is accepted only through explicit `--policy-stdin`; malformed input is rejected. The response schema is version 1, separate from desired-policy config schema version 2.
- Live CLI check returned `disabled` by default and `unavailable` for a private transport policy. Both report `remote_access_active=false`, public ingress false, and no emitted credential/client reference values. The implementation neither resolves those references nor contacts a network or changes a service.
- Focused policy + management tests passed **27/27**; CLI help contract passed; response schema JSON parsed; full `bash scripts/repo_test.sh` passed **194/194** in **32.778 seconds**. See [structured remote-access evidence](2026-10-18-p3-private-remote-policy-tests.json).
- P3 remains open: no provider was selected, no transport adapter exists, and no off-home device/network qualification was performed.

- Follow-up response-contract check: `python -m unittest tests.test_remote_access_policy tests.test_management_service -v` passed **28/28**, checking both preview modes against the version-1 response schema shape and fixed safety fields.


### 2026-10-18 00:35 UTC current P3 gate recheck

- Re-ran read-only Doctor, desktop status, managed SSH inspection, PRoot inventory, Termux:Boot status, recovery status, reboot status, and Wake Lock status from native Termux. Full structured summary: [fresh P3 gate recheck](2026-10-18-p3-current-readonly-gate-recheck.json).
- Doctor remains warning (14 pass / 14 info / 1 warning / 0 errors) for the native wildcard SSH config on port 8022 with password authentication enabled; process owner and external reachability remain unknown. Managed SSH on loopback 8023 is running and answers with a protocol banner; listener ownership remains unknown because procfs denied the socket table.
- Native desktop `:1` is running; GUI visibility is unknown to CLI. Debian PRoot is installed but ownership is unverified and no guest was entered. Termux:Boot app/directory are present but delivery policy is unknown. Recovery journal has zero unresolved operations. RB03 remains `boot_observed`/`NOT_READY`; RB02 `inconclusive`/`NOT_READY`; RB01 `prepared`/`NOT_READY`; automatic resume remains false.
- These were read-only checks; no desktop/service/package/boot/PRoot state was changed.


### 2026-10-18 bounded Ternux guest diagnostic handoff

- Added `proot.guest.verify` to the native allowlisted management service and `ternuxx proot verify`. It requires an explicit Debian guest user, display, and backend; confirms the installed distro; accepts only the self-identifying Ternux guest companion; and invokes only its version/status commands as argv, without a shell string. Zink/Turnip, VirGL, display, and source-documented PulseAudio endpoint are explicit; shader caching is disabled for the probe. `proot status` remains inventory-only.
- Source re-pin: Ternux `main` was rechecked at `9fda63162426f77ee575b5f6729d8799a30f51b7`. Its guest companion exposes read-only `status`/`--version`; host `start`/`stop` are explicitly Termux-host operations and are not invoked.
- Live verification at 00:41:44 UTC identified guest companion 1.4.0; on requested/observed display `:1`, X11 was reachable and renderer was `zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))`. Audio at `tcp:127.0.0.1:4713` was unavailable, so result is `partial`. Without shared `/tmp`, the guest could not reach X11; adding the Ternux-documented shared-temp route made X11 reachable. Full record: [bounded guest handoff evidence](2026-10-18-p3-ternux-guest-handoff.json).
- The `:1` native desktop remained running after the probe. No guest write command, package change, host lifecycle, or service action was invoked. This does not establish Ternux profile ownership, active `:0` configuration, agent workload execution, or P3/P4 completion.
- Validation of this integration: focused PRoot/management tests passed **30/30**; CLI help contract passed; Python compilation, shell syntax, JSON schema/evidence parsing, repo-knowledge verification (**0 findings**), and `git diff --check` passed. Full `bash scripts/repo_test.sh` passed **201/201** in **33.000 seconds**. These are repository fixture tests; they do not change the live device gate result above.

### 2026-10-18 guest PulseAudio reachability repeatability

- Rechecked the existing TCP bridge without changing its module or starting/stopping audio services. The native server reports `OpenSL_ES_sink`; its read-only module inventory showed `module-native-protocol-tcp` restricted to loopback `127.0.0.1:4713` with loopback ACL and anonymous auth.
- The first timed verification plus five subsequent guest-verifier invocations reported PulseAudio unavailable while X11 and Zink/Turnip remained reachable. A later native/guest loopback and `pactl info` check connected, then **10/10** sequential `ternuxx proot verify` runs reported `complete` with audio, X11, and Zink/Turnip reachable. The same native `:1` desktop remained running.
- Follow-up: after the 10/10 pass window, a one-second zero-valued PCM client attempt failed with `Connection refused` before PulseAudio accepted the stream. At 00:55:01–00:55:03 UTC, native and guest loopback probes, guest `pactl info`, and `ternuxx proot verify` passed again. Native `ternux status` simultaneously reported PulseAudio stopped while native `pactl info` identified the PulseAudio server and OpenSL sink. The reason for this discrepancy/flapping is unknown; no audible signal was accepted. No PulseAudio configuration, service, package, desktop, or guest lifecycle was changed. Record: [guest audio repeatability evidence](2026-10-18-p3-ternux-audio-repeatability.json).


### 2026-10-18 native/guest Ternux status correlation

- Extended `proot.guest.verify` to query only native `ternux --json status` and return an allowlisted, schema-validated status summary alongside the selected guest checks. It reports identity/ownership as unverified and does not use Ternux's host `pulseaudio` process field as endpoint health. Invalid/malformed output remains `unknown`; no shell command is accepted.
- The pinned Ternux status implementation uses `pgrep -x pulseaudio` for its PulseAudio field, so that field indicates matching process-name presence rather than `pactl` or TCP endpoint connectivity ([pinned Ternux source](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/lib/desktop.sh#L611-L634)). Live native `ternux --json status` at 01:03:37 UTC reported running/X11 yes/PulseAudio stopped; the same Ternuxx guest verification reported X11 and Zink/Turnip reachable but guest audio unavailable. This keeps the mismatch visible without claiming ownership or changing Ternux.
- Detailed correlation was appended to [guest audio repeatability evidence](2026-10-18-p3-ternux-audio-repeatability.json). The PRoot diagnostics subset passed **11/11** before API integration.

- Final validation for this change: focused PRoot/management tests most recently passed **34/34**; Python compilation, schema/evidence JSON parsing, `python3 tools/phase_docs.py refresh`, repo-knowledge verification (**0 findings**), and `git diff --check` passed. Full `bash scripts/repo_test.sh` passed **205/205** in **32.468 seconds**. The live Ternuxx report at 01:03:35–37 UTC correctly returned `partial`, showing native PulseAudio process state `stopped`, guest audio unavailable, X11 reachable, and Zink/Turnip selected. No lifecycle, service, package, or rootfs mutation occurred.

- P4 profile-discovery follow-up: safe Ternux `info`, `backend show`, and filtered `state --json` observations report configured backend `zink`, Vulkan yes, but host renderer unknown. Ternuxx now includes the fixed backend-show response separately from the actual guest renderer; at 01:08:30 UTC the host configured backend was `zink`, guest `:1` selected Zink/Turnip, and guest audio remained unavailable. The inspected structured state output did not identify the configured Debian user/distro, so profile ownership remains unverified. No raw state directory/path or installation history was copied into evidence.


### 2026-10-18 P3 continuation regression check

- Recorded at 2026-10-18 01:12:27 UTC, `bash scripts/repo_test.sh` had passed **205/205** in **32.576 seconds**. `python3 -m tools.repo_knowledge verify` reported **0 findings**, `git diff --check` passed, and `python3 tools/phase_docs.py refresh` regenerated the phase status successfully. Structured record: [continuation test evidence](2026-10-18-p3-continuation-tests.json).
- This was a repository-only check; no live device, package, service, desktop, boot profile, or PRoot operation was run. It does not close any device-only P3/P4 gate.


### 2026-10-18 fresh native P3 gate recheck

- At 01:14:03 UTC, the bounded native read-only gate commands reported Doctor warning (14 pass / 14 info / 1 warning / 0 errors); desktop `:1` and its X11/XFCE processes running with GUI visibility unknown; managed loopback SSH 8023 running with banner reachable but listener ownership unknown; Debian installed with Ternux ownership unverified; Termux:Boot policy unknown; zero unresolved recovery records; reboot checkpoints still `NOT_READY` with automatic resume false; and the registered Wake Lock coordinator owner is native SSH while Android lock state remains unknown.
- All eight commands were read-only; no service, desktop, package, profile, reboot, guest, or Wake Lock operation was applied. Allowlisted summaries: [latest P3 gate snapshot](2026-10-18-p3-current-readonly-gate-latest.json).


### 2026-10-18 latest Ternux guest diagnostic

- At 01:16:27 UTC, the bounded read-only `ternuxx proot verify` returned `partial`: Debian guest X11 on `:1` was reachable and selected `zink Vulkan 1.4 (Adreno TM 825; MESA_TURNIP)`; the guest PulseAudio control check was unavailable. Native Ternux status reported X11 yes and PulseAudio process status stopped; configured backend was Zink, host renderer remained unknown, and PRoot/profile ownership remained unverified.
- The guest diagnostic did not run a sound stream and changed no service, package, desktop, guest file, or lifecycle state. This fresh failure is appended to the existing time-series [audio and renderer evidence](2026-10-18-p3-ternux-audio-repeatability.json); it preserves the earlier 10/10 passing control window and later failures.


- Immediate cross-layer follow-up: native `pactl info` succeeded (`pulseaudio`, `OpenSL_ES_sink`) and native TCP `127.0.0.1:4713` connected at 01:16:53 UTC. A subsequent bounded guest verifier returned `complete` by 01:17:08 UTC with guest audio/X11 reachable and Zink/Turnip selected, while native Ternux process-status still said PulseAudio stopped. This is control reachability only, not audible playback or stable operation; the time series is preserved in [audio/renderer evidence](2026-10-18-p3-ternux-audio-repeatability.json). No audio stream or service action ran.


### 2026-10-18 three-run audio/control repeatability sample

- Three sequential read-only guest status checks at 01:18:02–01:18:09 UTC returned **1 partial / 2 complete**. All three reported X11 reachable and Zink/Turnip; native PulseAudio `pactl info` and loopback TCP checks succeeded immediately after each guest invocation, while native Ternux's process-only PulseAudio field said stopped for all three.
- This supports an inference that the intermittent result lies on the guest/control path, but endpoint availability was not sampled concurrently with the failed guest call, so the cause is not proven. No sound stream ran; audible playback and stable operation remain unverified. Full per-run allowlisted data is appended to [audio repeatability evidence](2026-10-18-p3-ternux-audio-repeatability.json).


### 2026-10-18 concurrent audio-bridge control check

- Three sequential read-only guest verifier calls at 01:19:25–01:19:32 UTC all returned complete with guest audio, X11, and Zink/Turnip reachable. During the guest calls, native loopback TCP succeeded on **15/15** samples; `pactl info` and loopback checks also succeeded before and after every call. Native Ternux process-only PulseAudio status still reported stopped.
- This verifies a short control-connectivity window and isolates the existing process-status mismatch; it does not erase earlier failures or establish long-term reliability/audible output. No sound stream, service action, package change, or guest write was performed. Full timing and per-run evidence: [concurrent audio sample](2026-10-18-p3-ternux-audio-repeatability.json).


### 2026-10-18 typed native PulseAudio endpoint status

- `proot verify` now reports native `pactl info` as a separate bounded, read-only field, distinct from Ternux's process-name PulseAudio status and the guest audio check. It includes only an allow-listed server name/default sink and fails closed to unavailable/unknown. The strict response schema and fixture coverage were updated.
- Focused PRoot/management tests passed **36/36**; full native Termux suite passed **207/207** in **32.713 seconds**. Live check at 01:22:36 UTC returned `complete`: native endpoint available (`pulseaudio`, `OpenSL_ES_sink`), guest audio/X11 reachable, and Zink/Turnip selected; Ternux process-only PulseAudio still said `stopped`. Profile ownership remained unverified. No sound stream or service/package/guest mutation occurred. Full record: [typed pactl endpoint evidence](2026-10-18-p3-pactl-endpoint-status.json).
- This improves state diagnosis but does not resolve prior audio intermittency, prove audible guest playback, or close P3/P4 ownership and workload gates.


### Typed native PulseAudio endpoint status and regression check (2026-10-18)

- `proot verify` now reports a read-only typed native `pactl info` endpoint summary separately from Ternux process status. The allowlisted probe is bounded, captures only server name/default sink, and leaves unavailable or unrecognized responses explicit. This prevents `pulseaudio=stopped` from being conflated with actual native endpoint reachability.
- Schema, docs, and fixture coverage were added. Full suite passed 207/207 in 33.461 seconds; `python3 -m compileall -q lib tests`, CLI help, repository knowledge verification (0 findings), phase-doc refresh, and `git diff --check` passed.
- Latest live guest verification at 01:22:36 UTC was complete with native endpoint available, guest audio/X11 reachable, and Zink/Turnip renderer present. This remains endpoint/control and renderer observation only: profile ownership is unverified, no audible playback was tested, and cross-time stability is not established. P3 remains in progress.


### Fresh read-only Doctor state (2026-10-18 01:34 UTC)

- `./ternuxx --json doctor` returned a valid JSON report with `read_only=true`, `overall=warning`, 14 pass / 14 info / 1 warning / 0 errors (exit 1 because of the warning). Evidence stores a redacted subset and omits transient PIDs.
- Native desktop record remains running on `:1`; SSH policy is wildcard bind with password authentication enabled, while listener owner and external reachability remain unknown. Runit service status and a loopback SSH banner were observed; neither proves listener ownership or off-device reachability. Debian inventory is present with ownership unverified. Shizuku app is present, but Ternuxx provider/build identity/service/permission remain unknown.
- No configuration, package, service, desktop, or PRoot lifecycle change was made. The only Doctor warning remains the SSH bind/auth policy finding; assess it before enabling off-home access. See [structured read-only Doctor recheck](2026-10-18-p3-current-doctor-recheck.json).


### SSH listener ownership recheck (2026-10-18 01:36 UTC)

- Read-only `ternuxx ssh inspect` distinguished the general native SSH configuration on `0.0.0.0:8022` and `[::]:8022` (wildcard; password auth enabled) from managed Runit service `ternuxx-sshd` on `127.0.0.1:8023` (loopback-only config; service definition identity verified; banner probe passed).
- Listener-to-daemon correlation remains unknown because procfs TCP listener tables returned permission denied; `netstat` lacks AF_INET support and `ss` is absent. Actual socket owner and external reachability remain unknown. No package was installed to add tools; no listener/config/service action ran. See [SSH ownership evidence](2026-10-18-p3-ssh-listener-ownership-recheck.json).

- Related regression check: `python3 -m unittest tests.test_ssh_diagnostics -v` passed **9/9**. Fixtures cover procfs permission-denied distinction, exact service-definition identity, process-tree/socket-inode ownership correlation, and loopback-only probe scope.

### Local ADB server status in Doctor (2026-10-18 07:01 UTC)

- Added `NTX-ADB-001`, a bounded native-only `host:version` query to fixed loopback `127.0.0.1:5037`. It never invokes ADB or asks for device/authorization data. Focused tests passed 26/26; the complete repository suite passed 225/225.
- Native Doctor returned protocol `0x0029`; local server responsiveness is confirmed, while bind scope, device transport/authorization, and Shizuku readiness remain unknown. Desktop `:1` remained recorded running and no lifecycle/package/settings action was performed. P3 gate 6 stays partial/open. See [implementation/device evidence](2026-10-18-p3-adb-doctor-integration-0701.json).
- The user pointed to the existing ADT report as the authoritative Shizuku custom-fork analysis. Ternuxx links that report rather than duplicating its forensic content; the ADT report's dated dependency conclusions are treated as a snapshot, not current runtime proof.

### Management TCP authorization policy preparation

- Added one explicit capability scope for each current management-service operation. Unknown operations, wildcard grants, malformed grants, and read-only-to-mutation escalation deny by default. Contract tests enforce exact parity with the service allowlist so a newly added operation cannot silently become transport-exposable.
- This is not authentication, session bootstrap, or HTTP/TCP transport. The existing service continues to reject non-CLI callers; no listener, network access, or device service action was enabled. See [management API contract](../architecture/MANAGEMENT-API.md) and [ADR-0014](../architecture/decisions/ADR-0014-proot-adb-and-management-tcp.md).
- Focused scope-policy tests passed 4/4, followed by full suite 229/229 in 145.148 seconds. See [structured evidence](2026-10-18-p3-management-authorization-policy.json).
- A follow-up auth/session slice adds a single-use bootstrap, exact requested-scope narrowing, in-memory digest-only credentials, idle and absolute expiry, mutation CSRF, revocation, and serialized bootstrap/session state. This is not connected to a listener or CLI dispatch. Focused and full-suite evidence: [management session authority](2026-10-18-p3-management-sessions.json).
- A transport-independent request guard now checks exact loopback Host/Origin, GET/POST, JSON POST, body-size limits, and a thread-safe global rate bucket. Focused authorization/session/request tests passed 19/19. This guard does not bind a socket or enforce concurrency/deadlines, response headers, audit, or operation dispatch; it is not device transport evidence.
- Final full repository suite after the request-policy slice passed 244/244 in 145.904 seconds. See [structured transport guard evidence](2026-10-18-p3-management-transport-guards.json).
- The first HTTP adapter layer routes session bootstrap/revoke and typed operations through the shared service after request, bearer scope, and CSRF checks. A private durable request store now records at-most-once mutation markers and an allowlisted audit trail without bodies, arguments, tokens, or responses. Mutating routes remain disabled by default and require explicit opt-in plus this durable store. An interrupted request is marked outcome-unknown and is never automatically re-dispatched. Session credentials remain memory-only.
- Focused management authorization/session/policy/adapter/store tests passed 34/34 after the durable-store addition. Full suite result is recorded in [management request-store evidence](2026-10-18-p3-management-request-store.json). The in-process contract tests do not open a socket or qualify a device listener; no listener or device mutation occurred.

## 2026-10-18 management TCP source gate

- Added `lib/management_http_server.py` as an explicitly constructed and started IPv4 loopback listener. It rejects any bind other than `127.0.0.1`, limits workers to 1–16 (default 4), caps request headers/body, applies a total connection deadline, returns 503 on worker exhaustion, suppresses request logging, and waits for active handlers during graceful shutdown.
- Deadline expiry closes the client socket; it cannot interrupt a typed service call already executing. The durable idempotency marker keeps the operation from being automatically replayed if the client reconnects. Mutation routes remain disabled unless explicitly enabled with the durable request store.
- The listener test uses temporary ephemeral loopback ports only. Focused server tests passed 8/8, 100 immediate start/close cycles passed, and the latest full repo suite passed 268/268 in 77.675 seconds. Added checks reject malformed HTTP without echoing parser data and reject oversized decimal Content-Length without integer conversion. The durable store now rejects NaN and unreasonable timestamps. No persistent service, boot integration, browser flow, or remote access was enabled. Device fixed-port loopback, bootstrap-secret provisioning, operation-specific execution deadlines, and launcher/recovery integration remain open. See [HTTP server evidence](2026-10-18-p3-management-http-server.json).

## 2026-10-18 foreground runtime integration

- Added `ternuxx management http serve [--port 8765]`. It requires native Termux environment markers and an interactive TTY; it generates a per-run bootstrap secret in memory, displays it on stderr only, and does not write it to a file or environment. The default reviewed grants are read-only and a module invariant refuses any overlap with mutation capabilities.
- The command binds only `127.0.0.1` and stays in the foreground until Ctrl-C/SIGTERM. No automatic Runit/Termux:Boot start or persistent listener was enabled. The service flow has focused ephemeral loopback tests only; device fixed-port, browser onboarding, restart/session lifecycle, and off-home transport remain open.
- Runtime tests passed 4/4; combined focused management/security tests passed 47/47; CLI help path passed; full repository suite passed 272/272 in 101.661 seconds. Evidence: [foreground runtime](2026-10-18-p3-management-http-runtime.json).


### Management listener readiness (2026-10-18 08:09 UTC)

- Added `GET /ready` alongside adapter liveness at `GET /health`. Readiness is tied to the owning loopback listener thread, uses the same Host/Origin/rate checks, returns 503 when the probe is false, and is cleared before shutdown drain. During drain the listener rejects new connections. This does not claim GUI, guest, SSH, or workload readiness.
- Focused HTTP runtime/server/adapter tests passed 22/22; the full Native Termux suite passed 273/273 in 41.756 seconds. Only ephemeral test listeners were opened and closed; no persistent listener, service-manager integration, or off-home route was enabled. See [readiness evidence](2026-10-18-p3-management-readiness-0809.json). P3 remains active.


## Native repository suite recheck — 2026-10-18 08:18 UTC

The complete Native Termux fixture suite passed **273/273** in 41.229 seconds. The run did not apply packages or change desktop/service/boot/device/PRoot state. See [structured native test evidence](2026-10-18-p3-native-suite-recheck-0817.json). The separate 08:14 run was executed in Debian PRoot and is classified as PRoot source-fixture evidence only.


## Native Doctor recheck — 2026-10-18 08:19 UTC

Doctor returned `overall=warning`, `read_only=true`, 14 pass / 15 info / 1 warning / 0 errors. The warning remains the separate native SSH configuration with wildcard bind and password authentication; process ownership and external reachability are unknown. ADB responds only to the bounded local `host:version` probe (0x0029); device authorization and Shizuku readiness remain unknown. Debian inventory still does not establish Ternux guest ownership. No service, package, boot, desktop, Android setting, network, or PRoot state was changed. Evidence: [sanitized native Doctor recheck](2026-10-18-p3-native-doctor-recheck-0819.json).


## Existing guest read-only verification — 2026-10-18 08:23 UTC

The native-host `proot verify` command returned `complete` for Debian, display `:1`, requested Zink. X11 and PulseAudio control were reachable; renderer was Zink/Turnip on Adreno 825. The verifier entered the guest for fixed read-only status/renderer checks, with `guest_write_command_invoked=false`; it started/stopped no service or desktop. Ownership, audible playback, visible GUI, and workload routing remain unverified. See [structured verification evidence](2026-10-18-p3-ternux-guest-verify-recheck-0823.json).


## Current recovery-kind coverage correction — 2026-10-18 08:25 UTC

The current summary now reflects the dispatcher and `docs/OPERATIONS.md`: every journal kind declared in `lib/operation_journal.py` has an operation-specific `recovery resolve` path. Compensating `recovery rollback` remains profile-restore-only; generic resume and future unregistered kinds stay unsupported. Native Termux focused recovery regression passed **56/56**. Earlier dated entries describing the then-incomplete recovery surface are retained as history. Evidence: [focused recovery regression](2026-10-18-p3-recovery-focused-recheck-0825.json).

## 2026-10-18T08:29:21Z — Managed 8023 repository suite and next-session routing

- The full `bash scripts/repo_test.sh` suite was run through the loopback managed SSH shell on port 8023 (accessed from the 8022 work shell): **273/273 passed** in 35.700 seconds. This is fixture/source test evidence, not a new hardware or PRoot qualification. No package, desktop/service lifecycle, boot/Android setting, PRoot guest, or separate Ternux repository mutation occurred. Evidence: [2026-10-18-p3-managed-8023-suite-recheck-0829.json](2026-10-18-p3-managed-8023-suite-recheck-0829.json).
- Added durable shell-routing and repo-boundary guidance to `AI_ASSISTANT.md` for the next session. It explicitly says use 8022 for work, 8023 for managed suite runs, verify runtime rather than assuming it, keep credentials out of repo, and do not modify the separate `soobujmiah/ternux` repo.
- P3 remains in progress; this test result does not close its open ownership, workload, boot, listener, or Shizuku gates.


## 2026-10-18 8023 reboot-observer source identity recheck — 08:41 UTC

The installed native observer previously reported `managed_service_definition=unavailable` because its default source path was derived under `$PREFIX`. The resolver now honors `TERNUXX_REPO_ROOT`, uses checkout-relative source when available, and falls back to `$HOME/ternuxx/scripts/termux-services/ternuxx-sshd/run`; the Runit adapter shares that resolver. A private rollback backup was retained before syncing the installed SSH diagnostic module.

Through the authenticated 8023 loopback SSH test shell, installed and checkout `boot-observe --dry-run` both returned `managed_service_status=running`, `managed_service_definition=verified`, valid managed config, and an SSH banner. Listener-to-daemon correlation remains `unknown`. The full managed suite passed **274/274** in 35.028 seconds, including an installed-module-path fixture. Read-only status still reports RB01–RB03 `NOT_READY`; the observed boot ID differs from RB03's saved pre-reboot ID but does not prove Termux:Boot delivery. No actual reboot, boot observer write, service action, desktop action, package operation, Android setting, or PRoot mutation occurred.

See [structured 8023 observer and readiness evidence](2026-10-18-p3-managed-8023-reboot-observer-resolver.json). P3 remains in progress.


## RB04 pre-reboot baseline — 2026-10-18 08:48 UTC

Prepared private checkpoint `TERN-20261018-RB04` at mode 0600; status is `prepared` / `NOT_READY`. Baseline records the existing native XFCE desktop on `:1`, Debian inventory without guest entry, managed 8023 service/config readiness, current 8022 wildcard/password policy, enabled Termux:Boot receiver with delivery still unknown, and Wake Lock ownership limits. The public repo evidence excludes the checkpoint nonce and boot ID. No reboot, service/desktop action, boot-setting change, package operation, or PRoot action occurred.

The CLI has no device reboot operation. The next step is an owner-initiated Android restart; afterward, reconnect on 8023 and collect read-only checks. Do not manually run `boot-observe`, because that would not prove Termux:Boot delivery. Evidence: [RB04 prepared baseline](2026-10-18-p3-reboot-rb04-prepared.json).

## 2026-10-19 Shizuku identity disclosure recheck

Doctor's Shizuku finding now includes the observed package ID alongside versionCode, and labels the `shizuku_server` process result only as a process-name signal. It explicitly keeps upstream/custom provider identity, signer/release identity, permission, and watchdog health unverified. Regression assertions reject the earlier upstream attribution. Native `./tx doctor --json` remains read-only and reports `overall=warning`; the full repository suite passed 346/346 in 75.339 seconds. Evidence: [read-only Shizuku and suite recheck](2026-10-19-p3-doctor-shizuku-identity-recheck.json). No device state or service was changed. P3 remains open for provider ownership and reboot/cold-boot qualification.


## Native boot-profile preview/apply byte parity — 2026-10-19

The supported `cli-only` and `native` boot-profile preview scripts now match the exact managed script bytes, including the trailing newline. Regression tests enforce parity. Focused tests passed 12/12 and the full Native Termux suite via SSH 8022 passed 347/347 in 69.117 seconds. No boot profile was applied; Termux:Boot delivery and cold-boot behavior remain unqualified. See [parity evidence](2026-10-19-native-boot-profile-preview-parity.md).


## Native X11 activity request and fallback fixtures — 2026-10-19

Desktop lifecycle fixtures now cover the fixed Termux:X11 Activity component request, accepted-request visibility limits, and rejected/unavailable manual-open fallback. Focused tests passed 16/16; full Native Termux suite via SSH 8022 passed 350/350 in 71.566 seconds. These are source/fixture checks only; Android UI, boot delivery, and background policy were not exercised. See [evidence](2026-10-19-native-x11-activity-fallback-tests.md).


## Native boot-profile identity diagnostics — 2026-10-19

`tx boot profile status` now verifies only the fixed Ternuxx boot script against the selected profile and reports legacy, missing, mismatch, or unsafe states without repair. The bounded read uses no-follow open and validates owner/mode. Response schema is v2. Focused boot tests passed 14/14, management-service tests passed 24/24, and the full native suite through SSH 8022 passed 352/352 in 71.703 seconds. Live status returned `cli-only`, `match`, and `read_only=true`; no runtime state changed. See [evidence](2026-10-19-native-boot-profile-identity.md). Boot delivery and cold boot remain unqualified.
