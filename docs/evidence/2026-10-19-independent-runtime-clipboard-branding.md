# 2026-10-19 — P3/P4 independent PRoot and Management Center continuation

Phase: `P3`

## Evidence

This report records Native Termux live observations and source/test validation for the current P3/P4 continuation.

## Runtime baseline

- Work was performed through the owner-managed Native Termux development SSH on port 8022 in `/data/data/com.termux/files/home/ternuxx`; Native Termux `$PREFIX` was `/data/data/com.termux/files/usr`.
- Branch `main`, HEAD `69e378e`; worktree already contained 133 status entries (70 tracked dirty) before this increment. Existing edits were preserved; no reset, cleanup, or commit.
- `./tx proot status --json` returned installed distro `debian`, `guest_entered:false`, `read_only:true`, ownership `unverified`, and one host process candidate with unverified association.
- `proot-distro list` shows the installed Debian distribution. The existing rootfs candidate at `$PREFIX/var/lib/proot-distro/containers/debian/rootfs` is a directory owned by the Termux UID. The `proot-gui0.sh` source explicitly disables a new `:0` desktop start.
- Read-only `tx proot gui status` reported a schema-v2 session record at `~/.local/share/ternuxx/proot-display0/session.json` as `running` on `:0`. The record is a regular file, owned by the Termux UID, mode 0600. Its recorded supervisor PID 16541, X11 PID 16550, and desktop PID 16616 were all absent from `/proc` during inspection. The record was not changed and no process was signalled.
- The recorded `:0` state and installed Debian rootfs do not prove that the old `db`/`x.sh` workflow, current Ternuxx app dispatch, and Ternux-owned workloads can safely share that rootfs concurrently. Independent full-guest lifecycle remains unavailable pending an explicit rootfs/process ownership adapter and concurrency safety qualification.

## Implemented

- `tx web` now passes its memory-only bootstrap secret to `termux-clipboard-set` via stdin. The secret is not placed in the URL or routine output. If clipboard copy fails, the server closes and does not disclose the secret. `--show-secret-on-clipboard-failure` opts into a terminal fallback.
- The Termux clipboard and browser opener binaries are installed in Native Termux. No live clipboard write or browser launch was performed, preserving the owner's current clipboard and focus.
- Added the exact tagline and portfolio link in the Web footer, compact TUI header, and GTK Management Center footer/About area.
- Updated `tx web --help`, architecture/API documentation, and focused tests. Existing Web authorization and loopback behavior were not changed.

## Verification

- Focused tests: `python3 -m unittest tests.test_management_http_runtime tests.test_terminal_ui -v` — 28/28 passed, 0.445 seconds, exit 0.
- Live GUI/PRoot lifecycle, browser viewport rendering, clipboard contents, and application windows were not changed or visually tested.
- Focused tests: `python3 -m unittest tests.test_proot_gui_routing tests.test_management_http_runtime tests.test_terminal_ui -q` — 30/30 passed, 0.750 seconds, exit 0.
- Full Native Termux suite: `bash scripts/repo_test.sh` — 414/414 passed in 85.753 seconds, exit 0.
- GTK deployment: `bash scripts/install-management-center.sh` exit 0; installed GTK 4.24.1 `--self-check` exit 0. Installed binary SHA-256 `7042d1f2e6e11c5c9cf933ce1da96eb927d846871ac61da28bc7004f14250912` and launcher SHA-256 `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd` match the generated identity record. Source C SHA-256 `1b23ad0f371e957c3b4c724560fb67536b32ae5a6590b367dbb61d1ef2a232e1`; bridge hash matches the existing installed identity.
- Static validation: Python compilation, shell syntax, HTML parser, and `git diff --check` all exit 0. `python3 -m tools.repo_knowledge verify` reported 0 findings.
- Installed `$PREFIX/bin/tx web --help` and `$PREFIX/bin/tx proot gui status` exit 0. GUI monitoring read-only status reports disabled, scheduler disabled, no Activity/focus probe, no check timestamp, and Linux desktop running.
- A passive loopback socket connect to `127.0.0.1:8765` succeeded after the test run; this agent did not start or stop that listener, authenticate to it, or attribute it to a specific owner. Browser tooling was unavailable, so no viewport screenshots/overflow checks were made.
- No Web server, GUI Activity, desktop, audio service, SSH service, PRoot workload, or reboot was started/stopped. `ssh.inspect` reports managed 8023 configuration on loopback with matching source/installed service-definition hashes and an SSH banner, while listener-to-process observation is permission denied; 8022 is wildcard configured and its owner/listener correlation remains unknown.

## Open items

- PRoot owner/lifecycle status remains blocked: the installed Debian rootfs is shared legacy infrastructure; no exclusive Ternuxx ownership, safe simultaneous use, or complete cleanup contract is verified.
- `:0` record says running while its recorded processes are absent. It remains untouched; it needs a supported identity-aware read-only reconciliation path before any recovery is attempted.
- Actual Android clipboard copy and authenticated browser workflow remain unverified because the test would replace private clipboard contents and open/foreground a browser.
- Web mobile visual test and GTK visible UI test remain unverified where no browser automation or owner-operated screenshot qualification was available.
