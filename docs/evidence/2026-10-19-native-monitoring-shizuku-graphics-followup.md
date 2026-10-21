# Native monitoring, Shizuku, naming, and graphics follow-up — 2026-10-19

## Execution environment

All commands and tests in this record ran in Native Termux over the manually managed development connection on port 8022. `HOME=/data/data/com.termux/files/home`, `PREFIX=/data/data/com.termux/files/usr`, checkout `$HOME/ternuxx`, branch `main`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`. The worktree was already dirty before this follow-up; existing changes were preserved. `$PREFIX/bin/tx` is a 412-byte shim to `$HOME/ternuxx/tx`; its SHA-256 matches `scripts/tx-installed` (`a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401`).

## GUI monitoring policy

The policy code and tests are in the repository and are reached by the installed `tx` shim. Live read-only `./tx gui monitor status` was run repeatedly. Each response reported `enabled=false`, interval 300 seconds, `activity_launch=false`, `focus_check=false`, `scheduler=disabled`, no prior check, `activity_requests_performed=false`, and `focus_probe_performed=false`. No policy file exists, so defaults remain active. `./tx --json gui status` reported Linux GUI `running` on `:1`; the supervisor, Termux:X11 server, and XFCE process identities were live, while independent Android visibility remained `unknown`. The same session state and monitoring status were preserved through these read-only queries.

The one Runit scheduler source exists at `scripts/termux-services/ternuxx-gui-monitor/run`, but `sv status ternuxx-gui-monitor` reports that its service directory is absent. It has not been installed or started on-device. Thus default-disabled/non-intrusive behavior is device-verified; opt-in scheduled monitoring is fixture-tested but is not yet installed/qualified on the device. No Android Activity launch or focus probe was executed for this follow-up.

The complete Native Termux unit/fixture suite passed **385/385** in **94.338 seconds**, exit **0**, command `python3 -m unittest discover -s tests`. An earlier run had one stale boot-profile assertion expecting an automatic Activity request; that assertion was corrected to expect disabled-by-default/manual-open behavior, the focused boot-profile suite passed **14/14**, and the final full suite passed. Focused Doctor tests (24/24), GUI monitoring (10/10), management service (27/27), HTTP runtime (6/6), desktop lifecycle fixtures (20/20), and boot-profile fixtures (14/14) passed. After the final Doctor/audio/Shizuku diagnostic changes, the complete suite passed **387/387** in **119.771 seconds**, exit **0**, with command `python3 -m unittest discover -s tests`. These are unit/fixture results, not live Activity qualification.

## Shizuku `rish` files

Only the owner-specified source paths were accessed. Both sources were regular files, owner UID 10269, mode 660:

- `/sdcard/Others/rish`, 882 bytes, SHA-256 `3b01b0cc72cfad779bff56efc29e6ad30aaa9b3969aa349cdf2aa5f876bf2066`.
- `/sdcard/Others/rish_shizuku.dex`, 59712 bytes, SHA-256 `99dbfa1998acf5092c7d9f17523157307755c7a70d04798df13ad702a390f1ab`.

Copies now exist in Native Termux `$HOME/rish` and `$HOME/rish_shizuku.dex`; their hashes match the originals exactly. The copied wrapper is mode 700 and DEX mode 400, both owned by the Termux UID. The inspected wrapper is the supplied Shizuku shell stub and contains the documented `PKG` application-ID placeholder. `$HOME/rish.sh` was absent; no new launcher was fabricated and the source wrapper was not modified. The Android package query `pm path moe.shizuku.privileged.api` failed with `Failed transaction` from the package-manager Binder. No provider process was observed by the bounded process-name query. Doctor package metadata independently reports the package present at versionCode 1318. Provider identity, Binder/server health, Termux authorization, and command capability are still unknown; no `rish` command was executed. The integration remains optional and unqualified.

## Canonical naming and installed boot artifacts

A case-insensitive repository search at that checkpoint found no live identifier using the reported double-x spelling. Earlier compatibility code and private state used a prior-name state override, executable, and module tree. That private tree contained a session record, SSH/wakelock state, logs, diagnostic snapshots, and operation records; its records differed from the canonical state tree. The two trees were not renamed, merged, deleted, or overwritten. Source boot/recovery preferred canonical state and module locations while retaining explicit fallback support until an ownership-aware migration was designed. This describes the recorded historical state; current checkout and runtime status are audited separately.

Repository and installed boot files still differ. Current source SHA-256: `00-ternuxx-services` `8dfa04273dd93cc0def5f26b70d496b9f80575f4608bcf079cea993eb04d3119`; `ternuxx-recovery` `702f4f21229495bf8725ce67063877ccd47810fd20f0651ae1e9a79ae9fad64d`. Installed files under `$HOME/.termux/boot/` remain at the previously recorded hashes `53b6745a930af57434cc046861f5df11d9a6aaf76529a857ab4c2cc978ac9b4e` and `4861f2145f58e3d21f0dd4619e30f4a09f555df9a78bfbe515757a567d417c26`. They were not redeployed in this follow-up; source/installed boot parity and cold-boot behavior remain unverified. No reboot occurred.

## Native graphical/audio and PRoot observations

Live `pactl info` connected to a local PulseAudio 17.0-dirty server at `/data/data/com.termux/files/usr/tmp/pulse-AU1kTwNZYXzc/native`, reporting `OpenSL_ES_sink` as the default sink. `pactl list short sinks` showed that sink in `IDLE`. The daemon process was visible but is not recorded as owned by the Ternuxx GUI supervisor; no audio service lifecycle action was taken. The native XFCE process had `DISPLAY=:1`, a private D-Bus session address, and Ternuxx's XFCE runtime path. No PULSE_SERVER variable was present in that process environment.

The read-only `./tx proot status --json` reported the existing Debian distribution installed, no guest entry, and host PRoot process ownership unverified. Existing launcher sources show separate `:0` and `:1` paths; the inspected wrappers do not set `PULSE_SERVER`. PRoot, `db/droot`, workspace, `x.sh`, `xgo`, `killx`, acceleration configuration, and guest files were not modified or entered. Shared audio socket visibility, cookie/authentication compatibility, Debian client connectivity, audio playback, and display parity remain unverified. These findings do not qualify PRoot/audio integration.

## SSH and gate

Read-only `./tx ssh inspect --json` reconfirmed:

- **8022:** manually managed development SSH is present and its config is valid; TCP listener observation is denied by Android procfs restrictions, so daemon-to-listener ownership remains unknown. No 8022 lifecycle or configuration action occurred.
- **8023:** `ternuxx-sshd` is Runit-running, configured for `127.0.0.1:8023`, source and installed run definitions match at SHA-256 `1e45a818d1d5c4b9d74eddb46ee57b3e74412915e63fadacfb609c25301b9237`, and a loopback SSH banner was observed. Socket-to-process PID ownership remains unavailable in the current diagnostic.

P3 remains **blocked / not qualified** by boot/source deployment and cold-boot evidence, socket ownership restrictions, GUI screen visibility, Shizuku provider/authorization, and service readiness/lifecycle qualification. P4 remains **planned/gated**; no Debian adapter or workload change was made. Reboot was not performed. Existing GUI, SSH, and PRoot processes were left operational.


## Final validation update — 2026-10-19

After the Doctor audio/Shizuku diagnostics and boot-profile expectation update, `python3 -m unittest discover -s tests` passed 387/387 in 119.771 seconds (exit 0). `python3 -m unittest discover -s tests -p 'test_doctor_report.py' -v` passed 24/24. Repository knowledge verification returned 0 findings before this final documentation refresh; it was rerun as part of final checks. No live policy configuration, Activity, focus probe, Shizuku command, service restart, boot redeployment, or reboot was performed.


The final live check reran `./tx --json doctor` with exit 1 because the aggregate Doctor report is warning-level; the JSON retained a passing PulseAudio finding and an informational Shizuku finding with unknown provider/authorization. A live `./tx gui` repeat returned already-running with exit 0; the canonical session record hash remained `2d99ec0c777493644b26f60097161b42980f7a94eaded51a969f644544970abe`.


## Doctor audio probe safety follow-up

- Native Termux libpulse-family artifact scan did not find the `PULSE_NO_AUTOSPAWN` marker in the installed client/runtime files inspected. This does not by itself prove the setting is unsupported, but it is insufficient evidence to claim safe suppression.
- Updated `lib/doctor_report.py` to stop invoking `pactl info` during Doctor and to report PulseAudio protocol readiness as unknown until a supported passive probe is verified. The generic subprocess runner no longer sets the unverified PulseAudio variable.
- Native focused validation: `python3 -m unittest tests.test_doctor_report -v` passed 24/24, exit 0. Regression test asserts no `pactl` subprocess is invoked.
- Earlier manual `pactl info` observation remains a dated snapshot only; no service was started, stopped, or restarted during this follow-up.

## Final continuation validation and boot-ready service requirement

- Actual Native Termux run environment confirmed `HOME=/data/data/com.termux/files/home`, `PREFIX=/data/data/com.termux/files/usr`, repository `$HOME/ternuxx`, branch `main`; pre-existing dirty owner worktree was preserved. Installed `$PREFIX/bin/tx` and `scripts/tx-installed` SHA-256 both `a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401`.
- Native full suite after the Doctor probe change: `python3 -m unittest discover -s tests`, 387/387 passed in 112.759 seconds, exit 0. Focused `python3 -m unittest tests.test_doctor_report -v`: 24/24 passed, exit 0.
- Static checks: shell syntax exit 0; `compileall` exit 0; phase state and all JSON schemas parsed; `git diff --check` exit 0; repository knowledge verification 0 findings, exit 0.
- Live read-only `tx gui status`: display `:1` running and supervisor/X11/XFCE identities verified; Android visible state unknown. `tx gui monitor status`: enabled=false, interval=300, Activity launch/focus checks=false, scheduler=disabled, freshness=never; no Activity request or focus probe performed. `tx ssh inspect`: 8022 manually managed/configured, process/listener mapping unknown; 8023 Runit `ternuxx-sshd` running on loopback with matching installed/source definition and SSH banner, listener PID ownership unavailable. `tx proot status`: Debian installed, guest not entered, process ownership unverified. `tx doctor`: exit 1, overall warning; audio readiness unknown and no PulseAudio client probe run.
- The requested generic boot-ready service catalog and cross-interface add/remove/configure parity remain implementation gaps. The current architecture doc records the target and boundary; duplicate/unowned audio processes remain inspect-only. No Android Activity, focus poll, service lifecycle action, Shizuku invocation, PRoot guest entry, boot deployment, or reboot occurred.


## Owner scope clarification — shared service/resource management

The accepted project scope includes one shared managed-resource catalog used by CLI, TUI, Web UI, and graphical UI. Supported resources (including managed SSH endpoints) must be addable/removable and configurable; lifecycle controls include start/stop/restart, background execution where supported, enable/disable and autostart-at-boot, status/readiness, dependencies, logs, and safe recovery. Idempotent reconciliation must avoid duplicate processes and preserve conflicting/unowned resources. Port 8022 remains manually managed and excluded; 8023 remains the current Ternuxx-managed SSH service. This is a scope clarification, not evidence that the full catalog is already implemented. Existing GUI recovery, configurable monitoring, Shizuku, SSH ownership, boot qualification, graphics/audio, and Debian PRoot work remain active parts of the same project.


## Owner usability clarification — categorized management

The shared resource/service/deployment catalog is expected to remain easy to navigate as scope grows: stable categories and IDs, concise descriptions, category browsing/search, only context-valid actions, guided common tasks, and review previews for disruptive changes. Category/resource vocabulary and operation results must be consistent across CLI, TUI, Web UI, and GUI. This is an accepted usability requirement; implementation and usability qualification remain pending with the general catalog.
