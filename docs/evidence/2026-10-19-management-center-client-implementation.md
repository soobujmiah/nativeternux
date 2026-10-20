# Management Center client implementation — 2026-10-19

## Target and preservation

Implementation ran in Native Termux at `/data/data/com.termux/files/home/ternuxx` (`$HOME/ternuxx`), `PREFIX=/data/data/com.termux/files/usr`, on branch `main`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`. The worktree was already dirty and all unrelated/pre-existing changes were preserved. The repository's shared catalog v2, API-v1 operation dispatcher, exact capability map, and request store remain authoritative. No PRoot files, 8022/8023 listeners, GUI session, audio server, boot script, or Activity-monitor policy were changed by lifecycle action.

## Client implementation

- **Web Console:** `lib/management_web_ui.html` now has the green-dark responsive layout, categories from `management.catalog`, search/status filters, resource ownership/readiness/capability details, supported/planned actions, a response panel, and the monitoring policy form. It calls the authenticated loopback `/api/v1/operations` API. Web grants catalog/diagnostic read scopes plus `desktop.manage` and `desktop.monitor.manage`; mutation scopes allow only desktop start/stop/restart and monitoring-policy configuration. Mutations use confirmation, CSRF proof, and durable idempotency. SSH/boot/PRoot/recovery writes remain unavailable in Web.
- **TUI:** `lib/terminal_ui.py` now browses catalog categories/resources, supports keyboard category navigation and search, reports resource capability/current state, performs only zero-argument read operations automatically, and offers guided PRoot launch, confirmed native desktop start/stop, and Activity-monitoring-policy configuration. Ordinary navigation no longer requests operation IDs or JSON arguments.
- **Native graphical application:** `apps/management-center/management-center.c` is a GTK4 application, separate from XFCE and the browser. It provides categorized/searchable resources, detail and live-inspection views, explicit desktop start/stop confirmation, and a monitoring-policy form with seconds/minutes/hours validation. Its fixed-action bridge at `scripts/management_desktop_bridge.py` delegates to the shared `management_service` operation contract and rejects arbitrary shell actions. No Termux:X11 Activity request or focus poll is part of status inspection.

All interfaces use catalog category/resource IDs and the same capability maturity terms: implemented, partial, external, unverified, unavailable, and planned. Current limits are recorded in the capability matrix: no client yet offers full SSH 8023 deploy/lifecycle, boot-profile writes, PRoot shortcut apply/remove, recovery apply, general server deployment, log/history readers, or asynchronous operation IDs/progress. The Native GTK window has not been opened for visual/manual interaction qualification.

## Install and live checks

Commands executed in Native Termux:

- `./tx management center install` — exit 0; compiled and installed GTK4 client and source identity record.
- `$PREFIX/libexec/ternuxx/management-center --self-check` — exit 0; reported GTK 4.24.1.
- `$PREFIX/bin/tx-management-center --version` — exit 0; printed Ternuxx Management Center 0.1.
- `./tx --json management catalog list --category desktop-audio` — exit 0; live checkout CLI returned the catalog category/resource response.
- `python3 scripts/management_desktop_bridge.py catalog` and `... monitor` — exit 0; bridge emitted all 12 catalog categories and reported monitoring disabled without Activity/focus work.

Installed artifact identity:

- C source SHA-256: `480521811a54c623351cd204d74480370fdfef5ac122c90fd0891db5e28ee44a`
- Typed bridge SHA-256: `24882c638341550e9e7618ef36a970d28ce592809fd665a98b7d90a5a982a213`
- Installed GTK executable (`$PREFIX/libexec/ternuxx/management-center`) SHA-256: `8dcae232426e4c4785bf2331c3a5b8df92378182f413c321859929e8e109969d`
- Installed launcher (`$PREFIX/bin/tx-management-center`) SHA-256: `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd`

The identity values match `$PREFIX/libexec/ternuxx/management-center.identity`. GTK4 was already installed; no package install/upgrade occurred. Build and launcher do not execute or launch the graphical window unless `tx management center` is explicitly run. The window was not launched in this validation, so rendered UI, native actions, and owner visual interaction remain unverified.

## Tests and validation

Focused tests, all run in Native Termux with exit 0:

- `python3 -u -m unittest discover -s tests -p 'test_management_http_runtime.py' -v` — **7/7**.
- `python3 -u -m unittest discover -s tests -p 'test_terminal_ui.py' -v` — **10/10**.
- `python3 -u -m unittest discover -s tests -p 'test_management_desktop_bridge.py' -v` — **5/5**.
- `clang -Wall -Wextra -Werror=implicit-function-declaration apps/management-center/management-center.c -o "$TMPDIR/ternuxx-management-center-test" $(pkg-config --cflags --libs gtk4)` — exit 0.
- `python3 -m py_compile ...` for the changed Python service/UI/bridge/tests — exit 0.

Complete Native Termux suite: `unittest` discovery ran **398/398 tests in 130.181 seconds**, all passed. The bounded wrapper checked that no non-main Python worker thread remained and returned exit 0. A prior direct `bash scripts/repo_test.sh` run printed 397/397 `OK` but remained alive during interpreter shutdown; it was interrupted after that output, so that invocation did not receive a clean shell exit status. The completed 398-case wrapper used an explicit post-result process exit after confirming zero remaining threads; this distinction is recorded rather than attributing an unobserved normal-shutdown exit.

`git diff --check` passed after the implementation review. Repository knowledge validation returned `VERIFY: 0 findings` (exit 0). Final live read-only checks are recorded below.

## Acceptance state and remaining work

Installed source/artifact identity, GTK binary startup self-check, live catalog query, Web static serving/auth/capability behavior, UI fixture behavior, and the full test suite are verified. A screenshot/visual pass and user-driven GTK interaction are still pending. Web/TUI/GTK parity is partial by design because the capability matrix does not yet have safe client workflows for all existing mutations. No reboot, Activity launch, monitoring enablement, desktop lifecycle mutation, SSH lifecycle change, audio change, or PRoot mutation was performed. P3 remains in progress/unqualified and P4 remains gated by the existing ownership, boot, Shizuku, and PRoot evidence gaps.


## Final live read-only follow-up — 2026-10-19

All commands ran in Native Termux at `/data/data/com.termux/files/home/ternuxx`, over the existing development SSH session on port 8022.

- `python3 -m tools.repo_knowledge verify` — exit 0; `VERIFY: 0 findings`.
- `./tx --json status` — exit 0; display `:1`, session `running`, supervisor/X11/XFCE `live`, Android GUI visibility `unknown`, audio owner `external`. No Activity request was made.
- `./tx --json proot status` — exit 0; Debian distribution installed; a host PRoot process was observed but ownership remained unverified; guest was not entered.
- `./tx --json ssh inspect` — exit 0; 8022 listener PID mapping unknown and config owner unknown; 8023 service `ternuxx-sshd` running under Runit, effective bind `127.0.0.1:8023`, SSH banner probe ready, socket PID mapping blocked by permission denial.
- `python3 scripts/management_desktop_bridge.py monitor` — exit 0; monitoring `enabled=False`, interval `300` seconds, Activity launch policy disabled, focus polling disabled.
- `./tx --json management gui-monitor status` — exit 2 because that is not a supported CLI command; no state change occurred. The valid read-only bridge query above was used instead.

The PRoot, GUI session, and SSH services were inspected only. No graphical window was opened, so the newly installed GTK app's rendered appearance and user interaction remain unverified. The Termux:X11 app was not launched or foregrounded.

## Evidence

Phase: `P3`

P3 management-interface progress evidence: catalog v2 category navigation is wired through Web, TUI, and the installed Native GTK4 client; focused interface tests and the complete Native Termux suite passed as recorded above. Native live inspection confirms the GUI process/session is running, the optional Activity/focus monitor remains disabled, and SSH/PRoot ownership limitations are explicit. This work advances P3 management capability but does not qualify P3 or unblock P4.
