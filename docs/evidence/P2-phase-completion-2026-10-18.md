# P2 phase completion — safe native desktop lifecycle

Phase: `P2`
Gate: PASS
Reviewed: 2026-10-18 (Asia/Dhaka)
Evidence scope: attached Android 16 / aarch64 Termux target, repository fixtures, and recovered APT history. This does not certify other device builds.

## Acceptance criteria

- **Preview-first package installation:** PASS. The installer now saves the complete requested candidates, APT simulation, and resolved package/version closure in private state. An explicit SHA-256 plan ID binds owner approval to that exact record. Before any package mutation, the current simulation is rebuilt and must match the saved preview; the complete version-pinned closure is passed to APT. The target-native test exercised a current official-index preview and intercepted the apply argv before invoking APT; the argv matched all four resolved versions exactly. Source fixtures also tested same-plan apply, changed-plan refusal, missing consent, outside-HOME/symlink refusal, and private file modes.
- **Native lifecycle:** PASS for the recorded target. The device evidence records initial start, repeated start, injected partial startup failure and scoped cleanup, stop/repeated stop, and preservation of the existing Debian PRoot login across the native lifecycle test. The owner confirmed the `:1` Termux:X11 GUI was visible.
- **Unrelated audio ownership:** PASS for the recorded target. PulseAudio remained externally owned; the owner reported hearing the test tone and requested three additional playbacks, which were run. No Ternux or PRoot rootfs/launcher changes were made.
- **Versioned physical-device record:** PASS. Termux, Termux:X11 package and APK, Android/API, ABI, display, audio ownership, and native renderer limits are recorded in the P2 lifecycle evidence. Other device builds remain unqualified.
- **Interrupted lifecycle state:** PASS at the P2-to-P3 boundary. Native start/stop journal records and recovery findings are implemented and exercised in fixtures; this does not claim P3 recovery is complete.

## Evidence

- [P2 lifecycle progress and physical-device record](P2-lifecycle-progress.md)
- [Recovered 77-package applied XFCE transaction](P2-termux-xfce-install-transaction-2026-10-18.json)
- [Target-native exact-preview and version-pinned apply-argument validation](P2-live-installer-preview-validation-2026-10-18.json)
- [Latest read-only installed package-closure recheck](2026-10-18-p2-package-closure-latest-recheck.json)
- [P3 Doctor, journal, and package-plan fixture evidence](P3-doctor-progress.md)
- Full repository tests: `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` passed **83/83** after the installer and journal changes. Targeted package-plan tests passed **11/11**. `bash -n lib/phases.sh`, CLI help contract, JSON syntax, and `git diff --check` passed.

## Historical evidence limitation

The original XFCE install's console output before consent did not include or preserve the complete 77-package dependency preview. That historical capture is not recreated or claimed here. APT history proves which 77 package/version entries were applied, while the later target-native validation proves that the current installer records, identifies, revalidates, and version-pins a full preview before package execution. No second package transaction was run to manufacture historical evidence. The optional `xfce4-power-manager` preview used for the target-native validation was not installed; its APT application branch was intercepted before execution.

## Post-completion regression recheck — 2026-10-18

- Re-ran `PYTHONPATH="$HOME/.cache/ternuxx-audit-venv/lib/python3.14/site-packages" bash scripts/repo_test.sh` from the authenticated native Termux shell. The full repository fixture/unit suite passed **125/125** in 31.509 seconds. This adds current source-regression evidence; it does not change the historical install capture or claim another physical lifecycle run.
- The test suite made no APT transaction and did not start/stop the desktop, SSH service, boot profile, or PRoot guest. The native desktop remained running on `:1` in the immediately preceding read-only status/Doctor check.

## Post-completion installed package-closure corroboration — 2026-10-18

- A read-only native Termux `dpkg-query -W` audit compared every package/version in the recovered 77-entry APT history record against the current installed package database. **77/77** names remain installed at the exact recorded version; 0 were missing and 0 had a version mismatch.
- Evidence: [current installed package-closure audit](2026-10-18-p2-installed-package-closure-audit.json). This corroborates present installed state against APT history; it does not recreate the original pre-consent preview or change the separate four-package live-preview record. No package action occurred.

## Post-completion native recheck — 2026-10-18 08:16 UTC

- Over the authorized native Termux SSH connection, `./ternuxx --json status` reported the existing desktop running on `:1`. A fresh read-only `dpkg-query` comparison found all **77/77** packages in the recovered XFCE transaction installed at their exact recorded versions, with no missing package or version mismatch.
- No package, desktop, service, boot, Android setting, or PRoot action ran. This is current-state corroboration only; the original complete pre-consent preview remains unavailable and is not reconstructed. See [structured native recheck](2026-10-18-p2-native-closure-recheck-0816.json).


## Current installed package closure recheck — 2026-10-18

- Re-ran native Termux `dpkg-query -W` for all 77 names in the recovered XFCE APT transaction. **77/77** remain installed at the exact versions in the transaction record; 0 missing or version-mismatched. This is a read-only current-state check, with no APT command that changes package state.
- Detailed per-package output is in [current P2 package-closure recheck](2026-10-18-p2-package-closure-current-recheck.json). It strengthens the current installed-state gate only; the original full pre-consent preview is still unavailable and is not reconstructed or claimed.


## Latest installed package-closure recheck — 2026-10-18

- At 2026-10-18 01:15:07 UTC, native Termux `dpkg-query -W` confirmed **77/77** packages from the recovered XFCE APT transaction remain installed at their exact recorded versions; 0 were missing or mismatched. This was read-only and made no package changes.
- Evidence: [latest closure recheck](2026-10-18-p2-package-closure-latest-recheck.json). It corroborates current package state only; the original full pre-consent console preview remains a non-recreatable historical limitation, and no claim is made that this new check recreates it.


## Fresh package closure follow-up — 2026-10-18

- At 2026-10-18 01:27:49 UTC, a new read-only `dpkg-query -W` check compared all 77 names and expected versions in the recovered XFCE APT transaction. **77/77** remain installed at the exact recorded versions; 0 missing or mismatched. No APT transaction was run.
- Evidence: [fresh package closure follow-up](2026-10-18-p2-package-closure-followup.json). This strengthens present-state closure evidence only. The original full pre-consent dependency simulation is still absent and cannot be recreated from the installed-state database; the four-package target-native preview remains evidence of current installer preview/apply binding only.

- At 01:29:12 UTC, read-only status after the recheck still reported native desktop running on `:1` with X11 and XFCE session present, GUI visibility unknown, and external audio ownership. `proot status` listed Debian without entering the guest and retained ownership unverified. These checks caused no lifecycle change; see `runtime_noninterference_check` in the follow-up evidence.

- Phase-state metadata correction: `project/phase-state.json` and generated phase tables previously dated P2 completion as 2026-10-17, inconsistent with this completion record and the 2026-10-18 target evidence. The completion date is now recorded as 2026-10-18. No gate result or historical runtime claim changed.

- The same 01:32:21 UTC read-only package audit also checked every one of the 12 root candidates currently declared by `lib/phases.sh:_NT_BASE_PACKAGES`: **12/12 installed**, including `termux-x11-nightly`, D-Bus, PulseAudio, Python, and all eight XFCE roots. Versions are in the `base_installer_roots` section of the follow-up JSON. This is current installed-state evidence, not a replay of the original preview or approval.

- At 01:37:24 UTC, `./ternuxx --json install --preview` returned `already_installed` and `packages_changed=false` because all 12 base roots are currently installed. The command created no saved preview, as there was no install transaction to approve. This confirms safe no-op behavior and preserves the original historical-preview limitation.

## Current-session state recheck — 2026-10-18

- At 2026-10-18 05:40 UTC, a read-only native Termux check confirmed the native desktop process state remains running on `:1` with X11/XFCE reported present; GUI visibility is unknown to the CLI and audio is externally owned. PRoot inventory reports Debian installed without entering the guest; ownership remains unverified.
- The recovered XFCE APT transaction still matches **77/77** currently installed package versions. This supports present-state continuity only. The original full pre-consent simulation remains unrecoverable and is not reconstructed.
- Evidence: [current P2/P3 session recheck](2026-10-18-p2-p3-current-session-recheck.json). No reboot, package transaction, desktop/service lifecycle, guest entry, or network action occurred.

## P2 source fixture regression recheck — 2026-10-18

- Fresh package-plan tests passed **11/11** and desktop lifecycle fixture tests passed **8/8**. The package fixture intercepts the pinned apply argv; desktop lifecycle uses mock processes and does not touch the device desktop. No APT transaction or device lifecycle action ran.
- Evidence: [current P2 regression recheck](2026-10-18-p2-regression-recheck-0545.json). This verifies current source fixtures; it does not recreate the original pre-consent dependency preview or replace physical-device evidence.

## Current full-suite regression recheck — 2026-10-18

- The full repository suite passed **218/218** in 106.265 seconds from the current working tree. The record notes expected fixture diagnostics, including the stale-index rejection case. No device reboot, package transaction, or desktop lifecycle action occurred. See [full-suite recheck evidence](2026-10-18-p3-full-suite-recheck-0602.json).
- This current regression run supports source stability across the repository. It does not recreate the original 77-package pre-consent APT simulation; that historical limitation remains explicit above.

## Fresh native P2 package-state recheck — 2026-10-18 06:10 UTC

- Native `dpkg-query -W` compared every entry in the recovered XFCE APT transaction with the current package database: **77/77 exact installed version/status matches**, 0 missing or mismatched. Evidence: [fresh package closure recheck](2026-10-18-p2-package-closure-recheck-0610.json).
- `./ternuxx --json install --preview` returned `already_installed` and `packages_changed=false`; because every base root is present, the command created no new preview. Evidence: [current installer no-op result](2026-10-18-p2-installer-current-noop-0610.json).
- These are present-state/read-only checks. The historical pre-consent preview remains unrecoverable; no APT transaction or index refresh was run.

## Post-completion optional VLC package non-regression check — 2026-10-18

After the owner-authorized native VLC install for later media tests, a fresh read-only `dpkg-query` audit confirmed all **77/77** package/version/status entries from the existing XFCE transaction and all **76/76** VLC transaction pins remain installed exactly. No package transaction or network access occurred during this recheck. This confirms current package closure after the optional native player install; it does not recreate the historical XFCE pre-consent APT preview. Detailed evidence: [combined package/media record](2026-10-18-native-vlc-install-preview-0612.json).
