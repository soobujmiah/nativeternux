# P4 persistent broker and Web terminal follow-up - 2026-10-22

Phase: `P4`

## Scope and preservation

This increment was implemented in the Native Termux checkout at `$HOME/ternuxx` through SSH port 8022 and is paired with the canonical repository worktree. P4 remains in progress. The owner-provisioned `tx db` guest was not entered, started, stopped, or changed; no Debian rootfs files were inspected or written. The running Ternuxx Management Center process was left running. The existing Native broker service is the only persistent service changed in this increment.

## Persistent broker service

Added a fixed Runit service definition at `scripts/termux-services/ternuxx-terminal-broker/run` and preview-first install/status commands under `tx terminal service`. The service runs the Native broker from the checked-out Ternuxx source. It does not start a PRoot guest, enable Termux:Boot, or acquire a Wake Lock.

The first service start encountered an orphan Unix socket left by an earlier foreground broker. Runit was paused for the exact new service. The socket was confirmed to be a same-UID mode-0600 socket at the exact private Ternuxx state path; a connect attempt returned `ECONNREFUSED`; its inode identity was rechecked immediately before removing that one orphan socket. No guest path was accessed. The Runit service then reached `running` and remained available at the final recheck. `tx terminal status` returned `ok: true`, a broker generation, and `pty_relay: not_connected`. The installed Runit `run` SHA-256 matches the repository source (`cd6a3f107bad6bb434ca6770ac3f28de8386b8afa582f45809d7c45855881eb4`).

## Authenticated Web terminal

Added a lazy terminal dialog to the existing Management Web UI using locally vendored xterm.js 6.0.0 and FitAddon 0.11.0 assets with their license files. SHA-256: xterm.js `14903579ff54664cd72f8e8699e6961a6272c21863ec1c3b118cdc8af5d4a972`, xterm.css `854a7c0fb70e8b1a083c16797ab827299fb18744f5ad34f227b48337e33293c6`, FitAddon `ba3ea256ce0620a0992a197d6c9baea64823fc93d8da07a9e366ca9943c18527`. The Web transport uses CSRF-protected typed operations, exact origin/session binding, a short-lived single-use attach ticket, fixed session IDs and broker generation, and detaches on close/revoke/expiry. Opening the UI does not start a guest. Starting and stopping a managed session require a fresh exact preview and confirmation. Generic operation dispatch does not accept the terminal channel operations.

A runtime import guard originally blocked the Web server after terminal scopes were introduced. It now explicitly accounts for the terminal preview, channel, attach, input, resize, output, detach, and close operations while retaining the existing narrow mutation allowlist. `python3 lib/management_http_runtime.py --help` now imports and renders successfully.

## Evidence

- Focused Native Termux tests: `tests.test_terminal_service_deployment`, `tests.test_management_http_runtime`, `tests.test_management_http_adapter`, and `tests.test_management_http_server` — 39/39 passed.
- Python bytecode compilation passed for the changed runtime, adapter, server, service, broker, deployment, and CLI modules.
- Full Native Termux repository suite: 700/700 passed in 120.414 seconds after updating two obsolete expectations for the new scoped terminal operations.
- `git diff --check` passed.
- Native runtime identity: Android 15 kernel, `aarch64`, Termux prefix `/data/data/com.termux/files/usr`, checkout `$HOME/ternuxx`.
- Broker service is live and source-matched; no Ternuxx managed PRoot session is attached.

## Remaining work and limits

Follow-up visual review: Native Firefox ESR was launched through the named PRoot app action on X11 `:1`, and the authenticated management page rendered. The authenticated 752x1124 capture exposed category labels overflowing into the resource pane; `lib/management_web_ui.html` now wraps category labels and uses a zero-minimum content column at the two-column breakpoint. The first authentication succeeded. A later reload rejected the one-time credential, so the post-fix authenticated visual result remains unverified. This does not verify a managed guest attach. The review is documented in `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md`. The GTK Management Center visual review is recorded in [the earlier P4 GUI evidence](2026-10-22-p4-terminal-client-and-gui-review.md); its installed artifact identity matches the Native C source and desktop entry is present. A live managed interactive guest login was intentionally not started to preserve the existing guest and rootfs. P4 remains open until an owner-approved disposable/managed test guest can complete the interactive attach flow and the Web screen receives visual review. No P4 completion gate was claimed.
