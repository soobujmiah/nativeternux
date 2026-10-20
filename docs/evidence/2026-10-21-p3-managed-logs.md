# P3 bounded Native management logs - 2026-10-21

Phase: `P3` progress evidence; this does not complete the phase.

## Implementation

Added typed read-only operations `management.logs.list` and `management.logs.read` to the shared management service. The source allowlist contains the Native desktop XFCE log, Ternuxx Cron scheduler log, and secret-free management API audit trail. The XFCE log can contain output written by apps in the desktop session, so clients label it explicitly. Callers cannot pass filesystem paths.

Reads require a private Ternuxx state tree and same-user regular files with mode 0600; source directories must be same-user private directories with mode 0700. Symlinks, unknown IDs, changed identities, and invalid limits fail closed. Reads are limited to the last 256 KiB and at most 300 lines; ANSI/control characters are removed and long lines are capped. Audit output reconstructs a safe field set and omits request/session identifiers.

The CLI exposes `tx mng logs list` and `tx mng logs read SOURCE_ID`. TUI, Web, and GTK call the same typed operations. Web has an on-demand source picker and bounded viewer. GTK has source-specific actions; TUI prompts for an available source. No Android-global or arbitrary application logs are exposed.

## Evidence

### Native device

Read-only live Native Termux calls through `tx mng logs list` found all three allowlisted sources. The Native `desktop.log` was observed as a same-user mode-0600 regular file (84,858 bytes); its contents were not read during the metadata audit. Reading the management audit returned operation, capability, event, time, status, and duration fields; session references and request IDs were absent. The Cron scheduler log was present but empty. The catalogued managed-SSH log path and Activity-monitor log were absent, so their catalog status was corrected to not-recorded; no SSH service definition or process was changed. No log file was created or changed by the read.

The installed GTK Management Center was updated atomically by `scripts/install-management-center.sh`; its new Native desktop log button is source-compiled and installed. The prior binary hash was `2393e252165ecdd2a53c2b3b69f9b1e58e8949896b90bd2d33324f27ae45020f`; the refreshed binary SHA256 is `8762a16cb85c759d2af8eacfaf4352082a3315d2963cf77dc3a0b1c759f40659`. The existing Native :1 desktop and Termux session were not restarted. The new Native GTK window was opened on the live :1 display and visually inspected. Its stderr reported Freedreno Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER`, but the GTK window rendered; this visual check does not qualify Vulkan acceleration. Selecting Native Termux health showed the Native desktop, Cron scheduler, and management-audit log buttons; the desktop action label warns that app output may be included. No log button was clicked, so the potentially app-bearing desktop log contents were not exposed. A Native TUI PTY run at 120x40 then selected Native Termux health, opened the log-source prompt, selected the empty Cron scheduler log, and returned a successful read result. It did not read the desktop log. A Native loopback HTTP runtime in read-only scope served the current Web UI page (HTTP 200), including the Native desktop app-output note. A scoped diagnostics.read session listed all three sources and successfully read the empty Cron log; no browser was opened, so visual browser acceptance is not claimed.

## Verification

- Management/log-reader/TUI/Web/GTK bridge focused tests: **114 passed** before the dedicated log-reader fixtures were added.
- New log-reader fixtures: **5 passed**.
- Full Native Termux repository suite after the Native desktop source addition: **651 passed** in 101.869 seconds.
- GTK C syntax compile, Python compilation, shell syntax, and `git diff --check`: passed.
- Live `tx mng logs list` and `tx mng logs read` returned bounded results.
- No service, scheduler, desktop, SSH, PRoot session, or Android setting was changed.

P3 remains active. The operation is source-integrated across all four clients. GTK log-control visibility is visually confirmed on :1 and the TUI Cron log read succeeded; A Native loopback HTTP runtime in read-only scope served the current Web UI page (HTTP 200), including the Native desktop app-output note. A scoped diagnostics.read session listed all three sources and successfully read the empty Cron log; no browser was opened, so visual browser acceptance is not claimed. Cold-boot delivery remains unverified and must be qualified in its separate device-boot window.
