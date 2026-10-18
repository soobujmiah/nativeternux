# P3 exit-gate audit — 2026-10-18

- Phase: P3, still in progress; this is an evidence audit, not a completion record.
- Source of criteria: P3 exit gate in [`docs/ROADMAP.md`](../ROADMAP.md).
- Runtime snapshot: [latest native read-only P3 gate snapshot](2026-10-18-p3-current-readonly-gate-latest.json); earlier read-only rechecks: [00:35 UTC](2026-10-18-p3-current-readonly-gate-recheck.json) (with the earlier full snapshot at [00:09 UTC](2026-10-18-p3-current-readonly-gate-snapshot.json)), with [boot-profile preview recheck](2026-10-18-p3-boot-profile-preview-recheck.json).
- Test baseline: the latest full native Termux suite passed 218/218 at 05:36 UTC. Fresh focused reruns passed PRoot diagnostics 20/20, management service 24/24, package plan 11/11, desktop lifecycle fixture 8/8, reboot recovery 12/12, and runtime diagnostics 8/8. These are repository tests; device state was checked separately and no package/lifecycle/reboot mutation occurred during these reruns.

## Criteria and evidence

| # | Roadmap exit criterion | Current result | Evidence and remaining work |
|---|---|---|---|
| 1 | Doctor is read-only and accurately reports missing, failed, unknown, and conflicting states. | **Source/fixture pass; device qualification partial.** | Fresh 05:43 UTC Doctor check reports 14 pass / 14 info / 1 warning / 0 errors and `read_only=true`. The warning correctly reports native SSH 8022 wildcard/password auth while owner and external reachability are unknown. GUI visibility and Android background policy remain unknown. See [Doctor/remote recheck](2026-10-18-p3-doctor-remote-recheck-0544.json) and [SSH recheck](2026-10-18-p3-ssh-current-session-recheck.json). |
| 2 | Missing optional dependencies produce an explicit lower-capability fallback, never a silent provider switch or success claim. | **Pass for implemented source behavior.** | The dependency fallback matrix and `test_proot_and_hybrid_fail_closed_without_fallback` show PRoot/hybrid stay blocked without their ownership/workload adapters; no provider switch is reported. These adapters remain unimplemented. |
| 3 | Stale PID, unexpected process exit, interrupted operation, corrupt backup, path traversal, and external display conflict cases fail closed. | **Source/fixture pass.** | Existing fixture coverage exercises process identity, journal-specific recovery, corrupt/path-traversal inputs, ambiguous state, and display conflicts. The latest full suite passed 220/220; fresh targeted reboot-observer/runtime-diagnostics tests passed 20/20, and the boot diagnostic-specific suite passed 10/10 after the receiver-state implementation. See [latest source implementation test record](2026-10-18-p3-ternux-profile-source-implementation-0536.json) and [fresh observer regression](2026-10-18-p3-reboot-observer-regression-recheck-0555.json). |
| 4 | Until the P4/P8 adapters exist, PRoot/hybrid requests fail closed without fallback or a second desktop; preserve a reviewed ownership contract. | **P3 source pass; provider operation deferred.** | Ternuxx exposes inventory/diagnostics only and marks guest ownership unverified. No Ternuxx-owned PRoot launch or hybrid route is claimed. P4 owns Ternux parity/start adapter; P8 owns workload routing. See [provider-contract evidence](2026-10-18-p3-ternux-provider-contract-recheck-0821.json). |
| 5 | Verify native cold boot/retry, CLI service, X server, Android GUI activity request, background restrictions, and manual-open fallback on an explicitly authorized/disposable profile. | **Partial / open.** | RB06 remains `verified_reboot_service_unqualified` / `NOT_READY`. A later native Termux `am` wrapper request was accepted and ADB confirmed MainActivity resumed; the stale :1 pair was then recovered and native Ternuxx returned to :1. The owner confirmed PRoot `xmessage` and Thunar windows visible on :1. This proves app-level display sharing, while `gui_visible` telemetry, cold-boot startup, manual-open fallback, and Android background restrictions remain unqualified. Boot profile stays default CLI-only. PRoot boot follows P4; hybrid follows P8. See [RB06 postboot review](2026-10-18-p3-rb06-postboot-review.json), [activity retry](2026-10-18-p3-native-termux-am-wrapper-retry.json), and [display recovery](2026-10-18-p3-native-display-1-stale-recovery.json). |
| 6 | Distinguish Shizuku upstream/custom provider, observe package/version, `rish`, process-name signal, and keep Binder permission/watchdog health unknown unless directly observable; keep ADB Wi-Fi listener disabled by default. | **Read-only diagnostic slice implemented; service/provider qualification remains open.** | Doctor now adds bounded `pidof shizuku_server` signal without returning PIDs or treating no match as stopped. Current check: package present, versionCode 1318, `rish` not found, process name not observed (visibility unknown), loopback ADB 5037 not observed; signer, Binder, granted permission, and watchdog remain unknown. No app/service/settings action. See [Shizuku process-signal evidence](2026-10-18-p3-shizuku-process-signal.json). |
| 7 | Recovery previews list every affected path; restore/rollback touch only disposable Ternuxx fixtures and preserve the existing Ternux setup. | **Source/fixture pass; no live restore performed.** | Recovery handlers use exact preview IDs and list journal paths; fixtures cover exact paths, stale previews, corrupt archives, ambiguous state, and rollback ancestry. No restore was run against device state, the Ternux rootfs, or launcher. |

## P3 disposition

P3 is **not complete**. Gates 1–3 and 7 pass for the cited source/fixture evidence; gate 2 confirms fail-closed behavior where adapters are absent. Gate 4 is an ownership/fallback contract only: actual existing-Ternux parity and PRoot startup are P4, while hybrid workload routing is P8. Gate 5 has app-level X11 visibility confirmation and an accepted Android activity request, but RB06 is still `NOT_READY`; cold boot, telemetry, and background behavior remain open. Gate 6 has a read-only process-name signal; provider identity, Binder permission, and watchdog health remain unverified. SSH 8022 is configured wildcard/password-enabled, but listener ownership and external reachability remain unknown; remote access stays disabled. P4 remains planned behind P3 ownership acceptance. This audit pass did not launch a GUI or change boot settings.


- Fresh continuation check recorded at 2026-10-18 01:12:27 UTC: full suite 205/205 (32.576 seconds), repository-knowledge verification 0 findings, generated phase docs refreshed, and `git diff --check` passed. This does not alter the open gate disposition above. See [structured test record](2026-10-18-p3-continuation-tests.json).


- Fresh native read-only recheck at 2026-10-18 01:14:03 UTC is recorded in [latest P3 gate snapshot](2026-10-18-p3-current-readonly-gate-latest.json). It reconfirms the open device gates; no lifecycle or profile mutation was run.


- Latest bounded PRoot diagnostic at 2026-10-18 01:16:27 UTC again returned partial: X11 and Zink/Turnip were reachable, guest PulseAudio was unavailable, native process-status remained stopped, and Ternux profile ownership was unverified. The audio gate remains open; the test ran no sound stream or lifecycle action. See [time-series audio/renderer evidence](2026-10-18-p3-ternux-audio-repeatability.json).


- At 01:16:53 UTC, native PulseAudio info and loopback TCP were reachable despite the immediately prior guest failure; the following guest verification completed by 01:17:08 UTC. This confirms time-variable control connectivity only. Audible output and stable bridge operation remain open; see [timestamped audio evidence](2026-10-18-p3-ternux-audio-repeatability.json).


- The next three-run read-only sample (01:18:02–01:18:09 UTC) returned one guest audio failure followed by two passes, with X11/Zink/Turnip in all runs and native pactl/TCP checks succeeding after each. This makes the time-variability repeatable but does not prove audible playback or exact endpoint state at failure. Keep P3 gate 4 open; evidence: [per-run audio sample](2026-10-18-p3-ternux-audio-repeatability.json).


- A concurrent native/guest sample at 01:19:25–01:19:32 UTC passed 3/3 guest checks and 15/15 native loopback probes, with `pactl info` reachable before and after each guest check. This is a short control-protocol success window; prior failures remain and audible playback/long-term reliability are still unverified. Gate 4 stays open. See [concurrent audio evidence](2026-10-18-p3-ternux-audio-repeatability.json).


- Latest typed endpoint verification at 01:22:36 UTC returned complete: native `pactl info` was available, guest audio/X11 were reachable, and Zink/Turnip was selected even though native Ternux process status said PulseAudio stopped. The new endpoint field correctly preserves both signals; audible output and long-term reliability remain open. See [implementation/test/live evidence](2026-10-18-p3-pactl-endpoint-status.json).


- Fresh continuation check recorded at 2026-10-18 01:25:38 UTC: full native Termux suite passed 207/207 in 33.461 seconds, including the new typed PulseAudio endpoint cases; repository-knowledge verification found 0 issues, Python compilation and CLI-help contract passed, generated phase docs refreshed, and `git diff --check` passed. This is source/fixture verification only. No device lifecycle, package, service, or playback action ran, and P3 gates 4–6 remain open/partial. See [structured continuation test evidence](2026-10-18-p3-continuation-tests.json).

- Second live endpoint recheck at 01:26:38 UTC again returned `complete`: native pactl endpoint available (`pulseaudio`, `OpenSL_ES_sink`), guest audio/X11 reachable, and Zink/Turnip visible; Ternux process-name status remains stopped and profile ownership unverified. No packages, services, guest files, lifecycle, or audio stream were changed. This repeats endpoint/control reachability only; audibility and sustained reliability remain open. Updated [typed endpoint evidence](2026-10-18-p3-pactl-endpoint-status.json).


- Fresh read-only Doctor recheck at 01:34 UTC returned 14 pass / 14 info / 1 warning / 0 errors, with `read_only=true`; the SSH wildcard/password policy warning remains and listener ownership/external reachability are unknown. Redacted structured device evidence is [here](2026-10-18-p3-current-doctor-recheck.json). No service or configuration action ran; this updates gate 1 observation without closing device-only gates.

- At 01:36 UTC, a read-only SSH inspection verified the managed `ternuxx-sshd` Runit definition and its loopback-only `127.0.0.1:8023` config/banner. The separate native config reports wildcard `:8022` with password auth enabled. Procfs socket enumeration was permission-denied, so neither actual listener ownership nor external reachability was established. No configuration/service change or package install was run. See [SSH ownership recheck](2026-10-18-p3-ssh-listener-ownership-recheck.json).

- P4 discovery advanced with the installed Ternux user/backend/display configuration and same-input display probes. The configured `:0` path returned partial, while the separate `:1` path returned complete Zink/Turnip. This narrows the live integration discrepancy but does not prove profile ownership or satisfy P3 gate 4; no desktop lifecycle was invoked. See [P4 profile/display evidence](2026-10-18-p4-ternux-profile-discovery-recheck.json).

- Post-comparison check at 01:46:47 UTC confirms native Ternuxx desktop still running on `:1`; PRoot inventory remains read-only and did not enter Debian. No desktop/session/lifecycle/package changes occurred during the `:0`/`:1` diagnostic comparison.


- Read-only boot-profile recheck at 2026-10-18 02:00 UTC: configured profile remains the default `cli-only`; the native startup command preview is ready, while PRoot and hybrid previews fail closed on the missing Ternux ownership/workload-routing adapters. Termux:Boot is installed and its script directory is present (two regular scripts), but its command is unavailable and startup delivery policy remains unknown. No script contents were read and no profile or boot file was changed. This narrows gate 5 to delivery/background/visible-GUI evidence and PRoot/hybrid adapters; see [boot-profile preview evidence](2026-10-18-p3-boot-profile-preview-0200.json).


- Fresh display ownership clarification at 02:02 UTC: Ternux reported `running`/X11 present; the visible `termux-x11` process was on `:1` and its transient PID matched Ternuxx Doctor's verified X11 process, while no `:0` process was observed. The current checked-out Ternux source uses a name-presence check, but its identity with the installed script was not established. This means the observed Ternux status cannot qualify its configured display. It does not prove that no hidden `:0` server exists or establish guest rootfs ownership. P3 gate 4 remains open; see [X11 process correlation evidence](2026-10-18-p3-ternux-x11-presence-correlation-0202.json).


- At 02:06 UTC, guest verification gained a bounded read-only visible-display process comparison for failed X11 handoffs. The PRoot/management focus suite passed 39/39 and the full local PRoot Debian fixture/unit suite passed 210/210 in 73.610 seconds. On-device `:0` remained partial and now explains that no matching Termux:X11 process was observed; `:1` remained complete with Zink/Turnip and audio control reachable. The check stores no PID/argv and does not claim ownership/absence. The full local PRoot Debian fixture/unit suite then passed 210/210; native device state was rechecked read-only afterward and remained on :1 with Debian inventory unentered/ownership-unverified. Evidence: [display-process diagnostic record](2026-10-18-p3-display-process-diagnostic-0206.json).

## 02:15 UTC follow-up

The earlier 205-test baseline above is retained as a dated snapshot. A later full `bash scripts/repo_test.sh` run in the attached native Termux checkout passed **210/210** during the 02:12 UTC continuation (see [latest display diagnostic evidence](2026-10-18-p3-display-process-diagnostic-0206.json) and [managed SSH boot-path evidence](2026-10-18-p3-managed-ssh-boot-static-inspection-0212.json)); the focused SSH diagnostics suite then passed **9/9** at 02:15 UTC.

The 02:15 native SSH recheck confirms the fixed Runit unit definition and config, running status, and loopback SSH banner on `127.0.0.1:8023`. Procfs listener enumeration is permission-denied. Available `lsof` and `netstat` commands did not attribute the endpoint to a process, so listener ownership remains **unknown** ([probe record](2026-10-18-p3-ssh-ownership-alternative-probes-0215.json)). The executable Termux:Boot service script references `ternuxx-sshd`, but cold-boot delivery remains unverified ([boot-path record](2026-10-18-p3-managed-ssh-boot-static-inspection-0212.json)). No service, boot, package, desktop, or PRoot changes were made.

P3 remains **in progress**. These follow-ups do not close the ownership, cold-boot, GUI visibility, guest audio, or PRoot/hybrid workload-routing gates. P4 remains planned until the P3 dependency and ownership contract are satisfied.

### 02:17 UTC private-access follow-up

Native CLI default policy remains disabled. A policy-only preview using synthetic opaque references returned `private_transport` / `unavailable`, with no active access, network probe, credential resolution, or reference-value emission. The focused remote policy and management suite passed **30/30**. No provider was selected, no adapter exists, and no external network was touched; off-home access remains an open feature gate. See [live recheck](2026-10-18-p3-private-access-live-recheck-0217.json).


### 02:19 UTC managed SSH boot-path correlation

The executable Termux:Boot service script references `ternuxx-sshd` and sources Termux `start-services.sh`, whose service-daemon uses `$PREFIX/var/service`; the managed service entry is present. Kernel `CLOCK_BOOTTIME` and runit status report the service began about 40 seconds after kernel boot. This is strong evidence consistent with the 8023 service starting during the current boot, but does not prove the Android boot receiver delivered this script; the CLI still reports startup policy unknown and no controlled reboot was performed. Loopback SSH health is good, while listener ownership remains unknown. The focused boot-profile/SSH diagnostics suites passed **21/21**. See [timing-correlation record](2026-10-18-p3-managed-ssh-current-boot-timing-0219.json). P3 stays open.


### 02:23 UTC diagnostic update

`ssh inspect` now returns a sanitized startup_timing object that compares the fixed Runit unit age with Linux CLOCK_BOOTTIME; it never stores the service PID and does not claim boot-script causation. Tests cover observed timing, stopped/unavailable/inconsistent status, and schema shape. On-device live result reports service start 41 seconds after kernel boot, with listener ownership still unknown. Focused SSH diagnostics passed **10/10**; full repository suite passed **211/211** in 33.367 seconds. Evidence: [live validation](2026-10-18-p3-ssh-startup-timing-live-0223.json). P3 remains open.


### 02:24 UTC Shizuku discovery update

Doctor now reports the installed Shizuku package versionCode and rish executable presence separately from server, signer/build identity, permission, and watchdog health. The live package metadata query returned versionCode 1318; `rish` is absent from PATH. These facts do not authenticate the build or prove Shizuku availability. Focused Doctor tests passed **21/21** and full suite **213/213** in 33.709 seconds. Evidence: [Shizuku metadata record](2026-10-18-p3-shizuku-package-metadata-0224.json). P3 gate 6 remains partial pending an Android-side or reviewed rish health/permission integration and bounded watchdog qualification.

### 02:31 UTC continuation

The full native Termux repository suite passed **213/213** in 33.491 seconds. The installed-Ternux profile discovery record confirms the private state file was a regular non-symlink owned by the Termux UID with mode 0600, and that its configured guest-user key matched the earlier explicit verifier input; the literal user value was not retained. The read-only CLI profile/status output does not expose that value. Therefore no new guest entry was attempted and no account was guessed. Existing profile evidence still supports the earlier :1/Zink/Turnip handoff, but it is not a new live renderer check. No Ternux lifecycle, PRoot rootfs, boot, package, or display state was changed. P3 remains in progress; see [continuation test and input record](2026-10-18-p3-continuation-0231.json).

The same 02:31 UTC live read-only snapshot reports Doctor at 14 pass / 14 info / 1 warning / 0 errors, managed Runit SSH `ternuxx-sshd` running on loopback `127.0.0.1:8023` with a banner and service start about 40 seconds after kernel boot. Process-to-listener attribution remains unavailable. The separately observed SSH configuration is wildcard-bound on port 8022 with password and keyboard-interactive authentication enabled; its listener owner is unknown, so this is recorded as an exposure requiring owner review and has not been changed. Debian remains installed with `guest_entered=false` and ownership unverified. See the expanded [continuation record](2026-10-18-p3-continuation-0231.json).

### 02:33 UTC P2 current-state recheck

The 77 packages in the recorded XFCE transaction were queried again with `dpkg-query`: **77/77** were installed at the recorded exact versions. The current install preview returned `already_installed` and `packages_changed=false`; it is a no-op because the transaction is already present. Desktop status remains running on `:1` with X11 and XFCE present, GUI visibility unknown, and audio owner external. Debian remains installed, unentered, and ownership-unverified. These checks are read-only; no packages, desktop processes, or PRoot state were changed. The historical pre-consent apt simulation is still unrecoverable and is not implied by this recheck. See [P2 current gate recheck](2026-10-18-p2-current-gate-recheck-0233.json).

### 02:35 UTC read-only Ternux guest handoff

Resolved the configured guest account only from Ternux's own protected `state` file (regular, non-symlink, Termux-owned, mode 0600); the account value was passed in memory and was neither printed nor saved. The bounded verifier completed for Debian on `:1`/Zink: X11 reachable, renderer `zink Vulkan 1.4 (Adreno 825, MESA_TURNIP)`, and PulseAudio control-protocol reachability. It invoked no guest write command and did not start/stop host lifecycle or services. Native Ternux status still says PulseAudio stopped, so control-path reachability is not service-health proof; audible playback was not tested. The installed Ternux CLI reports 1.4.0, but installed-vs-checkout source identity and guest ownership remain unverified. P3 gate 4 remains open because this diagnostic is not a Ternuxx-managed workload launch or hybrid router. See [guest handoff evidence](2026-10-18-p3-ternux-guest-handoff-0235.json).

### 05:36 UTC protected Ternux profile source for bounded verification

Added the --guest-user-from ternux-state option to the typed proot verify CLI path. It obtains the configured account from Ternux's own state file, requires an absolute state directory below Termux HOME, traverses it without following symlinks, verifies current-UID ownership/private directory modes and a regular mode-0600 state file, and accepts exactly one supported non-root account. The account is only held in memory for the existing fixed Ternux version/status probes and never appears in the diagnostic response or evidence. Explicit --guest-user USER remains supported.

The live device command completed on Debian :1/Zink with X11 reachable, Zink/Turnip on Adreno 825, and audio control-protocol reachable; it invoked no guest write command and started/stopped no service or desktop lifecycle. Focused tests passed 20/20 (PRoot diagnostics) and 24/24 (management service); the full suite passed 218/218 in the reported 2189.176 seconds. Python compilation, shell syntax checks, repo knowledge verification (0 findings), and git diff --check passed. This only improves bounded profile discovery; ownership-aware workload dispatch, GUI visibility/cold-boot evidence, and audible playback remain open, so P3 stays in progress. See [implementation and device evidence](2026-10-18-p3-ternux-profile-source-implementation-0536.json).

- 2026-10-18 05:40 UTC continuation: read-only native status still reports the `:1` desktop process state running; GUI visibility remains unknown. Debian inventory is present but guest was not entered and ownership remains unverified. The P2 package closure remains 77/77 exact versions. The fresh record does not close P3 GUI visibility, ownership, audio, cold-boot, or remote-access gates; no reboot or lifecycle action was performed. See [current P2/P3 session recheck](2026-10-18-p2-p3-current-session-recheck.json).

- 2026-10-18 05:41 UTC continuation: native `ssh inspect` confirms the managed 8023 Runit service is running, its source/installed definition hashes match, the configured bind is loopback-only, and a local SSH banner responds. Service age is about 40 seconds after kernel uptime start, which is consistent with current-boot startup but does not prove Termux:Boot delivered it. Listener PID ownership remains unknown because procfs enumeration is permission-denied. Separate 8022 policy remains wildcard-bound with password and keyboard-interactive authentication enabled; daemon/listener correlation and configuration owner remain unknown. No auth attempt or service/config action was made. Evidence: [current SSH recheck](2026-10-18-p3-ssh-current-session-recheck.json).

- 2026-10-18 05:42 UTC guest repeatability recheck: three bounded `proot verify --guest-user-from ternux-state --display :1 --backend zink` runs completed. Each reported X11 reachable, Zink/Turnip on Adreno 825, and audio control endpoint reachable; native PulseAudio process-only status still reported stopped while native `pactl` endpoint was available. This does not establish audible guest playback, Ternux rootfs ownership, or workload dispatch, so P3 gate 4 stays open. No audio stream or guest write ran. Evidence: [three-run guest verifier recheck](2026-10-18-p3-ternux-guest-repeatability-recheck.json).
- Focused regression rerun at 05:43 UTC: PRoot diagnostics 20/20 and management service 24/24 passed (44 total). Evidence: [focused test record](2026-10-18-p3-continuation-focused-tests-0543.json).

- 2026-10-18 05:43 UTC Doctor/remote policy recheck: Doctor remains read-only and reports 14 pass, 14 info, 1 warning, 0 errors. The warning is the separate native SSH 8022 wildcard bind with password auth enabled; owner and external reachability remain unknown. Remote access preview remains disabled with no transport selected, no credentials resolved, and no network/service/file changes. Evidence: [Doctor and remote preview recheck](2026-10-18-p3-doctor-remote-recheck-0544.json).

- 2026-10-18 05:52 UTC reboot gate review: Termux:Boot is installed and its standard script directory contains two regular executable scripts, but the CLI command is unavailable and startup policy remains unknown. Reboot status shows RB03 `boot_observed`/`NOT_READY`, RB02 `inconclusive`/`NOT_READY`, and RB01 `prepared`/`NOT_READY`; automatic resume is false for all. RB03's earlier verification is `verified_reboot_partial`; a separate postboot authenticated loopback probe passed, but the boot observer did not establish service health at boot. `resume-info` requires manual evidence review, so no checkpoint was changed and no new reboot was performed. Sanitized current record: [reboot gate review](2026-10-18-p3-reboot-gate-review-0546.json); detailed prior probe: [postboot SSH verification](2026-10-18-postboot-native-ssh-verification.json).

- 2026-10-18 05:53 UTC boot-log correlation: private native logs show the current kernel-boot estimate at 18:21:55Z; the two exact Termux:Boot scripts are owner-matched executable regular files (0700) whose hashes match repository source. The boot observer, service-start script, and Runit wrapper logged at 18:22:35Z; the service script logged SSH running/ready and the wrapper recorded Wake Lock acquire success. A separate postboot authenticated loopback SSH probe already passed. This materially supports current-boot startup and connection evidence, but log/script correlation cannot exclude a manual script invocation; GUI visibility and listener PID ownership remain unknown. RB03 remains `NOT_READY` because the boot observer itself recorded partial health; no checkpoint was edited and no new reboot ran. See [sanitized boot-log delivery evidence](2026-10-18-p3-boot-log-delivery-recheck-0554.json).

- 2026-10-18 05:55 UTC reboot-observer fixture recheck: `test_reboot_recovery.py` passed 12/12 and `test_runtime_diagnostics.py` passed 8/8 (20 total). These are repository fixtures only; they did not reboot or alter boot scripts, service, checkpoint, desktop, packages, or PRoot. Evidence: [reboot-observer regression record](2026-10-18-p3-reboot-observer-regression-recheck-0555.json).

- Fresh read-only live gate check at 06:03 UTC: Doctor 14 pass / 14 info / 1 warning / 0 errors. Managed SSH 8023 remains Runit-running, definition hash matches source, loopback banner succeeds, and startup timing is ~40 seconds after kernel boot; listener PID correlation is permission-denied/unknown. SSH 8022 remains configured wildcard/password-enabled, with listener ownership and external reachability unknown. Debian PRoot is inventoried but ownership remains unverified. Remote policy preview remains disabled and performed no network/service/file action. No reboot, package, guest, service, or desktop lifecycle action occurred. See [sanitized current live gate snapshot](2026-10-18-p3-live-current-gates-0603.json).

- Full-suite regression refreshed at 06:00 UTC: **218/218 passed** in 106.265 seconds. The structured result is [full-suite recheck evidence](2026-10-18-p3-full-suite-recheck-0602.json); this validates source fixtures, not device UI, sound output, boot causality, or provider ownership.

- Follow-up listener visibility probe at 06:09 UTC: native `ss` is not installed; `netstat` reports no AF_INET TCP support; `lsof` 4.99.7 returned no rows for the TCP-listener filter. Doctor independently reports listener observation permission-denied and daemon correlation unknown. Empty/unsupported output is not evidence that listeners are absent; PID ownership remains unresolved. No network or service action occurred. See [unprivileged listener probe record](2026-10-18-p3-ssh-unprivileged-listener-probes-0609.json).

- Installed Ternux CLI help was rechecked at 06:10 UTC. Version 1.4.0 lists lifecycle, diagnostics, benchmark, profile/backend/state, logs, update, and uninstall commands; it exposes neither a generic workload dispatcher nor a bounded audio-test operation. No guest command or sound stream was sent. This confirms the audible-output gate cannot be safely closed through the supported interface available today; PulseAudio control reachability remains a separate signal. See [installed CLI audio/workload command-surface check](2026-10-18-p3-ternux-audio-command-surface-0610.json).

- Native-side MP3 playback smoke check at 06:10 UTC: one regular MP3 from the native Termux HOME/Desktop was played with `termux-media-player` for an 8-second sample; play, playback-info, and stop commands all returned success. The personal filename was not recorded. This checks native media playback only; it does not prove Xfce/PulseAudio client routing or audible PRoot guest output. Owner audible confirmation is pending. Evidence: [native MP3 playback check](2026-10-18-p3-native-mp3-playback-check-0610.json).


- 2026-10-18 06:20–06:21 UTC native VLC checks: after owner-authorized native install (76 exact pins, zero upgrades/removals), VLC 3.0.24 played an 8-second MP3 sample to native PulseAudio with sink-input count 0→1→0 and exit 0. A separate bounded video invocation on :1 forced `xcb_x11`, disabled audio, and exited 0; GLX preflight was reachable. These do not confirm human audibility/visible frames, GPU decode, or PRoot guest playback. P3 audio/GUI gates stay open pending those distinct confirmations. See [native VLC evidence](2026-10-18-native-vlc-install-preview-0612.json).
- Post-media read-only Doctor at 06:23 UTC remained 14 pass / 14 info / 1 warning / 0 errors, with the existing SSH wildcard/password warning; the recorded :1 session remains running. This does not confirm GUI visibility or close P3 ownership/audio gates.

- 2026-10-18 06:24 UTC audio-enabled video rerun: bounded native VLC playback on :1 exited 0 with XCB video and PulseAudio output. Pulse sink-input count changed 0→1→0, confirming a native audio stream existed during playback. The previous silent video run had `--no-audio` intentionally. Audible/visual owner confirmation remains pending; this does not prove GPU decoding or PRoot routing. See [native VLC evidence](2026-10-18-native-vlc-install-preview-0612.json).
- 2026-10-18 06:26 UTC owner reported hearing sound during the audio-enabled native VLC video sample. Native VLC/Pulse audibility is now human-confirmed for that sample; this does not establish PRoot guest output or visual playback.
- 2026-10-18 06:26 UTC owner confirmed both sound and video frames during the audio-enabled native VLC sample on :1. Current-session native X11 media visibility and audibility are human-confirmed. This narrows the GUI gate for the live session only; it does not establish Termux:Boot GUI activity delivery, cold-boot visibility, PRoot display ownership, or guest audio.

- 2026-10-18 06:27 UTC off-home transport research: official Tailscale docs show Android incoming traffic is policy-controlled, the Android client has no CLI, and `tailscale serve` is a CLI-based loopback relay. This leaves Tailscale as an unqualified candidate only; current wildcard/password SSH on 8022 was not reused and no remote access was enabled. Provider/client choice and a safe Termux relay remain open. See [candidate review](2026-10-18-p3-offhome-tailscale-candidate-review.md).
- 2026-10-18 06:28 UTC post-media read-only Doctor remains 14 pass / 14 info / 1 warning / 0 errors; :1 session and managed 8023 banner remain observed, while 8022 wildcard/password configuration and listener ownership stay unresolved. Debian ownership remains unverified. No lifecycle action followed the media test. Full selected snapshot: [native VLC evidence](2026-10-18-native-vlc-install-preview-0612.json).
- 2026-10-18 06:30 UTC post-VLC package integrity recheck: 77/77 existing XFCE package records and 76/76 VLC transaction pins remain installed at exact versions/status; mismatch count 0. Read-only `dpkg-query`; no APT/network action. This corroborates P2 desktop dependency continuity after the optional native player install without reconstructing the original preview. See [combined package/media evidence](2026-10-18-native-vlc-install-preview-0612.json).
- 2026-10-18 06:32 UTC live P3 refresh: native desktop :1 and managed SSH 8023 remain running; boot delivery policy, platform Wake Lock state, listener attribution, Shizuku, and PRoot ownership remain unresolved. Three reboot checkpoints are still NOT_READY; no reboot/lifecycle mutation was made. Separate 8022 remains wildcard/password-enabled. Full sanitized state: [current P3 gate recheck](2026-10-18-p3-current-gate-recheck-0632.json).
- 2026-10-18 06:33 UTC remote-access preview remains disabled and non-applying: zero allowed clients/targets, transport not probed, and no credential/file/network/service action. Provider choice remains pending; see the appended [current P3 snapshot](2026-10-18-p3-current-gate-recheck-0632.json).

## 2026-10-18 06:40 UTC — Termux:Boot receiver qualification

- Native `./ternuxx --json boot status` reports Termux:Boot installed and enabled, its `BOOT_COMPLETED` receiver enabled, two regular scripts, and zero non-executable scripts. Independent Android package-manager queries for user 0 returned the enabled package and `com.termux.boot/.BootReceiver` in default and include-disabled receiver queries.
- Read-only `cmd appops get --user 0 ...` was denied by Android (`GET_APP_OPS_STATS`), and `cmd package dump` was denied (`DUMP`). Background-delivery policy therefore remains unknown. No reboot or script execution was used to infer boot causality; RB03 remains `NOT_READY` and manual invocation cannot be excluded.
- The boot diagnostic and Doctor NTX-APP-102 now expose package enabled state and receiver state while leaving system delivery policy explicitly unknown. Focused and full-suite results will be recorded after the implementation run. See [live boot receiver evidence](2026-10-18-p3-boot-receiver-enabled-0640.json).


## 2026-10-18 06:49 UTC — Native SSH listener attribution recheck

- Read-only `./ternuxx ssh inspect --json` reports the managed 8023 Runit service running, definition identity verified, loopback-only bind, and SSH banner response.
- All-process TCP listener enumeration remains `permission_denied`; the empty observed listener array is inconclusive and daemon-to-port ownership stays unknown. The separate SSH configuration reports wildcard bind; its listener owner and external reachability remain unknown.
- No service/configuration action or SSH authentication test was performed. See [sanitized 8022/8023 inspection](2026-10-18-p3-ssh-inspect-recheck-0649.json).

## 2026-10-18 06:56 UTC — ADB/Shizuku follow-up

A read-only SSH session found no native Termux `adb` CLI, but did find an
`adb`-named process under the Termux PRoot loader. A protocol `host:version`
query to `127.0.0.1:5037` returned `OKAY` / `0x0029`, confirming an ADB server
answered locally. Its process arguments identify TCP 5037, but do not establish
the bind host or external reachability. A command lookup in the default
`proot-distro` Debian guest did not locate `adb`; the active server's exact
guest identity remains unresolved. Shizuku package versionCode 1318 is
installed for user 0, while custom fork/signer identity, Shizuku process and
watchdog health, Wireless Debugging endpoint, and device authorization remain
unknown. No ADB device query, pairing, service/settings mutation, or lifecycle
action ran. Gate 6 remains **partial/open**. See [sanitized live evidence](2026-10-18-p3-adb-live-recheck-0656.json) and [ADR-0014](../architecture/decisions/ADR-0014-proot-adb-and-management-tcp.md).

The owner clarified that the complete custom-fork investigation already lives
in the ADT repository. We verified that checkout's remote as
`soobujmiah/adt`, confirmed the report matches `origin/main` at the pinned
commit, and reused [ADT's operational dependency report](https://github.com/soobujmiah/adt/blob/abece9e714a3bcb24d4a8dcc9f001feb421c1411/docs/ON_DEVICE_ADB_SHIZUKU_OPERATIONAL_DEPENDENCY.md).
That 2026-09-13 snapshot documents the loopback PRoot relay on 5037, the
separate Android-side 5555 bridge, Shizuku's `shizuku_server` role, manual
relay startup, and the custom fork's boot/watchdog behavior. It concludes the
5037 relay does not remove Shizuku's bridge/bootstrap dependency in that
workflow. Ternuxx records the conclusion and current 06:56 5037 response; it
does not duplicate ADT's source/forensic analysis or claim the dated ADT
snapshot alone proves current boot behavior.

## 2026-10-18 07:57 UTC — Native P2/P3 read-only recheck

An authenticated SSH session to native Termux reconfirmed all 77 P2 package
records installed at their exact recorded versions. The original full
pre-consent package simulation remains unrecoverable; this package-database
query does not recreate it. P2 remains complete under its existing accepted
evidence and historical limitation.

The same session reported Doctor 14 pass / 15 info / 1 warning / 0 errors,
with the existing `:1` desktop recorded running and GUI visibility unknown.
The Runit-managed `ternuxx-sshd` service on loopback 8023 is running, its
definition identity matches source, and an SSH banner responds; listener
process ownership remains unverified. The separate native 8022 configuration
still has wildcard bind and password authentication enabled, while listener
correlation and external reachability are unknown. Termux:Boot and its
`BOOT_COMPLETED` receiver are enabled, but delivery policy and reboot
causality remain unknown. Local ADB `host:version` returned `0x0029`; device
transport and authorization remain unknown. Shizuku versionCode 1318 is
present, `rish` is absent from PATH, and signer, service, permission, and
watchdog state remain unknown. No service, package, desktop, boot profile,
Android setting, or PRoot state was changed. Structured result:
[native recheck](2026-10-18-p3-p2-native-recheck-0757.json).

This refresh does not close P3 gates 4–6 or the remote-access gate. Existing
device ownership, cold-boot causality, guest workload routing, listener
ownership, Shizuku readiness, and off-home transport remain open.

The fresh full Native Termux fixture suite then passed **272/272** in 39.629
seconds with exit code 0. No device lifecycle or service action ran. This is
source/fixture verification, not closure of the open device-only P3 gates; see
[structured suite evidence](2026-10-18-p3-repo-test-recheck-0800.json).


## 2026-10-18 08:09 UTC — Management readiness contract

The loopback management adapter now distinguishes `GET /health` liveness from `GET /ready` listener readiness. The readiness probe follows the owning serving thread, passes through the existing request policy, fails closed, and is cleared before shutdown drain. Focused HTTP tests passed **22/22**; the full Native Termux suite passed **273/273** in 41.756 seconds. This is fixture evidence only; no persistent device listener, boot/service integration, browser, or remote transport was qualified. Evidence: [management readiness](2026-10-18-p3-management-readiness-0809.json). This source change does not close P3 exit gates 4–6.


- 2026-10-18 08:19 UTC native Doctor recheck remains read-only (14 pass / 15 info / 1 warning / 0 errors). It reconfirms the 8022 wildcard/password configuration, ADB `host:version` only, Shizuku uncertainty, and unverified guest ownership. No P3 device gate closes from this observation. See [sanitized live evidence](2026-10-18-p3-native-doctor-recheck-0819.json).


- 2026-10-18 08:21 UTC existing-provider interface check: native Ternux v1.4.0 exposes read-only status/backend commands but no generic workload dispatcher. Ternuxx `proot status` reports Debian installed, ownership unverified, and no guest entry. This confirms P3/P4 must keep dispatch unavailable until a reviewed supported contract exists; no Ternux lifecycle or rootfs action ran. Evidence: [provider-contract recheck](2026-10-18-p3-ternux-provider-contract-recheck-0821.json).


- 2026-10-18 08:23 UTC current `proot verify` again returned complete for the existing Debian `:1`/Zink route: X11 and audio control reachable, Zink/Turnip on Adreno 825. This strengthens repeatability evidence for gate 4, but does not qualify ownership-aware workload dispatch, audible output, GUI visibility, or hybrid routing. No guest writes or lifecycle actions occurred. See [verification record](2026-10-18-p3-ternux-guest-verify-recheck-0823.json).


- 2026-10-18 08:25 UTC source audit corrected the current P3 progress summary: every currently declared journal kind has an operation-specific `recovery resolve` handler; compensating rollback is limited to profile restore. The native focused recovery suite passed **56/56**. This supports the source/fixture recovery gate only, not device boot, guest ownership, or lifecycle qualification. See [recovery test record](2026-10-18-p3-recovery-focused-recheck-0825.json).

## 2026-10-18 08:29 UTC — Managed 8023 suite recheck

The full `bash scripts/repo_test.sh` suite ran through the loopback managed SSH test shell on port 8023 after entering from the 8022 work shell: **273/273 passed** in 35.700 seconds. This is source/fixture evidence; it does not qualify Android hardware, guest workload ownership, boot causality, or Shizuku readiness. No package, desktop/service lifecycle, boot/Android setting, PRoot guest, or separate Ternux repository mutation occurred. See [managed 8023 test evidence](2026-10-18-p3-managed-8023-suite-recheck-0829.json). P3 remains in progress.


### 2026-10-18 08:41 UTC — installed reboot observer source identity

A managed 8023 loopback dry-run now verifies the installed `ternuxx-sshd` definition against the canonical checkout; the earlier `unavailable` result came from resolving the source beneath `$PREFIX`. Installed and checkout dry-runs agree, and the managed 8023 suite passes 274/274. This improves the reboot observer evidence only: listener ownership is still unknown, RB03 remains `NOT_READY`, and Termux:Boot causality/post-boot GUI visibility are not established. No reboot was run. See [structured evidence](2026-10-18-p3-managed-8023-reboot-observer-resolver.json).


## RB04 pre-reboot baseline — 2026-10-18 08:48 UTC

Prepared private checkpoint `TERN-20261018-RB04` at mode 0600; status is `prepared` / `NOT_READY`. Baseline records the existing native XFCE desktop on `:1`, Debian inventory without guest entry, managed 8023 service/config readiness, current 8022 wildcard/password policy, enabled Termux:Boot receiver with delivery still unknown, and Wake Lock ownership limits. The public repo evidence excludes the checkpoint nonce and boot ID. No reboot, service/desktop action, boot-setting change, package operation, or PRoot action occurred.

The CLI has no device reboot operation. The next step is an owner-initiated Android restart; afterward, reconnect on 8023 and collect read-only checks. Do not manually run `boot-observe`, because that would not prove Termux:Boot delivery. Evidence: [RB04 prepared baseline](2026-10-18-p3-reboot-rb04-prepared.json).


## Native Termux full-repository audit follow-up — 2026-10-18 09:36 UTC

This is a follow-up snapshot; the original gate assessments remain historical.

- The full fixture suite ran directly in the native Termux work shell after the display-allocation source change: **277/277 passed** in 37.894 seconds. The focused desktop lifecycle suite passed **10/10**. Repository knowledge verification reported **0 findings**; JSON/YAML parsing, shell syntax, Python compileall, and git diff check passed.
- Audit found the default allocator began at :0 while the owner assigns :0 to the existing Ternux PRoot and :1 to native Ternuxx. The shared allocator now searches :1 through :10, checking both the X socket and lock and preserving occupied artifacts. Fixture coverage confirms default :1 and fallback :2 without claiming :0. The target desktop is currently running on :1; GUI visibility and concurrent :0/:1 server behavior remain unknown.
- RB04's owner-operated reboot produced verified_reboot_partial / NOT_READY: boot identity/observer evidence matched, but the observer sampled managed SSH before readiness. Later authenticated 8023 checks passed. The transient readiness retry is deployed; no reboot has tested that change yet. Termux:Boot delivery policy, listener process/socket ownership, Android Wake Lock state, and cold-boot GUI recovery remain open.
- A first interactive read-only Wake Lock status invocation produced no output for over 15 seconds and was interrupted. Direct manager and CLI retries then passed in 0.11 and 0.26 seconds; the behavior was not reproduced and no code/state change followed.
- Debian PRoot inventory remains read-only (guest_entered=false, ownership unverified). No PRoot lifecycle action ran.
- The dirty worktree snapshot is separately recorded in [native Termux dirty-tree audit](2026-10-18-native-termux-repo-audit-0936.json). The 08:14 manifest's 316 entries are all still present with unchanged Git statuses; 13 additional paths were already present by the start of this audit. All changes remain unstaged.


## 2026-10-18 10:02 UTC — RB06 postboot exit-gate follow-up

RB06 observed the changed boot and matching observer record, but Ternuxx's checkpoint verifier remained `verified_reboot_service_unqualified` / `NOT_READY`: managed-service health was unknown, socket binding was not observed, and authenticated connectivity was not part of the verifier result. A separate authenticated 8023 SSH session and the managed SSH banner/config checks passed after boot, but they do not establish listener ownership or update the private checkpoint. The retry change therefore remains device-unqualified by this result. Native desktop status was degraded with no supervisor/X11/XFCE process; GUI visibility remains unknown. Debian was present but its guest was not entered or ownership checked; db/xgo preservation was not checked. Termux:Boot package/receiver enablement and the matching observer were observed, while broadcast causality and system delivery policy remain unknown. Wake Lock platform state and 8022 listener attribution remain unknown. P3 stays in progress: gate 5 is still partial, gate 4 remains open, gate 6 remains partial, and no phase completion is claimed. See [RB06 postboot review](2026-10-18-p3-rb06-postboot-review.json).


## Follow-up evidence — 2026-10-18

The owner later confirmed that a PRoot `xmessage` window and then Thunar were visible on the native Termux:X11 `:1` display. This supports app-level X11 sharing and does not prove PRoot desktop ownership, cold-boot behavior, or machine-reported GUI visibility. Later native recovery evidence records `:1` as the active Ternuxx display while `gui_visible` remains unknown. The latest native repository suite now passes 283/283 via SSH 8022; this is source/fixture evidence only. P3 gates 5 and 6 remain open/partial, and gate 4 remains limited to the fail-closed ownership contract.
