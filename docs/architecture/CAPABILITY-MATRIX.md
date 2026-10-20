# Capability matrix — Native Termux audit (2026-10-20)

Updated against clean Native checkout `204b561` and the checked-in client/service source on 2026-10-20. The current catalog has 13 categories and 20 resources; the typed service registers 84 operations. This matrix separates shared-service operations, actual per-client controls, and human visual qualification. It does not treat a catalog operation as a client action. Native GTK visual interaction remains unqualified.

## Surface summary

| Surface | Current reach | Usability/coverage gap |
|---|---|---|
| CLI | Organized top-level help plus detailed help; aliases are documented. Native management commands reach the broadest set, including Cron definitions/executions, timezone, boot, PRoot sessions/shortcuts, backup/recovery, continuity, graphics, and services. The typed service currently registers 84 API-v1 operations. | Some service operations are internal or only available through grouped CLI commands; full command coverage is not identical to the operation registry. |
| Shared service / API | Catalog and typed service define the common operation/capability contract. Loopback browser sessions receive scoped reads and only narrow desktop, graphics, monitoring, and managed SSH 8023 actions. | API registration does not imply all clients expose an action. HTTP does not grant PRoot lifecycle, Cron mutation/runtime, timezone mutation, boot mutation, or backup/recovery write capabilities. |
| TUI | All catalog categories, search, live status reads, explicit per-resource action hints, confirmed desktop and managed SSH 8023 lifecycle, graphics status/OpenGL/GLES/Vulkan verification and Native backend selection, monitoring policy, named PRoot app launch, Cron saved-job listing, and recovery history/details. | No guided timezone, Cron mutation/execution history, boot, backup/restore, PRoot session lifecycle/recovery, or SSH deploy flow. Visual keyboard acceptance remains owner-operated. |
| Web UI | Catalog navigation, search/status filtering, supported/planned operation lists, selected reads, confirmed desktop lifecycle, graphics status/OpenGL/GLES/Vulkan verification and Native backend selection, monitoring policy, preview-confirmed managed SSH 8023 lifecycle, recovery history, and Cron status/job-list reads. | No PRoot app/session actions, Cron mutation, timezone mutation, boot, backup/restore, SSH deploy/rollback, or recovery writes; rendered browser viewport remains unverified. |
| Native GUI app | Installed GTK4 client: categories/search, shared resource details and live inspection, confirmed desktop start/stop, graphics status/OpenGL/GLES/Vulkan verification and Native backend selection, preview-confirmed managed SSH 8023 lifecycle, monitoring policy, Cron saved-job list, and recovery history. | Does not expose PRoot app/session actions, Cron mutation/execution history, timezone configuration, boot, backup/restore, or SSH deploy/rollback. Native GTK visual/manual acceptance remains open. |

## Launcher and mobile verification note — 2026-10-19

Ternuxx-owned PRoot launch wrappers and generated desktop entries now dispatch through the supported checkout tx executable. Existing user-modified entries classified as conflicts are not overwritten. Current menu source attribution for all reported (PRoot) labels and actual application-window creation remain unverified. TUI action labels come from catalog-supported operations and only name workflows implemented by the TUI. Web mobile CSS and handler assertions are unit-tested; no rendered viewport measurements are available. See [dated evidence](../evidence/2026-10-19-launcher-tui-web-followup.md).

## Cross-interface action and test coverage

| Resource/action | CLI / shared API | TUI | Web | Native GTK | Authorization/provider and tests | Limitation |
|---|---|---|---|---|---|---|
| CPU / GPU / NPU qualification | tx doctor / doctor.report | Resource inspection | Read-only diagnostics if catalog/API scope permits | Dedicated CPU / GPU / NPU qualification resource runs bounded read-only renderer probes | diagnostics.read; tests/test_doctor_report.py, tests/test_management_desktop_bridge.py, tests/test_management_catalog.py | CPU is baseline; Native GTK startup logged VK_ERROR_INCOMPATIBLE_DRIVER; live Debian PRoot :1 reports Zink/Turnip Adreno 825 with accelerated GL and authenticated Native PulseAudio; NPU runtime/workload is unverified; no inference workload integration is implemented |
| PRoot graphics backend handoff | `tx db --backend zink|virgl`; `tx virgl status/start/stop` | n/a | n/a | n/a | Native service is identity-checked; launch handoff tests cover VirGL and unchanged Zink default | CPU remains baseline; current Debian PRoot Zink/Turnip evidence is separate; Native VirGL PID 21034 is running on :1, but Android procfs restrictions block client-aware stop and no guest VirGL renderer/workload is qualified; NPU workload remains unverified |
| PRoot named-app launch | tx mng app / proot.app.launch | Guided launch on the verified Native Ternuxx display | Unavailable | Unavailable | applications.launch; test_proot_shortcuts.py, test_terminal_ui.py | Live Thunar menu Exec path starts a visible window; 35 guest desktop entries are indexed into Native PRoot Apps. The agent did not click the GUI menu; owner visual category check remains. |
| Native desktop start/stop | tx start/stop / desktop.start, desktop.stop | Guided confirmation | Authorized HTTP mutation with confirmation | Typed bridge confirmation | desktop.manage; desktop lifecycle, HTTP runtime, TUI, GTK bridge suites | No lifecycle action was applied during this increment. |
| Managed SSH 8023 start/stop | tx ssh / ssh.service.start, ssh.service.stop | Preview, impact and plan confirmation | Dedicated scoped preview/apply | Typed bridge preview/apply | ssh.managed.lifecycle; HTTP runtime, management service, TUI and GTK bridge suites | 8023 inspected live; no start/stop apply. |
| GUI Activity/focus policy | tx gui monitor / desktop.monitor.status, desktop.monitor.configure | Guided policy form | Authenticated policy form | Typed policy form | desktop.monitor.manage; GUI monitoring, HTTP runtime, TUI and GTK bridge suites | Live policy remains disabled; no Activity/focus check. |
| Recovery operation history | tx recovery / recovery.status | H history + v details | Read-only resource action | Typed history action | diagnostics.read; recovery, HTTP runtime, TUI and GTK bridge suites | Service log-file browsing and progress tracking are unavailable. |
| Cron job registry and scheduler runtime | tx mng cron status/start/stop/jobs/executions; explicit lease-guarded daemon and typed dispatch | Status and saved-job list only | Authenticated status/list reads only; cron.manage and cron.scheduler.manage not granted | Status inspection and saved-job list only | cron.manage/cron.scheduler.manage for mutations; diagnostics.read for reads; Cron registry, ledger, scheduler runtime tests | Scheduler runtime is explicitly started, not boot-installed; retry/cancel/recovery delivery policies remain unqualified; Android packed tzdata 2025a observed |
| Official Termux:Boot Cron integration | tx mng boot cron status/validate/preview/enable/disable; exact-plan opt-in create-only script manager | Read-only catalog/status; no mutation flow | Read-only only; boot.manage is not granted | Read-only catalog/status; no mutation flow | boot.manage for writes, diagnostics.read for inspect; `tests/test_termux_boot_cron.py` and safe-script runtime test | Actual device boot delivery unverified; no live script enabled; requires owner reboot qualification |
| Native timezone preference | tx mng timezone status/list/set; shared typed operations | Catalog/status only | Status/list read; mutation transport disabled | Catalog/status only | timezone.manage for set; diagnostics.read for status/list; `tests/test_timezone_support.py` | No Web/TUI/GTK configuration form; optional IP suggestion is not implemented |
| Web mobile layout and handlers | Shared authenticated HTTP API | n/a | Mobile CSS + existing handlers | n/a | test_management_http_runtime.py structural viewport/handler assertions | No browser engine available; no rendered viewport/overflow measurement. |

## Per-operation exposure

`CLI area` is the command family found in help/source. `tx mng` is canonical; `tx management` is deprecated with a warning. TUI/Web/Native entries name only the guided actions actually exposed. Resource catalog entries may list supported operations that a client does not yet offer as an action.

| Operation | Capability | Kind | CLI area | TUI | Web | Native GUI |
|---|---|---|---|---|---|---|
| backup.create | state.backup | mutate | tx backup | not exposed as a guided action | not authorized | none |
| backup.inspect | diagnostics.read | read | tx backup | not exposed as a guided action | catalog details | none |
| backup.list | diagnostics.read | read | tx backup | fixed view | catalog details | none |
| boot.disable | boot.manage | mutate | tx boot | not exposed as a guided action | not authorized | none |
| boot.enable | boot.manage | mutate | tx boot | not exposed as a guided action | not authorized | none |
| boot.profile.preview | diagnostics.read | read | tx boot | not exposed as a guided action | catalog details | none |
| boot.profile.status | diagnostics.read | read | tx boot | not exposed as a guided action | catalog details | none |
| boot.cron.status | diagnostics.read | read | tx mng boot cron status | no guided action | not granted | catalog/status | test_termux_boot_cron.py | App/script/runtime states are distinct; boot delivery unverified |
| boot.cron.validate | diagnostics.read | read | tx mng boot cron validate | not exposed | not granted | catalog/status | test_termux_boot_cron.py | Does not execute script or prove reboot delivery |
| boot.cron.preview | diagnostics.read | read | tx mng boot cron preview enable|disable | not exposed | not granted | catalog/status | test_termux_boot_cron.py | Read-only exact change plan |
| boot.cron.enable | boot.manage | mutate | tx mng boot cron enable --yes --plan-id ID | not exposed | not authorized | none | test_termux_boot_cron.py | Creates only 20-ternuxx-cron after confirmed package and exact-plan confirmation |
| boot.cron.disable | boot.manage | mutate | tx mng boot cron disable --yes --plan-id ID | not exposed | not authorized | none | test_termux_boot_cron.py | Removes only exact verified owned script |
| boot.status | diagnostics.read | read | tx boot | not exposed as a guided action | catalog details | none |
| continuity.prepare | continuity.manage | mutate | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| continuity.prepare-reboot-test | continuity.manage | mutate | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| continuity.resume-info | continuity.read | read | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| continuity.status | continuity.read | read | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| continuity.verify | continuity.manage | mutate | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| continuity.verify-reboot-test | continuity.manage | mutate | tx checkpoint / tx reboot | not exposed as a guided action | not authorized | none |
| desktop.monitor.configure | desktop.monitor.manage | mutate | tx gui monitor | Guided policy form | Policy form | GTK policy form |
| desktop.monitor.status | diagnostics.read | read | tx gui monitor | Resource status | Resource policy/status | GTK policy/status |
| desktop.restart | desktop.manage | mutate | tx start/stop/restart/status | not exposed as a guided action | Confirmed API action | not exposed |
| desktop.start | desktop.manage | mutate | tx start/stop/restart/status | Guided + confirm | Confirmed API action | Confirmed GTK action |
| desktop.status | diagnostics.read | read | tx start/stop/restart/status | Resource status | Resource status | GTK live inspect |
| desktop.stop | desktop.manage | mutate | tx start/stop/restart/status | Guided + confirm | Confirmed API action | Confirmed GTK action |
| doctor.report | diagnostics.read | read | tx doctor | fixed view | visible read button | Native health + CPU/GPU/NPU qualification resources |
| management.catalog | diagnostics.read | read | tx mng catalog/doctor/app/shortcuts | 13-category browser | 13-category browser | 13-category browser |
| agent.hermes.status | diagnostics.read | read | tx mng hermes status | catalog discovery only | catalog discovery only | catalog discovery only | Hermes scheduler status is read-only; task content/execution and scheduler bridge are unsupported |
| cron.status | diagnostics.read | read | tx mng cron status | Resource status | Resource status | Resource status | Ledger core exists; resident scheduler is not installed |
| cron.jobs.list/show/validate/next_runs | diagnostics.read | read/preview | tx mng cron jobs | Saved-job list only | Saved-job list only | Saved-job list only | Schedule preview uses shared engine; no execution |
| cron.jobs.create/update/remove | cron.manage | mutate configuration | tx mng cron jobs | unavailable | not authorized | unavailable | Web session intentionally excludes cron.manage |\n| cron.executions.list/show | diagnostics.read | read history | tx mng cron executions list/show | not exposed | not exposed | not exposed | API/CLI read only; bounded private ledger; no production scheduler delivery |
| native.ssh.status | diagnostics.read | read | tx ssh inspect | fixed view | catalog details | none |
| proot.profiles.list/show | diagnostics.read | read | tx mng proot profiles list|show | Inventory only | Catalog/API read only | Catalog/API read only | tests/test_proot_sessions.py | Fixed profiles: headless probe and foreground Debian login; interactive profile not live-launched |
| proot.start.preview | diagnostics.read | preview | tx mng proot start --profile ID | Preview only | Not exposed | Not exposed | tests/test_proot_sessions.py, test_management_service.py | Plan binds profile, rootfs and launcher identity |
| proot.start | proot.session.manage | mutate | tx mng proot start --profile ID --yes --plan-id ID | Not exposed | Not authorized | Not exposed | tests/test_proot_sessions.py | Probe live-tested; interactive attempts failed closed on cwd/guest UID identity checks |
| proot.stop.preview | diagnostics.read | preview | tx mng proot stop SESSION_ID | Preview only | Not exposed | Not exposed | tests/test_proot_sessions.py | Unknown ownership blocks a plan |
| proot.stop | proot.session.manage | mutate | tx mng proot stop SESSION_ID --yes --plan-id ID | Not exposed | Not authorized | Not exposed | tests/test_proot_sessions.py | Exact recorded session group only; no force signal/global cleanup |
| proot.recovery.inspect | diagnostics.read | read | tx mng proot recover SESSION_ID | Not exposed | Not exposed | Not exposed | tests/test_proot_sessions.py | Inspection only; never signals or repairs an ambiguous record |
| proot.recovery.reconcile.preview / proot.recovery.reconcile | diagnostics.read / proot.session.manage | preview / mutate | tx mng proot reconcile SESSION_ID [--yes --plan-id ID] | Not exposed | Not authorized | Not exposed | tests/test_proot_sessions.py | Can mark exited only on absent/reused-PID evidence; no signal |
| proot.app.launch | applications.launch | mutate | tx proot / tx mng app\|shortcuts | Guided PRoot launcher | not authorized | not exposed |
| proot.guest.verify | guest.diagnostics.read | read | tx proot / tx mng app\|shortcuts | not exposed as a guided action | not authorized | none |
| proot.shortcuts.apply | applications.manage | mutate | tx proot / tx mng app\|shortcuts | not exposed as a guided action | not authorized | none |
| proot.shortcuts.sync | applications.manage | mutate | tx mng papps sync; Native desktop startup | not exposed as a guided action | not exposed | test_proot_shortcuts.py |
| proot.shortcuts.list | diagnostics.read | read | tx proot / tx mng app\|shortcuts | fixed view | visible read button | none |
| proot.shortcuts.preview | diagnostics.read | read | tx proot / tx mng app\|shortcuts | not exposed as a guided action | catalog details | none |
| proot.status | diagnostics.read | read | tx proot / tx mng app\|shortcuts | fixed view | visible read button | none |
| recovery.inspect | diagnostics.read | read | tx recovery | not exposed as a guided action | catalog details | none |
| recovery.resolve | recovery.manage | mutate | tx recovery | not exposed as a guided action | not authorized | none |
| recovery.rollback.apply | recovery.manage | mutate | tx recovery | not exposed as a guided action | not authorized | none |
| recovery.rollback.preview | diagnostics.read | read | tx recovery | not exposed as a guided action | catalog details | none |
| recovery.status | diagnostics.read | read | tx recovery | `h` history + `v` details | View operation history | View operation history |
| remote.access.preview | remote_policy.read | read | tx remote access | not exposed as a guided action | not authorized | none |
| restore.apply | state.restore | mutate | tx restore | not exposed as a guided action | not authorized | none |
| restore.preview | diagnostics.read | read | tx restore | not exposed as a guided action | catalog details | none |
| ssh.inspect | diagnostics.read | read | tx ssh | Resource status | Resource status | GTK live inspect |
| ssh.service.deploy | services.manage | mutate | tx ssh | not exposed as a guided action | not authorized | none |
| ssh.service.deploy.rollback.apply | services.manage | mutate | tx ssh | not exposed as a guided action | not authorized | none |
| ssh.service.deploy.rollback.preview | diagnostics.read | read | tx ssh | not exposed as a guided action | catalog details | none |
| ssh.service.start | ssh.managed.lifecycle | mutate | tx ssh | Guided + impact confirm (8023 only) | Preview + confirmation (8023 only) | Preview + confirmation (8023 only) |
| ssh.service.stop | ssh.managed.lifecycle | mutate | tx ssh | Guided + impact confirm (8023 only) | Preview + confirmation (8023 only) | Preview + confirmation (8023 only) |
| wakelock.acquire | wakelock.manage | mutate | tx wakelock | not exposed as a guided action | not authorized | none |
| wakelock.release | wakelock.manage | mutate | tx wakelock | not exposed as a guided action | not authorized | none |
| wakelock.status | diagnostics.read | read | tx wakelock | not exposed as a guided action | catalog details | none |

## Domain maturity and planned work

Hermes is an optional local agent provider with a read-only scheduler-status adapter. It is not linked to Ternuxx scheduling; task listing, execution, cancellation, scheduler configuration, and ownership transfer remain unavailable.


| Domain | Catalog status | Planned/unavailable examples |
|---|---|---|
| native-desktop | implemented | none listed |
| sshd-servers | implemented | none listed |
| proot-runtime | partial-installed-debian-first | guest.adapt, guest.install, guest.uninstall, guest.distro.select, desktop.install, desktop.select |
| doctor-diagnostics | implemented | none listed |
| autoboot-background | implemented | none listed |
| backup-recovery-continuity | implemented | none listed |
| addons-plugins-tools | catalog-and-cli-tools-partial | addon.list, addon.preview, addon.apply, plugin.list, plugin.preview, plugin.apply, tool.catalog |
| api-backends | planned-disabled | backend.list, backend.health, backend.select, backend.credentials.reference |

## Prioritized implementation sequence

1. **Catalog and interface foundation — in progress:** catalog v2 is the source for 13-category navigation, resource search/status filtering, and capability maturity across CLI/TUI/Web/GTK. The GTK4 app is installed and hash-recorded. Tests cover category selection, typed bridge actions, Web scope/CSRF/idempotency, interval validation, and TUI guidance. Manual GTK visual qualification remains open.
2. **Existing-resource parity — in progress:** Web/TUI/GTK now expose preview-first start/stop for fixed SSH 8023 with a dedicated scope; port 8022 remains read-only. Next add reviewed workflows for boot profiles, PRoot shortcut add/remove, backups/recovery, service service logs and operation tracking. Do not offer an operation where API/auth/preview support is missing.
3. **Native reliability gates:** GUI/audio/SSH/Shizuku/boot checks, installed/source comparison, live readiness, and existing PRoot compatibility remain under P3/P4 gates.
4. Later adapters: general server/application deployment, expanded PRoot workload management, software inventory/install, AI runtimes/models/providers, networking integrations, and provider extensions.

## Guardrails

- Discovery is not ownership; preserve external/unverified processes. Distinguish implemented, partial, external, unverified, unavailable, and planned.
- Port 8022 remains manually managed and outside Ternuxx lifecycle. Port 8023 is the existing managed SSH service.
- Web/GUI operations require capability scopes, typed requests, preview/confirmation for disruptive actions, and audit/progress; never expose generic shell execution.
- Resource unregister is distinct from software uninstall and data deletion; preserve data by default and show dependant impact.
- Catalog discovery does not authorize boot/reboot, Activity polling, Shizuku invocation, audio changes, or PRoot process termination.

## Current independent-runtime boundary

| Capability | CLI/API | TUI | Web | GTK | Status / limitation |
|---|---|---|---|---|---|
| Installed Debian inventory | `proot.status` read-only | status view | status view | catalog only | Implemented; distro ownership unverified |
| Named PRoot application launch | `proot.app.launch` | guided launch | unavailable | unavailable | Partial; selected display handoff only, not a guest lifecycle manager |
| Ternuxx-owned Debian profile start/stop | tx mng proot start|stop; shared API, exact preview/confirmation | unavailable | unavailable | unavailable | Partial; disposable headless and real TTY login/job control tested; GUI and detach/reattach remain unqualified |
| Web bootstrap clipboard | `tx web` clipboard handoff | n/a | authenticated form | n/a | Source/fixture implemented; live clipboard copy not verified |
| Tagline / portfolio branding | n/a | compact header | footer link | footer link | Source implemented; GTK binary deployment must match source identity |


## Scheduler and PRoot lifecycle update - 2026-10-20

| Capability | CLI/API | TUI | Web | GTK | Evidence / status |
|---|---|---|---|---|---|
| Scheduler singleton lease and explicit event dispatch | Internal isolated core only; no public lifecycle route | unavailable | unavailable | unavailable | tests/test_cron_scheduler.py; lease/claim and harmless registered subprocess tested in temporary state; no resident scheduler |
| Device boot and scheduler recovery delivery | unqualified | unavailable | unavailable | unavailable | Trigger policy fields remain persisted; no Termux boot delivery or recovery event source enabled |
| Ternuxx-owned PRoot sessions | read-only inventory only; no start/stop | unavailable | unavailable | unavailable | Active processes remain unverified ownership; no session was entered or controlled |


### 2026-10-19 Cron runtime and PRoot session increment

| Capability | CLI/API | TUI/Web/GTK | Provider status | Evidence / limitation |
|---|---|---|---|---|
| Cron scheduler status, explicit start/confirmed stop | tx mng cron status/start/stop; shared API; start/stop require cron.scheduler.manage over authenticated transport | UI mutation controls remain unavailable | Implemented source; isolated daemon runtime tested | Daemon is not boot-installed or production enabled |
| Cron due dispatch | Shared daemon uses v1 registry, stable event claims, timezone engine and typed action registry | No interface-specific scheduler | Isolated runtime tested with scheduler.self_test | Only skip, one attempt and skip_overlap; other policies rejected |
| Cron device-boot/recovery triggers | Persisted fields/status only | Read-only | Unqualified | No Termux:Boot delivery installed or enabled |
| Ternuxx PRoot session inventory | tx mng proot status, sessions list/show; shared API | Read-only view through shared API only | Implemented | Registry contains only positively verified Ternuxx sessions |
| Ternuxx PRoot start/stop | Test-only isolated-probe manager module; no general CLI lifecycle exposed | Unavailable | Real harmless PRoot probe started/stopped in isolated test state | Existing rootfs reused with --minimal; workstation and GUI session lifecycle remain unqualified |


### 2026-10-20 - Reusable PRoot profiles and ownership-checked lifecycle

The fixed profile inventory includes a bounded headless diagnostic session and a foreground Debian login profile using the existing db guest/user/shared-tmp selection. Shared API operations cover profile inventory, start/stop preview and confirmed CLI lifecycle, session details, and read-only recovery inspection. The private schema-v3 registry records rootfs/launcher device+inode, profile, process-start identity, session/group leader and a per-session marker. Existing unmanaged sessions are not adopted. A live foreground login passed ownership verification and exited cleanly; detach/reattach and stop of a still-running session remain unqualified. No automatic cleanup or forced signal is available.

A disposable PRoot probe was started and stopped with an isolated temporary registry using exact identity checks. An earlier probe whose marker was not visible failed closed and remains as an unverified record; it expired naturally and was not signaled or deleted. See [2026-10-20 PRoot lifecycle evidence](../evidence/2026-10-20-proot-lifecycle.md). Cron remained stopped; Termux:Boot remained unconfigured. GUI/workstation lifecycle remains unqualified.


### Live accelerator and audio qualification — 2026-10-20

| Resource/context | Current observation | Qualification boundary |
|---|---|---|
| Native CPU | Native CPU baseline; inference integration not implemented | Baseline only, no model/runtime workload claim |
| Native GUI graphics | Current Native `:1` XFCE session loads the explicitly enabled extracted Mesa KGSL candidate; Adreno 825 / Freedreno reports `Accelerated: yes` | Candidate selection is saved in private Ternuxx state and applied on desktop start; local experimental candidate only, no inference or general application qualification |
| Native OpenGL ES | A standalone candidate EGL/GLES pbuffer workload completed; shared verification reports unavailable | No GLES workload runner is wired into shared management; no presented UI rate or broad app claim |
| Native Vulkan | Turnip enumerates Adreno 825 in the current candidate environment | Enumeration only; no Vulkan draw has been tested |
| Debian OpenGL ES | Unavailable through the current guest verifier | Guest verification covers configured OpenGL/Zink only |
| Debian PRoot GPU | Isolated read-only verify on `:1` reports Zink/Vulkan 1.4, Adreno 825, `MESA_TURNIP`; X11 reachable | Renderer evidence for this guest process/display, not a general workload benchmark; guest profile ownership remains unverified |
| VirGL | Native Ternuxx vtest server PID 21034 is running on :1; the earlier read-only renderer request observed Zink/Turnip and returned a mismatch | Server startup is live-verified, but no guest VirGL renderer/workload is qualified; Android socket ownership restrictions prevent verified stop; `tx proot verify --backend virgl` remains an expectation, while `tx db --backend virgl` activates the host handoff |
| NPU | Native GUI reports runtime/delegate unverified | Experimental only; no package/runtime/model/workload installed or run |
| Audio | Native Ternuxx cookie-auth endpoint is ready; isolated Debian PRoot client status passes on `:1` | Protocol path verified; physical audibility and UI lifecycle controls remain unqualified |

Evidence: [2026-10-20 qualification execution record](../evidence/2026-10-20-workstation-qualification-execution.md). `tx proot verify` read-only status enters the guest with a narrowly bound cookie file; it does not bind HOME, change guest state, or control host services.


## Current accelerator/runtime qualification — 2026-10-20

Ternuxx Native Termux remains the CPU and service authority. A direct tx db guest command on Debian :1 verified Zink/Turnip Adreno 825 with accelerated GL and the authenticated Native PulseAudio endpoint. Android ART/classpath/storage host variables were absent in the guest, while explicit display/audio/Zink settings remained. This is process/workload-renderer evidence, not a general benchmark. The Native GTK management process starts on :1 but emitted VK_ERROR_INCOMPATIBLE_DRIVER; its Android-visible window and human usability are unverified. The Native VirGL server is running, but it was not selected by the PRoot renderer verified in this check. NPU device/runtime/workload remain unverified.
## Acceleration qualification update — direct Native check (2026-10-20)

Native Doctor reports candidate NPU vendor-library visibility, FastRPC-node visibility, and known runtime-CLI availability separately; the recorded device check found no visible candidate device node or checked runtime CLI, so NPU execution remains unverified. Live Native `:1` status reports Adreno 825 with `Accelerated: yes`; bounded GL verification rendered successfully. Stock Mesa reports llvmpipe. Debian PRoot separately verified Zink/Turnip Adreno 825 and authenticated Native PulseAudio reachability. CPU remains baseline without an inference integration. Native VirGL has started, but no VirGL guest workload is verified and stop cannot prove client absence on this Android procfs. None of these renderer/probe checks qualifies an inference workload; see the dated execution evidence.


### Native host / Debian workload split — 2026-10-20 direct recheck

Native Termux owns the `:1` display and authenticated PulseAudio endpoint. Debian PRoot uses its own glibc Mesa/Turnip userspace against the existing host device/display handoff. Direct Zink verification passed. Native candidate-backed GL rendering also passed in a managed session; current active renderer and Native Vulkan drawing remain unverified. `tx proot verify --backend virgl` only checks for a VirGL renderer; `tx db --backend virgl` selects the Native-host service handoff. The Native vtest server has started, but guest VirGL workload remains unverified. CPU remains baseline without inference integration; NPU execution remains unverified. No host Bionic libraries are copied into Debian. Guest package/profile cleanup remains gated on a consumer and rollback inventory.
