# Fresh guest, terminal close and probe boundaries — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Fresh setup and preservation

I completed the pinned Debian image/snapshot replay on the separate `ternuxx-replay-p4` target through Native SSH 8022. The saved preview identity and installed receipt match. All 54 requested packages are installed; the status/version inventory contains 1102 installed entries. The ordinary account, sudo membership, locale and pinned Turnip driver hash were independently checked. [Setup record](2026-10-22-fresh-setup-live.json).

The installer wrapper compared the working Debian root identity and selected protected-file hashes before/after; they matched. This is scoped preservation evidence, not a full original-to-current rootfs snapshot comparison. The working Codex guest and Native Termux were not stopped or replaced. The new guest's driver installation is not graphics workload qualification.

## Actual terminal failure and fix

The first production broker replay passed start, guest I/O, observed PTY dimensions and detach/reattach, then failed close. The registry wrote `stopping` but rejected that state on read. SIGTERM did not close the interactive shell. A first SIGHUP to only the tracer group also failed: kernel evidence showed the shell in a separate job-control process group within the same new private session, while the tracer ignored hangup.

The stop path now keeps `stopping` readable, returns explicit state and discloses profile-specific signal/scope in a version-bound stop plan. Interactive close sends graceful SIGHUP to the owned leader and revalidated job-control groups within that private kernel session. Changed process-start, session or group identity prevents a child-group signal. Headless probes retain SIGTERM. No force signal or broad cleanup is used. A timeout remains `stopping`; already-completed PTY cleanup is accepted only when the runtime is disconnected.

The retained failed test session was recovered with that exact owned stop path, and its test broker/state were cleaned. A repeat run passed the production broker lifecycle and actual CLI I/O, resize, Ctrl+] detach, reattach and exact close. [Live result](2026-10-22-fresh-terminal-live.json). This does not qualify TUI/Web/GTK terminal interaction.

## Guest execution and browser detection

Installed PRoot-Distro 5.9.0 writes its generated guest profile for normal containers even in isolated/minimal mode. The fixed diagnostic payload remains non-mutating, but whole-operation `read_only` is now false once guest login was attempted; the result/schema separately disclose payload intent and possible launcher writes, including failure/timeout outcomes.

Both verification operations now require `graphics.manage` and mutation CSRF in HTTP. The former `guest.diagnostics.read` capability is removed. Debian graphics status now reads installed inventory without entering the guest; explicit verification performs the workload. Browser detection likewise checks a rooted executable without invoking a login, accepts in-root links and refuses escapes. Actual Native detection found Firefox and preserved the working guest profile.

Fresh Native loopback API/Web checks proved read-only rejection, control/CSRF enforcement and a Debian status response without guest entry. The working guest profile hash remained unchanged. [HTTP result](2026-10-22-probe-http-live.json). No existing Web listener was restarted; current source applies to new runtimes. The initial manually composed smoke-check cleanup used an unsupported keyword; its exact test process was stopped and the corrected check drained both temporary servers cleanly.

## Evidence

- Full Native regression: 743/743 passed in 105.231 seconds. [Source-bound result](2026-10-22-probe-terminal-regression.json).
- Focused session tests 44/44, broker assembly 4/4, guest diagnostics 24/24, HTTP runtime 17/17, management sessions 10/10 and graphics 16/16.
- Old scope/metadata behavior, browser-detection login, guest execution during status, unreadable stop state and interactive termination defects were reproduced before their fixes. Negative job-group cases verify no signal after start/session/group identity changes.
- The default live terminal broker was idle with no nonterminal managed records before its scoped reload; no SSH/desktop/working-guest service control was performed. The final idle reload/status also passed after the version-bound stop-plan update; a separate final guest replay observed the disclosed SIGHUP/private-session scope and returned stopped/disconnected.

## Remaining acceptance

Qualify TUI, Web and GTK/VTE start/attach/I/O/resize/detach/close on the new guest. Complete fresh rollback/removal, broader Native/guest config/package/driver parity and reproducibility, exact probe preview/rollback, credential/service-policy controls and the remaining all-document/source audit. Public release, rendering/inference/NPU and later cold boot are not implied. [Full audit](../audit/REPOSITORY-AUDIT.md).
