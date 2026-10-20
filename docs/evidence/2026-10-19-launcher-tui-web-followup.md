# Launcher, TUI, Web responsiveness follow-up — 2026-10-19

## Run identity and baseline

- Observed at Native Termux local time: 2026-10-19T20:06:22+06:00.
- Repository: $HOME/ternuxx; branch main; HEAD 69e378e; the worktree was already dirty before this increment. Existing user changes were retained.
- Runtime: HOME=/data/data/com.termux/files/home, PREFIX=/data/data/com.termux/files/usr; implementation and tests ran in Native Termux through the owner-managed development SSH 8022.
- Port 8022 inspection reported a daemon and wildcard bind configuration, but exact process/config ownership remained unknown. No 8022 operation was performed.
- Read-only tx ssh inspect --json: managed ternuxx-sshd is running under Runit, configured loopback-only at 127.0.0.1:8023, source and installed service definition hashes match, and the SSH banner responds. No SSH lifecycle operation was performed.
- Read-only tx status --json: GUI session :1, supervisor, X11 and XFCE are live; gui_visible=unknown. Android Activity/focus polling was not enabled.
- The local Web service at 127.0.0.1:8765 was not listening when checked. No Web UI session was started.

## XFCE/PRoot launcher diagnosis

The three Native Termux user menu entries inspected were ternuxx-proot-terminal.desktop, ternuxx-proot-files.desktop, and ternuxx-proot-shortcut-manager.desktop. Their existing Exec fields point to executable Native wrapper scripts under $HOME/ternuxx/scripts; all three pass desktop-file-validate (exit 0). The owner's $HOME/x.sh is an existing wrapper to scripts/proot-x11-app.sh; it was read and left unchanged.

The confirmed defect in this launch path was stale CLI naming: scripts/proot-x11-app.sh, the shortcut-manager wrapper, and shortcut command wrapper invoked $ROOT/ternuxx, which is absent in this checkout. The supported executable is $ROOT/tx. The same stale executable path was used by source-generated .desktop entries. Since the app wrapper checks CLI GUI status before PRoot dispatch, that missing executable caused the path to exit before invoking proot-distro or the target program. This is a source-proven cause for launch paths through these Ternuxx wrappers; it does not yet identify every entry named in the reported screenshot.

I updated the wrappers and generated entry to use the supported tx checkout entrypoint. The existing terminal and files entries are classified as conflict by the read-only shortcut catalog because their contents differ from the current generated template; they were preserved and not rewritten. The manager entry is reported installed. A freshly generated terminal .desktop entry validates (exit 0) and its Exec points to $HOME/ternuxx/tx management app launch terminal.

Post-fix read-only checks: ./tx status --json reports the live :1 display; a bounded Debian guest xdpyinfo through proot-distro login --shared-tmp --user <resolved-user> --env DISPLAY=:1 exits 0. Those checks prove pre-launch CLI/display access only; no GUI application was launched, so process startup, duplicate behavior, and window appearance remain unverified. The reported menu labels such as Blender (PRoot) and Firefox ESR (PRoot) were not found as matching entries in the inspected Native home, Termux system, or Debian guest .desktop directories. Their exact active menu source remains unresolved. Debian thunar, firefox-esr, blender, and xfce4-terminal executables resolve in the existing guest.

## TUI and shared capability contract

The TUI continues to load categories/resources from management.catalog and dispatch through management_service.dispatch. Navigation remains category left/right (or h/l), resource up/down (or j/k), / search, Enter status, h recovery history, v details, r refresh, a guided actions, and q/Esc quit. The selected resource now shows only its implemented guided controls. Existing handlers remain the authority: desktop start/stop confirmation; managed SSH 8023 start/stop with preview, impact and exact plan ID; GUI monitoring policy configuration; named PRoot app launch with session validation and confirmation; recovery history read. SSH 8022 remains read-only. Unsupported operations do not gain dummy toggles; they remain catalog/API/CLI-only or explicitly unavailable in the TUI. No mutation was applied.

## Web and GTK

The Web page now applies mobile rules at 760px and 380px: a single-column layout, wrapping header, width-bounded panels and fields, scroll-contained category navigation, stacked authentication controls on narrow viewports, and 44px touch targets. Existing viewport metadata and 15px base text remain. Existing connect/disconnect, refresh, search/filter, resource selection, health checks, monitoring, guided actions, history, and API-response controls remain bound to handlers in the shared HTTP API client. The responsive/event wiring regression checks are structural tests, not rendered layout measurements.

No browser engine, Node runtime, Playwright, or Selenium is installed in the verified Native Termux environment. The Web service was not running, so no browser viewport screenshots, measured overflow results, readability, or touch interaction were verified. The Web changes are implemented but visual mobile acceptance remains unverified.

GTK source/install identity was rechecked without opening its window:
- C source SHA-256: f4ed4af926fbec65b0655030c3a68590f3cde9e473691aea090af711861245ed.
- Bridge source SHA-256: 06fd6175e6b8d5cb3fdea4b88f1a33039de755b0fac4cdfe9e46047fcf942548.
- Installed binary SHA-256 matches its identity file: 87acf74192d81bdd0217a5171972ee0a0ee99d8655b34367144d6ebd17adaf3d.
- Installed launcher SHA-256 matches its identity file: e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd.
The GTK window was not opened; visual interaction remains unverified.

## Tests and checks

- Focused Native Termux suite: python3 -m unittest tests.test_proot_shortcuts tests.test_terminal_ui tests.test_management_http_runtime -v — 36/36 passed, 0.500 s, exit 0. One initial TUI rendering test failed because its fixture omitted the catalog's supported status operation; the fixture was corrected to match the catalog contract, then the focused suite passed.
- Full Native Termux suite: bash scripts/repo_test.sh — 408/408 passed, 80.718 s, runner exit 0.
- The full suite ran in fixtures and did not launch GUI apps or apply lifecycle operations.
- desktop-file-validate on the three existing menu entries: exit 0. Fresh generated entry validation: exit 0.
- bash -n on the four changed PRoot launcher scripts: exit 0.
- Bounded PRoot display query via xdpyinfo: exit 0.
- CLI GUI status: exit 0. CLI Center command with an unsupported status subcommand returned usage/error; this was an invalid inspection invocation, not a GTK runtime result. Installed/source identity was instead verified from the supported identity record and direct hashes above.
- Browser visual test: unavailable; no claim of responsive visual acceptance.
- No GUI app, Android Activity, PRoot workload, SSH service, audio service, boot behavior, or reboot was started/stopped/reconfigured. Existing PRoot rootfs/workspace and launchers were preserved.
- Port ownership remains split: 8022 is inspect-only and unverified as an owned service; 8023 remains managed, loopback-only and operational.
- P3 remains in progress/unqualified; P4 parity remains incomplete. Visual launcher verification and browser responsiveness measurements require the owner-operated GUI/browser check.

## Evidence

P3 remains in progress and unqualified; P4 parity remains incomplete. The machine evidence and test records above support this status.
\nPhase: `P3`\n