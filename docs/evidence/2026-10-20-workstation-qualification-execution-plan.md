# Ternuxx Workstation Qualification Execution Plan

**Started:** 2026-10-20 (Asia/Dhaka)
**Implementation target:** Native Termux checkout at `/data/data/com.termux/files/home/ternuxx`
**Execution route:** owner-provisioned SSH 8022; confirm Android/Termux identity for each implementation and test session
**Baseline:** local HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`; GitHub main `89a2a0b8f88b710775b1ee9f038db818d82cd6ce`; existing dirty worktree preserved
**Status:** execution plan; gates must be updated only with current evidence

## Confirmed baseline and open hypotheses

- Native Termux is confirmed by Android kernel, UID `u0_a490`, `PREFIX=/data/data/com.termux/files/usr`, and the canonical checkout path.
- The worktree has 73 changed tracked paths and 107 untracked paths. These are pre-existing work and must be classified/preserved; no broad cleanup, reset, or blind stash.
- Latest observed GitHub Contract workflow failed on the obsolete Termux-only launcher path. Knowledge Sync recorded 326 tests with two errors and failed its final test gate. Current CI must be rerun after any repair.
- Debian PRoot is installed and an active PRoot process was observed in the prior read-only baseline. No rootfs, active session, service, or 8022 change is authorized by this plan.
- Owner direction: retain 8022 unchanged; consider 8023 hardening only after key access and recovery are verified.
- User reports `tx gui` fails to launch the intended Native Termux graphical management UI. Root cause is not yet established. Existing source routes `tx gui` to native desktop lifecycle; verify intended product UI and installed graphical infrastructure before changing routing.
- An obsolete standalone `gui` shortcut is reported. Locate only Ternuxx-owned command registration/help/completion/docs and remove that alias while retaining canonical `tx gui`; do not touch unrelated system commands or PRoot GUI launchers.
- License remains unresolved; no release, tag, or license selection is authorized.

## Ordered work packages

### W0 — Preserve and plan
Capture Git branch/HEAD/remotes/upstream, staged and unstaged state, tracked/untracked/ignored inventory, critical runtime/session/service state, and exact Native Termux execution context. Review project instructions, security policy, architecture, current phase state, audit evidence, and CI definitions. Classify existing changes before editing. This plan is the mission record; add dated evidence rather than rewriting historical reports.

### W1 — Native GUI and CLI contract
Trace `tx gui` dispatch, native GUI lifecycle and management-center launcher, session/display/environment checks, installed packages/binaries, permissions, logs, and relevant configuration. Identify whether the report concerns the native XFCE desktop lifecycle or graphical management center; follow the documented architecture and current owner direction. Implement the smallest safe fix with actionable failures, exit codes, idempotence for a healthy session, and stale-state handling. Test already-running, missing-display, dependency failure, and stale/malformed state paths. Remove only the obsolete top-level `gui` shortcut from Ternuxx registration, completion and current help/docs/examples; keep `tx gui`, native desktop code, and PRoot GUI routes. Verify actual display/session startup only if an existing safe test path is available; do not stop or replace a live session. Mark human visual usability separately from automated launch tests.

### W2 — Repository/CI recovery
Reconcile local/remote ancestry without discarding dirty files. Fix the shell entrypoint portability contract and workflow failure. Investigate both CI wakelock errors and fix the root cause where safe. Run scoped then applicable suite, syntax and deterministic-state checks; inspect side effects and diff. Use established knowledge generation. Verify both workflows on the intended revision before marking CI complete. Do not commit/push unless separately requested by project instructions; no force push.

### W3 — Native–PRoot boundary and session safety
Review native/guest launchers, environment sanitization, shared services, display and audio adapters, ownership registry, and CPU/GPU evidence boundaries. Preserve Bionic/glibc separation and existing Debian rootfs/packages/GPU workflows. Exercise only isolated fixtures for identity, concurrency, locking, atomic updates, attach/detach/stop logic, and failure recovery. No live guest entry, rootfs edit, or active-session signal without a demonstrated recovery procedure and required authorization.

### W4 — Security and desktop concurrency
Keep 8022 as-is. Inspect effective 8023 configuration and verify key-only access/recovery before any reversible hardening; otherwise document the blocker. Do no external probing. Fix desktop stale/current replacement races using storage-appropriate synchronization. Test concurrent updates, malformed/stale data, ownership rejection, interrupted writes, recovery, and truthful audit events.

### W5 — Cron, boot and service lifecycle
Verify Cron policy at write and dispatch; test path containment, duplicate/concurrent dispatch, stale PID, service status/log/progress and unavailable dependency behavior in isolated fixtures. Keep production boot disabled; no reboot or service interruption for qualification.

### W6 — Management interfaces and release evidence
Compare CLI/API, TUI, Web, GTK and native graphical management UI operations against the capability matrix. Test safe mutation parity and visible errors/progress; test responsive Web output and GTK usability only where available. Do not claim human visual qualification from compilation or process exit. Reconcile current status, evidence, phase state and capability claims. Keep release status NOT RELEASE-READY while critical CI, PRoot, production boot, GUI usability, or license gates remain unresolved.

## Acceptance and stop conditions

For each change: record pre-state; state expected behavior; make the narrowest change; run targeted then relevant regression checks; inspect diff and side effects; record exact command, source revision, result, and limits. Distinguish source inspection, fixture tests, Native Termux runtime tests, PRoot tests, CI, and human visual acceptance.

Stop before destructive migration/cleanup, rootfs or package changes, live service/session interruption, SSH lockout risk, production boot enablement/reboot, bypassing ownership/security checks, license choice, or publication. Continue independent safe work and record exact evidence needed to resume. Any unavailable test remains an explicit unverified gate.


## Execution checkpoint — 2026-10-20

- W0: Native Termux execution/path verified. Dirty worktree preserved; origin/main is one generated-state commit ahead. Plan recorded.
- W1: tx gui now opens the Native GTK management center with fail-closed local-display checks; desktop lifecycle remains tx start, with explicit compatibility subcommands. Bare gui is no longer generated/help-advertised. Fixture and CLI coverage passed. Native X11/XFCE session was subsequently started on :2 with owner authorization; the GTK process launch was attempted. Automated checks show the session live, while Android window visibility and human visual acceptance remain unverified. A marked personal-shell shortcut, if installed, remains untouched.
- W2: Portable root launcher and deterministic generated-state reconciliation implemented. GitHub CI failure cause identified; runner umask fixture corrected. Local full suite passed 528/528. CI has not rerun on local changes.
- W3: Full fixture suite passed; no PRoot/rootfs/session operation was performed. Live login, identity, detach/reattach and shared-rootfs gates remain open.
- W4: 8023 hardened to key-only after key access and 8022 recovery were verified; config syntax, effective policy, service readiness and post-change login passed. 8022 unchanged. Desktop stale-record replacement is now restricted to the private lifecycle lock contract; lock and lifecycle fixture tests pass. Arbitrary same-UID writers outside Ternuxx remain outside the guarantee.
- W5: Cron/boot fixture suite passed; production boot and reboot remain unqualified and disabled.
- W6: Current capability/evidence updated. Overall release status remains NOT RELEASE-READY because CI, live GUI acceptance, PRoot integration, production boot, native CPU/GPU/NPU workload integrations, owner profile state, licensing and provenance gates remain unresolved.

See execution evidence at 2026-10-20-workstation-qualification-execution.md. No commit/push or release action was taken.

### W6 add-on — CPU/GPU/NPU visibility in Native GUI

Expose a read-only, typed acceleration qualification resource in the Native GTK catalog. Report CPU as baseline; probe native renderer/Vulkan only when explicitly queried from the GUI current display; keep Debian PRoot GPU evidence separate and dated; show NPU as unverified until a named runtime and workload pass. Do not install runtimes, access or rewrite PRoot configuration, or claim inference acceleration. Acceptance: catalog visibility, bounded read-only bridge dispatch, clear CPU/GPU/NPU context status, tests, and GUI evidence that distinguishes source/fixture checks from an opened visual window.

### W1 follow-up — stable Native Ternuxx display

Owner clarified that Native Ternuxx must use `:1` as its default consistently; `:0` remains the existing Debian PRoot display. Change default desktop start to fail closed on an occupied/ambiguous `:1`, without silently allocating `:2`. For a stale Ternuxx session, permit cleanup only when the private stale session record's exact X11 PID matches the X lock, that PID is absent, the private socket refuses a connection, and artifact identities remain stable. Keep explicit alternate-display selection available only as an owner-directed override. `tx gui` must derive the management-window target from the verified session when `DISPLAY` is unset and refuse a conflicting exported display. Acceptance: fixture coverage for safe same-display restart, exact stale-pair recovery, mismatched/live PID refusal, no implicit duplicate display, Native runtime migration preserving the active PRoot `tx db` shell, and GUI launch on the recorded display.

### W1 follow-up — shared GUI resource conflicts

Keep Native Ternuxx on the verified :1 session and Debian PRoot's existing :0 endpoint separate. `tx gui` attaches to the recorded Native session and does not start/stop X11, PulseAudio, D-Bus, or PRoot. The desktop lifecycle owns only its recorded supervisor/process group and private session state. Stale X11 artifacts may be reclaimed only with the exact absent PID from a stale Ternuxx record, same-UID regular lock/socket identity, refused socket, and unchanged artifact identities; active, mismatched, or unknown locks fail closed. Owner direction: Native Termux/Ternuxx must own PulseAudio service lifecycle, and Debian PRoot must consume that Native endpoint as a client. Before implementation, qualify exact process/config ownership, safe no-autospawn probing, private listener/authentication, stale-versus-live state recovery, logs, rollback, and concurrent PRoot CLI plus Native GUI. Preserve live/foreign locks and fail closed; audio unavailability must not block CLI/X11 startup. PRoot CLI (`tx db`) and Native management GUI are separate process/session scopes and must coexist without cross-stopping or environment inheritance. Acceptance: test exact stale X11 recovery and active/unknown refusal; confirm `tx gui` uses the session's :1 and rejects :0; confirm `tx db` remains alive; verify PRoot/GUI coexistence; qualify Native-owned PulseAudio startup and authenticated PRoot client playback as a distinct pending work package. Actual audio playback remains unqualified.

### W3 follow-up — Native-owned PulseAudio / Debian PRoot client

Owner explicitly authorizes Ternuxx to manage Native PulseAudio and to adapt the existing Debian PRoot client environment/config where needed. Keep the installed PulseAudio `default.pa` untouched because it is package-owned and currently modified by the owner. Live pre-state: no PulseAudio process or loopback listener at 4713; Native package and 256-byte private cookie exist; `default.pa` has one loopback anonymous listener (127.0.0.1:4713); PRoot `tx db` PID 14360 has `PULSE_SERVER=127.0.0.1`. Ternuxx must derive a private managed config that replaces only this exact known line with cookie authentication, run one foreground Native daemon with an exact identity record, and preserve/decline unknown or live servers and unsafe state. `tx start`, `tx gui`, and Debian `tx db` ensure the service idempotently, but audio failure never blocks GUI/CLI. `tx stop` must leave audio running because PRoot sessions may still use it. New `tx audio status|start|stop|restart` controls only the exact Ternuxx-owned process. Pass `tcp:127.0.0.1:4713` and the private Native cookie path to Ternuxx-launched Debian clients; never copy native libraries or change the PRoot rootfs unless required by evidence. Acceptance: fixtures for authenticated config transformation, wildcard/duplicate listener refusal, private cookie/state validation, lifecycle locking and PID reuse; Native start/status/stop identity tests; explicit no-autospawn probe; PRoot guest protocol test; actual output verification distinguished from protocol readiness; prove active `tx db` and Native GUI remain alive together. No global PulseAudio config edit, package install, rootfs replacement, or broad process cleanup.


### W3 follow-up — implementation checkpoint (2026-10-20)

Supersedes the earlier statement that Native PulseAudio ownership/client wiring was pending. Implemented private identity-managed Native PulseAudio lifecycle and explicit PRoot client endpoint/cookie handoff. Native `tx audio status` and authenticated explicit-endpoint `pactl info` passed; a separate `tx db -- pactl info` passed. Native `:1` desktop and existing interactive PRoot PID 14360 remained live. Full Native regression suite passed 547/547. Do not stop/restart the audio service while unknown PRoot clients may depend on it. Human audible output, live lifecycle race/stress, CI, and full PRoot session lifecycle remain open. See the matching evidence section in `2026-10-20-workstation-qualification-execution.md`.

### W6 follow-up — acceleration GUI and audio catalog truth

The management catalog/GTK bridge exposes read-only CPU/GPU/NPU qualification through `native.acceleration.qualification`; this does not prove accelerated workload support. Keep CPU as baseline, GPU as renderer/workload-specific, and NPU unverified until named workloads pass. Audio lifecycle controls are currently exposed through the canonical `tx audio` CLI; management UI lifecycle parity is not qualified. Updated the catalog ownership/status record to reflect the implemented Native service without advertising UI operations that are not wired. Human Android-visible GTK acceptance remains pending.


### W0/W2 follow-up — source and CI reconciliation (2026-10-20)

Fetched origin without changing the checkout. Local HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d` is the parent of `origin/main` `89a2a0b8f88b710775b1ee9f038db818d82cd6ce`; remote delta is one commit containing only six generated `.repo` files. Because `.repo/STATUS.md` and `.repo/project.yaml` are already modified in the dirty owner worktree, no checkout/merge/rebase overwrote those files. GitHub run `39159994935` failed because committed `ternuxx` invoked the Termux-only interpreter at `bin/ternuxx` on Ubuntu (exit 127). Local workflow/help-contract corrections now target `bin/tx` and `tx`; GitHub verification is pending publication by the owner. Run `39159994930` verified repository knowledge with 0 findings, pushed the generated-only `89a2a0b` commit, then intentionally failed because its test step had 326 tests and 2 wakelock fixture errors. Native dirty-tree full suite is 547/547 passed; that does not qualify GitHub CI. At this live recheck, the worktree has 78 changed tracked paths, 0 staged paths, and 118 untracked paths; all were preserved. Counts are a timestamped snapshot and can change as owner work continues. No commits, pushes, reset, stash, or integration checkout were performed. Exact evidence is in the current execution record.


### W3/W6 follow-up — isolated guest audio cookie and acceleration contexts

Root cause found in the Ternux guest verifier: `proot-distro login --isolated` intentionally excludes HOME, and its command passed `PULSE_SERVER` without the Native cookie. It therefore reported guest audio unavailable while the Native endpoint and ordinary `tx db` client worked. Added a validated private-cookie check and a single-file bind to a fixed guest path only for the read-only guest status check. No HOME/shared storage or guest config is exposed/changed. Live repeat on Debian `:1`/Zink now reports complete: X11 reachable, Zink/Turnip Adreno 825 renderer, guest PulseAudio reachable; safety fields confirm no guest writes/packages/services changed. Profile owner stays unverified. Focused PRoot test suite 24/24 and full Native suite 551/551 pass.

Keep accelerator routes distinct in GUI and evidence: Native CPU baseline; Native GL currently llvmpipe and Vulkan unsupported on this package; Debian PRoot Zink/Turnip is live renderer-verified on `:1`; VirGL remains retained as an available profile but is not active in this check; NPU remains experimental/unverified without named runtime/workload. The GUI bridge now has tested read-only audio status plus CPU/GPU/NPU findings. It does not claim hardware acceleration for the Native GTK window or guest inference. Human visual/audio acceptance and PRoot session lifecycle remain open.


### W2/W4/W6 follow-up — local contracts, SSH, and GUI evidence

Local Native checks matching the changed repository-contract workflow passed: portable `bin/tx` shell syntax/help contract, deterministic repository knowledge (0 findings), strict README knowledge bridge, project classification, and required-document checks. This is not a GitHub CI run. Read-only SSH inspect confirms 8022 remains wildcard/password-enabled as instructed; managed 8023 is running under Runit, loopback-only, key-only, and installed/source service identity matches. Listener ownership is permission-denied; no external reachability test was performed and no SSH config change was made.

The GTK bridge's audio resource inspection now returns the authenticated Native readiness finding, and its acceleration resource returns CPU/GPU/NPU findings. Current Native renderer is llvmpipe and Native Vulkan is incompatible; current Debian PRoot `:1` status is Zink/Turnip Adreno 825. VirGL remains preserved but is stopped/not active in this snapshot; NPU remains unverified. Read-only guest verify now confirms authenticated audio as well. Full suite: 551/551.


## Owner steering — Native-first Ternuxx workstation and accelerator ownership (2026-10-20)

**Confirmed from live device:** implementation runs in Native Termux as `u0_a490`, with `PREFIX=/data/data/com.termux/files/usr` and Termux `0.119.0-beta.3`, at `/data/data/com.termux/files/home/ternuxx`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`. The existing Debian PRoot is active (interactive PID 14360). Native desktop `:1` and Native Ternuxx PulseAudio PID 16222 are live. PulseAudio explicitly reads `$HOME/.local/share/ternuxx/audio/default.pa`; the installed package `$PREFIX/etc/pulse/default.pa` is not its active config and current evidence does not tie it to the reported issue. Do not edit/restart it without new causal evidence.

The current Debian `/etc/profile.d/termux-profile.sh` is a 496-byte legacy-named profile containing display, Zink/Turnip, PulseAudio, PRoot metadata, and app-compatibility variables. Debian `:1` read-only verification selected Zink/Vulkan on Adreno 825 (`MESA_TURNIP`). Treat settings as potentially functional; do not delete them wholesale. A targeted Native device-node check found `/dev/kgsl-3d0`; queried adsprpc nodes were absent and `/dev/dri` enumeration was denied. NPU access remains unknown; no NPU package/workload was installed or run.

### Work packages (dependency order)

- **W7a — Ownership/config inventory:** trace Ternux/Termux-specific PRoot dependencies in `tx db`, guest identity discovery, guest profile, graphics/audio handoff, and install flows. Separate legacy control-plane dependencies from guest libraries/settings needed for Zink/Turnip, audio, sudo, and existing workloads. Before guest config mutation, record content, mode, owner, hash, and a private scoped rollback copy. Never modify the separate `soobujmiah/ternux` repository or remove packages/rootfs data.
- **W7b — Ternuxx-owned clean setup:** make Native Ternuxx the default authority for its services and PRoot handoff. Replace per-command reliance on the legacy Ternux CLI/state with a validated Ternuxx-owned guest identity/profile contract suitable for a fresh Ternuxx setup. Existing settings must continue to work; ambiguous users/backends fail closed with actionable CLI guidance. No automatic guest package install or rootfs replacement.
- **W7c — Accelerator contract:** Native Termux owns hardware/display/audio service endpoints; Debian keeps ABI-compatible glibc userspace drivers and receives explicitly handed-off host capabilities. Never copy Bionic libraries into Debian. Preserve CPU baseline, current Zink/Turnip route, VirGL option, and experimental NPU integration separately. Report renderer/runtime per process; a Native `llvmpipe` renderer, device node, or Vulkan loader alone is not acceleration proof. NPU remains experimental until its device route and workload are verified.
- **W7d — Login environment contract:** installed proot-distro writes /etc/profile.d/termux-profile.sh on normal login from the supplied environment. Preserve that package writer and file name; pass Ternuxx handoff values through typed Native launch arguments instead of editing the guest profile/package. Verify a fresh login and compare generated profile before/after. Do not alter package code, sudo policy, or unrelated hooks.
- **W7e — Release reconciliation:** reflect this ownership contract in install/upgrade docs, CLI help, capability matrix, evidence, clean-install checks, and release gates. Ordinary Ternuxx operation must not require installing or invoking the separate Ternux CLI.

**Acceptance:** `tx db`, GUI, and typed PRoot operations use Ternuxx-owned configuration without a legacy Ternux CLI/state dependency; duplicate GUI/display/audio owners are rejected or reconciled without killing unrelated sessions; Debian Zink/Turnip remains available when selected, VirGL remains an independently selectable route, CPU remains baseline, and NPU is accurately marked experimental/unverified. Recovery of changed guest profile is documented and tested. Existing PRoot user data/packages, active sessions, and SSH 8022 stay intact.

**Stop conditions:** do not remove guest packages, sudoers, or user data based on naming alone; do not restart live services or stop sessions to test profile changes; do not edit package-owned `default.pa` unless a reproduced defect proves causation and rollback is verified. Keep GUI `:1`, Native PulseAudio, PID 14360, and SSH 8022 unchanged during inspection.


### W7d addendum — prevent Android runtime environment persistence

The installed proot-distro login writer persists a fixed set of host Android runtime variables into the guest profile during every normal login. Preserve its package-owned writer, but Ternuxx launch paths must remove those variables before invoking it, then provide display, PulseAudio, and selected graphics settings explicitly. Cover tx db, named PRoot GUI launches, shortcut availability probes, and the XFCE wrapper. Acceptance requires a real Debian login to show no Android ART/classpath/storage variables while retaining :1, the authenticated Native audio endpoint, and the selected Zink/Turnip route. Keep the existing rootfs/profile, active sessions, and package installation intact.

### W7 current evidence checkpoint — 2026-10-20

Native guest verification passed on Debian :1 with Zink/Turnip Adreno 825 and authenticated Native PulseAudio. A real tx db command confirmed no proot-distro-injected Android runtime keys, retained explicit display/audio/Zink settings, GL acceleration, and PulseAudio reachability. The generated profile remains proot-distro-owned and contains the explicit workstation settings. The live Native GTK management process started on the verified :1 session; the Android-visible window remains unverified and the Native Vulkan backend logged VK_ERROR_INCOMPATIBLE_DRIVER. CPU remains the baseline; NPU is still unverified. Current Native verification passed: `scripts/repo_test.sh` ran 550 tests with 0 failures; CLI help contract passed; `python3 -m tools.repo_knowledge verify` reported 0 findings; strict README bridge passed. These are local results on dirty HEAD 69e378e; GitHub CI has not tested these unpublished changes.


### W7 final routing status — 2026-10-20

Default Ternuxx PRoot app launch now targets only the verified Native Ternuxx display. The optional old Ternux session-owner field/CLI route was removed from CLI, shared API, TUI, and launch helper; an old API owner field fails validation. Test coverage confirms this boundary. Final local suite: 550/550 passed after this change; GitHub CI remains failed on the published source revision and has not evaluated this dirty checkout.
### W7f addendum — Native host acceleration and clean Ternuxx setup

Owner direction is that Ternuxx is the final, independent workstation project: Native Termux is its host/config/service authority and Debian PRoot remains its ABI-compatible Linux workload layer. A clean Ternuxx setup must avoid dependence on the separate Ternux CLI or unrelated legacy control-plane state while retaining dependencies actually needed for Termux:X11, Native audio, CPU tools, host device handoff, Debian Zink/Turnip, VirGL option, and experimental NPU adapters. Do not remove guest packages/profile variables by naming alone; identify each live consumer first. Native Bionic libraries must not be copied into Debian glibc directories.

Current baseline evidence: Native `DISPLAY=:1` graphics probe reports llvmpipe and `VK_ERROR_INCOMPATIBLE_DRIVER`, while the read-only Debian `tx proot verify` reports Zink/Vulkan 1.4 on Adreno 825 (`MESA_TURNIP`), X11 reachable, and authenticated Native PulseAudio. Native CPU is the baseline but has no Ternuxx inference runtime/model. NPU vendor libraries are visible under `/vendor/lib64`, while the probed FastRPC device nodes and known runtime CLIs are not visible in the Native process; execution remains unverified. VirGL is preserved but inactive. The installed PulseAudio package `default.pa` is not the active Ternuxx-managed config; do not edit it absent a reproduced causal defect.

Next safe work: inventory Ternuxx-owned install manifests and command dependencies; model each dependency as Native host, Debian guest ABI-compatible, optional provider, or unrelated legacy integration; verify clean-install plans in isolated fixtures only; assess whether current Ternuxx guest handoff already meets a minimal Ternuxx-only setup. Any production guest config change requires content/mode/owner/hash capture and tested scoped recovery before mutation. Keep CPU, Zink/Turnip, VirGL and NPU provider qualifications separate. NPU success requires an official compatible runtime, actual NPU delegate selection and correct representative model result, with fallback and thermal/performance evidence. This addendum changes no live state and is not a claim of NPU support.

### W7g — remove legacy companion dependency from current PRoot verification

Remove current Ternux companion-version/status fields and dead CLI-discovery code from the Ternuxx PRoot diagnostic contract. Keep selected guest identity explicit or resolve the unique regular account directly from the installed Debian rootfs. Mark the old companion JSON schema deprecated and preserve historical dated evidence. Reconcile README, architecture, installation, dependency fallback, management API, and current-state docs to identify Native Termux as host authority and the existing Debian PRoot as guest. Acceptance: no runtime lookup/call of the separate Ternux CLI; strict schema tests pass; live read-only verification still reports the selected display, renderer, and authenticated audio, with no guest mutation. No packages, rootfs/profile, service, or session may be changed for this cleanup.
