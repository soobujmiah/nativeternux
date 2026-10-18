# P2 native desktop lifecycle implementation progress

- Phase: `P2` source-progress snapshot dated 2026-10-17; superseded by the completion record dated 2026-10-18
- Reviewed: 2026-10-17 (historical snapshot)
- Evidence type: historical source-review snapshot; later target lifecycle and exact-preview evidence is recorded below and in the P2 completion record.
- At this snapshot, the device had not yet received the scoped XFCE install; this is historical and is superseded by the dated native-device evidence below.

## Source now present

- `lib/desktop.sh` provides initial `start`, `stop`, `restart`, and `status` command paths.
- `lib/desktop-supervisor.sh` records process start ticks and command markers, waits for the X11 socket, starts XFCE under Ternuxx-owned XDG paths, and limits cleanup to recorded child identities.
- Startup failure cleanup uses SIGTERM only. No broad process matching, SIGKILL, wildcard socket deletion, PulseAudio control, Ternux launcher call, or PRoot rootfs access is intended by these files.
- Session state and logs are kept under the Ternuxx state directory; state directory resolution is required to remain under Termux HOME.
- Start and stop use a Ternuxx session lock to avoid concurrent lifecycle operations.
- `lib/help.sh` now describes the implemented lifecycle and the actual mutation boundaries. The previous text incorrectly called start/stop/install stubs and claimed that no process or package state changed.
- `tests/test_cli_help.sh` checks that public help remains consistent with the lifecycle and installation behavior without invoking either mutating command.
- An isolated Linux process fixture exposed a lock leak: the old EXIT trap referenced a function-local lock variable after that variable had gone out of scope. `lib/desktop.sh` now stores the acquired lock path at module scope and releases that exact directory from the EXIT trap.
- `tests/test_desktop_lifecycle_fixture.py` runs a copied library with a Termux shebang adapted only inside the temporary fixture and mock X11/DBus/XFCE processes. Start, repeated start (same process identities), status, stop, owner-checked stale socket/lock cleanup by the supervisor, and repeated stop passed locally.
- Reproduced the restart lock defect in the same fixture, then verified repeated restart releases the lock and creates a fresh owned session. The mock regression passes; this does not validate Termux process semantics.
- Added `./ternuxx` and `bin/ternuxx` as canonical source-checkout commands while retaining `nativeternux` as a compatibility entry point. Installed aliases/state paths have not been migrated.
- Added native continuity checkpoint and read-only SSH diagnostic source with host-side fixtures. These are management/evidence foundations; neither Termux:Boot nor SSH service changes are implemented.

## Not established

- On 2026-10-17, `python3 -m unittest discover -s tests -v` passed 16 tests; `bash tests/test_cli_help.sh`, Bash syntax checks, Python byte-compilation, JSON syntax parsing, `python3 -m tools.repo_knowledge verify` (0 findings), and strict README bridge check passed. Full JSON Schema validation was not run because a validator is unavailable locally. See [structured evidence](2026-10-17-native-management-slice.json).
- Read-only inspection found the Termux:X11 APK but not native XFCE packages, so no physical-device lifecycle test was run. No package installation or PRoot change was performed. The owner permits X11 testing; this does not include package installation.
- Exact Termux:X11 command-line and process behavior, socket readiness, DBus/XFCE lifetime, startup rollback, repeated operations, and preservation of an unrelated session remain unverified.
- The current supervisor tracks the launched DBus/XFCE command and X11 command PIDs. Whether TERM to the recorded DBus/XFCE PID always terminates every descendant on the target build is specifically unresolved; verify process-tree cleanup or add an isolated process-group owner before calling the lifecycle safe.
- This implementation must not be treated as release-ready. Physical testing is permitted when prerequisites exist; do not install missing packages without separate authorization.

## Historical remaining P2 gate (2026-10-17 snapshot; superseded by the 2026-10-18 completion evidence)

The following gate list predates the 2026-10-18 native-device updates below. Review this source implementation, then validate command behavior in an authorized isolated environment and on the target device. Record versioned evidence for successful start, repeated start, partial startup failure, stop, repeated stop, and unrelated-session preservation. Only then consider the P2 completion workflow.

## 2026-10-18 native-device audit update

- Reviewed: 2026-10-18 (Asia/Dhaka)
- Device/runtime actions: installed Ternuxx's approved base desktop transaction after the owner authorized scoped installs. `./ternuxx install` preview listed XFCE packages from official Termux repositories only and stated no upgrades, removals, recommendations, or repository changes. Applying it installed 77 new packages (8 requested packages plus dependencies), upgraded 0, removed 0; APT reported 12 unrelated packages not upgraded. The transaction used 45.7 MB of archives and 268 MB additional storage.
- Native readiness: `./ternuxx doctor --json` now reports `check=pass`, `missing_count=0`; Termux:X11, DBus, xauth, XFCE, PulseAudio, Vulkan tooling, and Adreno825 device node were detected. `glxinfo` is still unavailable, so renderer/GPU qualification remains deferred. Free `/data` reported 87 GB.
- Test evidence: `PATH="$HOME/.cache/ternuxx-audit-venv/bin:$PATH" bash scripts/repo_test.sh` passed 53/53 tests. The venv is outside the checkout and uses the repo's `requirements-dev.txt` (PyYAML 6.0.3). `bash tests/test_cli_help.sh`, `git diff --check`, and JSON parsing of `schemas/remote-access-config.schema.json` also passed during this audit.
- Device lifecycle: `./ternuxx start` started the Ternuxx-owned X11/XFCE session on `:0`; status reported supervisor/X11/XFCE live. Repeated start was idempotent. Stop cleared the owned processes and status reported no supervisor/X11/XFCE; repeated stop also returned safely. PulseAudio remained externally owned. `gui_visible` remains `unknown`: the Termux:X11 Android activity/display was not verified by this SSH-only session.
- The previous 2026-10-17 statements that no packages were installed and the owner had not authorized package installation are historical snapshots and are superseded by this update. No PRoot or remote-access network configuration was changed.

## Remaining P2 gate after device audit

- P2 remains in progress. The native server/session lifecycle passed basic start/repeat/stop/repeat checks, but Android-side visible GUI output and audio behavior were not observed. The required unrelated-session preservation has not been demonstrated on-device; fixture coverage is not a substitute. Record Termux:X11 app/version, visible display and audio outcome, and unrelated-session preservation before using the phase completion workflow.

## 2026-10-18 Android-side visible GUI confirmation

- Owner confirmed the Termux:X11 screen showed the GUI after the SSH-started Ternuxx session came up on display `:1`.
- SSH inspection of `~/.local/share/nativeternux/session.json` reported owner `ternuxx`, provider `native`, display `:1`, status `running`, and recorded live supervisor/X11/XFCE process identities. `./ternuxx status --json` agreed: running, supervisor/X11/XFCE yes, audio owner external.
- The current-session part of `~/.local/share/nativeternux/desktop.log` (01:03:16–01:03:43 local device time) records XFCE startup and desktop activity. It also reports: Freedreno Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER` for GPU id 6830; no system bus; and XFCE could not prepare an ssh-agent socket under `~/.ssh/agent` (directory absent). These warnings did not prevent the owner-confirmed GUI from appearing, but Vulkan acceleration, system-bus features, and agent forwarding are not qualified. The log contains older session output too; only entries matching the current `xfce4-session` PID 439/start time belong to this run.
- This confirms visible GUI output through owner observation; audio outcome and unrelated-session preservation remain unverified. Keep the session running for the owner's use; do not mark P2 complete yet.

## 2026-10-18 screenshot and X11 input probe

- The owner requested a screenshot while the Termux:X11 desktop was visible. Captured the X11 root window from native Termux display `:1` (912x1402), inspected the reduced preview, and confirmed it showed the XFCE desktop, dock, and desktop icons without unrelated personal content. The screenshot remains ephemeral under native `$HOME/.cache`; it was not added to the repository.
- The owner suggested xdotool. Its package preview contained only `xdotool` (58.4 kB download, 246 kB installed, 0 upgrades/removals); installed it from the Termux:X11 repo. `DISPLAY=:1 xdotool getdisplaygeometry` returned 912x1402. A bounded pointer-move test to (290,390) returned pointer location X=290,Y=391. No click or text input was sent. This verifies XTEST-style input event acceptance, not physical mouse/keyboard hardware behavior.
- `xdotool` does not capture screenshots. SKB's current Termux environment guide documents a PRoot `ffmpeg` X11 capture route; this run used native X11 root-window capture because the session and display are native Termux. No PRoot process or config was changed.

## 2026-10-18 P2 audio and package-preview follow-up

- The owner reported hearing the first test tone and requested three more. All three subsequent `paplay` invocations returned success through the native PulseAudio `OpenSL_ES_sink`; the sink returned to `IDLE`, with no active sink-input left. This verifies the native PulseAudio output path by owner-reported hearing. It does not yet prove that an XFCE application in another provider/context uses the same route. No PulseAudio settings or service ownership were changed, and the generated tone file was removed.
- Review of the first XFCE installation showed the console preview listed the eight requested package candidates, while APT subsequently installed 77 new packages including dependencies. Although the owner had authorized scoped installation and the transaction performed zero upgrades/removals, the recorded preview did not expose the full dependency transaction well enough to meet P2's exact-preview gate. This install remains a historical gap; no rollback is appropriate.
- `lib/phases.sh` now displays the complete APT `Inst` transaction (dependency package/version pairs) in text and JSON preview output, and rejects empty simulation output or a direct-package candidate mismatch before preview/apply. Two synthetic APT regression cases were added. The focused package-plan suite passed 5/5 and the full repo suite passed 55/55. A fresh uninstalled-package device preview cannot be recreated without changing package state, so the change is verified through fixtures and read-only source review.
- The owner confirmed hearing the tone and seeing the screenshot GUI. The 8022 SSH control shell also remained usable for status and repeated-stop commands after a Ternuxx stop; this does not prove preservation of a separate GUI/PRoot session. P2 remains in progress: independent graphical-session preservation and the initial exact-preview evidence are still open.


## 2026-10-18 P2 device lifecycle follow-up

- Device baseline: Termux `0.119.0-beta.3`; native package `termux-x11-nightly` `1.03.01-6`; Android 16 / aarch64. The Android Termux:X11 APK version was not available through the Termux app-shell package query. `gui_visible` remains an owner-observed fact, not inferred from CLI status.
- Native `:1` start was repeated twice and both calls were idempotent; status retained the same running Ternuxx session. A forced partial startup failure on isolated display `:2` (test-only DBus launcher exited before XFCE startup) returned failure and recorded `status=failed` without changing the active `:1` session.
- That first failure probe exposed stale `:2` socket/lock files after the X11 process had exited. `lib/desktop-supervisor.sh` now removes only the exact display socket and lock when the recorded X11 process group is gone and the lock PID matches the session's recorded X11 PID. Display syntax is constrained to numeric `:N` values. The stale artifacts from the first test were removed only after matching them to the recorded failed Ternuxx `:2` session and confirming its X11 process identity was gone.
- Repeating the injected failure after the fix again returned failure, set `status=failed`, left no `:2` X11 process/supervisor, and left neither the `X2` socket nor `.X2-lock`. The live `:1` Ternuxx desktop remained running throughout.
- On a fresh supervisor using the updated source, stopping `:1` returned `status=stopped` and removed its exact X11 socket/lock. The existing Debian PRoot login (PID 15638, process start ticks 9455) remained listed with the same identity before and after; the 8022 SSH control session also remained connected. Repeated stop succeeded. The native GUI was restarted on `:1` afterward and status reports running. Earlier owner confirmation of visible XFCE and owner-heard audio remains the display/audio observation; this latest CLI status alone does not assert visibility.
- Runtime package/version inspection: `termux-x11-nightly` is `1.03.01-6`; Termux is `0.119.0-beta.3`. Android app metadata for the Termux:X11 APK could not be queried from the app shell.
- Verification after source change: `bash -n lib/desktop-supervisor.sh lib/desktop.sh`; `git diff --check` for the edited source/test files; desktop lifecycle fixture 6/6; full `bash scripts/repo_test.sh` 55/55. The fixture now leaves mock socket/lock artifacts on shutdown so exact owner-checked cleanup is covered.

### Remaining P2 gate (historical status before final gate review)

At this point in the audit, P2 remained `in_progress`: the first native XFCE install's console preview showed direct candidates but not the complete 77-package dependency transaction before consent. That original display cannot be reconstructed without another package transaction, and no reinstall/removal was done to recreate it. The Termux:X11 APK version was also not yet recorded. Later sections add target versions, lifecycle results, a saved-preview approval binding, and a live native APT preview validation; the final phase decision is recorded in [P2 completion evidence](P2-phase-completion-2026-10-18.md).


## 2026-10-18 recovered APT package closure and durable installer records

- Read the native Termux APT `history.log` entry for the XFCE install (`2026-10-18 00:54:27` to `00:54:46`, device local time). It records all 77 package names, aarch64 versions, and APT automatic-install marks: 8 explicitly requested XFCE packages and 69 automatically resolved dependencies; 0 upgrades and 0 removals. The four other base entries (`termux-x11-nightly`, `dbus`, `pulseaudio`, `python`) were already present, so APT did not include them in this transaction.
- The structured snapshot is [P2-termux-xfce-install-transaction-2026-10-18.json](P2-termux-xfce-install-transaction-2026-10-18.json). It preserves exactly the fields APT history retained. It does not invent archive hashes or repository URLs, which APT history did not record.
- `lib/phases.sh` now stores each successful dependency preview in the private Ternuxx state directory at `install-transactions/`, including requested package candidates, the full `name=version` transaction, and the complete APT simulation with repository/architecture lines. Records are atomically written as mode `0600` beneath a mode `0700` directory. Successful `--yes` application also stores an `applied` record.
- Transitive dependencies stay APT-resolved: the installer does not freeze the historical 69 dependencies as permanent direct packages. Each current preview captures the exact closure from the fresh signed package indexes, then apply rebuilds the plan before APT runs. This preserves future repository compatibility while recording what that run would install.
- This recovery establishes the exact applied package closure, but it cannot recreate the user-visible preview text shown before the original consent. Therefore the original preview-before-consent evidence gate remains historical and P2 stays `in_progress`; no package reinstall/removal was done to manufacture new evidence.


## 2026-10-18 P2 final target-state refresh

- ADB read-only package metadata query on the connected Android target reports Termux `0.119.0-beta.3`, Termux:X11 APK `1.03.01-9471ad9-14.08.26` (versionCode 15), Android 16, product `onyx` / model `25053RT47C`. Native Termux reports `termux-x11-nightly` `1.03.01-6`. The ADB transport is named `emulator-5554`; device properties identify the Redmi/onyx target, so this evidence is recorded as the attached target's reported metadata rather than inferring from the serial name.
- `./ternuxx status --json` reports the native Ternuxx session running on `:1`. Owner's earlier visible-screen confirmation and audio report remain the visual/audio observations. `DISPLAY=:1 ./ternuxx doctor --json` passes readiness and identifies `llvmpipe (LLVM 21.1.8, 128 bits)` for native OpenGL; this is software rendering and is not an acceleration claim. Without `DISPLAY`, renderer is correctly unknown.
- Updated installer help to state where full preview/applied records are stored and that APT may partially install before failure; Ternuxx intentionally performs no automatic package removal/rollback. Updated readiness output so it distinguishes prerequisite checks from full lifecycle qualification. This target's start/repeat/stop/failure/PRoot-preservation evidence is recorded above; other device builds remain unqualified.

## 2026-10-18 exact-preview approval binding

- The earlier installer persisted previews, but `install --yes` rebuilt a plan and could apply it without proving it was the plan the owner had reviewed. The installer now assigns a SHA-256 plan ID over requested candidates, the complete resolved package/version closure, and the exact APT simulation. JSON and human preview output show that ID.
- Apply now requires both `--yes` and `--plan-id ID`, re-resolves the transaction immediately before APT, and refuses unless a private (0600) saved preview under a 0700 Ternuxx state directory matches the entire current plan. The state path must be inside HOME and contain no symbolic-link components. Package resolution still blocks nonofficial repos, removals, and upgrades.
- Added a preview JSON schema and updated installer/help docs. Fixture tests verify exact record/hash, successful same-plan match, changed-plan refusal, missing-consent rejection, outside-HOME/symlink path rejection, and private modes, and that the apply helper passes the complete version-pinned closure to APT. No package install/apply was run for this change; the target's base packages are already installed.
- The first install's historical pre-consent output cannot be reconstructed; APT history remains the evidence for the applied 77-package closure. The new approval binding closes the forward safety/reproducibility defect but does not rewrite that historical gap. P2 remains `in_progress` pending review of the complete evidence and target qualification; no disposable package-state apply was performed.

### 2026-10-18 target-native preview validation

- Exercised `nt_cmd_install --preview` against the target's current official Termux signed indexes using the optional, not-installed `xfce4-power-manager` candidate. The 4-package closure and full simulation were saved under a private temporary Ternuxx state directory inside the repository; the test fixture was removed after evidence capture.
- Re-resolved the same plan with the target's real APT simulator, validated the persisted preview ID, and intercepted the final APT invocation before execution. Captured argv exactly matched the entire version-pinned closure. No package was installed and no package index was refreshed.
- Full output, closure, plan hash, modes, and explicit non-mutation limitation are recorded in [live installer preview evidence](P2-live-installer-preview-validation-2026-10-18.json). This validates current preview/approval behavior while preserving the fact that the earlier XFCE pre-consent console capture is incomplete. Final gate review: [P2 completion evidence](P2-phase-completion-2026-10-18.md).


## 2026-10-18 read-only installed package-closure corroboration

- Native `dpkg-query -W` found all **77/77** packages from the recovered XFCE APT history record installed at their exact recorded versions; no missing package or version drift was found at 04:51 +06.
- This strengthens current installed-state reproducibility but is not the original pre-consent APT simulation. The old console-capture gap remains as recorded. Details: [installed package-closure audit](2026-10-18-p2-installed-package-closure-audit.json).

## 2026-10-18 display-conflict regression fixtures

- Added isolated lifecycle fixtures for a listening Unix X11 socket owned by an external mock server and for a display lock file without a socket. Both explicit `start --display 7` attempts fail closed, preserve the socket/lock, and create no session or operation journal. The fixture permits the private empty state directory created before display selection.
- Native Termux focused run `python3 -m unittest tests.test_desktop_lifecycle_fixture -v` passed **8/8** after correcting that fixture expectation. This validates conservative artifact conflict handling; no live device display or desktop lifecycle was touched. Full repository regression run is recorded below when complete.
- Full native Termux `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` passed **160/160** in 32.914 seconds with these cases included. No target GUI/PRoot/SSH/boot/package action was performed by the fixture suite.


### 2026-10-18 current installed closure recheck

- Re-queried all 77 package names from the recovered native XFCE transaction with `dpkg-query -W`; 77/77 remain installed at their exact recorded versions. This is current-state corroboration only and does not recreate the original pre-consent dependency preview. See [recheck evidence](2026-10-18-p2-package-closure-current-recheck.json) and [P2 completion record](P2-phase-completion-2026-10-18.md).


## Latest P2 package-state recheck — 2026-10-18

- Native `dpkg-query -W` at 01:15:07 UTC confirmed the recovered 77-package XFCE transaction remains installed at exact recorded versions (77/77; 0 missing/mismatched). No package action was run. See [latest read-only closure evidence](2026-10-18-p2-package-closure-latest-recheck.json).
- This strengthens current-state corroboration only. The original pre-consent preview was not captured completely and remains unavailable; the later live exact-preview validation is a separate event and does not reconstruct it. P2 remains closed under the dated completion decision, with that evidence limitation explicit.


- Follow-up P2 installed-closure check at 01:15:07 UTC again found all 77/77 historically applied XFCE packages at their exact recorded versions, with no package change. Current closure evidence: [latest recheck](2026-10-18-p2-package-closure-latest-recheck.json). The original full pre-consent preview remains unrecoverable.


### Native installed-closure recheck — 2026-10-18 08:18 UTC

Native SSH read-only checks reported Ternuxx desktop `:1` running and all 77 recovered XFCE transaction packages at the exact recorded versions. No package or lifecycle action ran. This does not recreate the original complete pre-consent preview. See [native closure evidence](2026-10-18-p2-native-closure-recheck-0816.json).
