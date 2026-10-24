# Native Web authenticated reload/reconnect — 2026-10-24

Phase: `P4`
Finding: `A18`
Result: fixed for browser reloads while the owning Native Web runtime and memory session remain alive. Runtime restart, expiry, and revoke still end the session.

## Implementation

I implemented a reconnect path for the authenticated loopback management page. Bootstrap consumes its one-time secret and sets the session bearer in an HttpOnly, SameSite=Strict cookie scoped to `/api/v1`; the bootstrap response no longer returns the bearer to JavaScript. The page reconnects with an exact-Origin POST after reload and obtains the CSRF proof again. The proof is HMAC-derived from the bearer and session reference using a random process-local key. Cookie authentication and legacy bearer-header authentication are accepted only when both credentials agree. Revoke clears the cookie.

The listener remains loopback HTTP, so the cookie has no `Secure` attribute. This design depends on the existing exact Host/Origin validation and loopback-only bind. Restarting the Web runtime creates a new HMAC key and loses in-memory sessions; the user must obtain a fresh bootstrap secret after restart or expiry. No durable session or credential storage was added.

## Verification

On Native Termux, the focused management HTTP/session tests passed (109 tests across HTTP adapter/runtime, session manager, and management service suites). The full repository command then passed:

```text
bash scripts/repo_test.sh
Ran 939 tests in 150.830s
OK
```

An earlier full-suite attempt had one timing-sensitive Cron daemon test fail to observe its scheduled record; that test passed by itself, and the subsequent full run passed all 939 tests.

I ran `tools/check_web_ui.py --distro ternuxx-replay-p4 --visible` against Firefox ESR 153.5.0 on Native X11 `:1`. It passed the authenticated page reload and reconnect, cleared bootstrap field, HttpOnly cookie visibility, catalog/search, 752px-requested responsive layout (actual viewport 742 CSS px), action controls, session inventory, and no-terminal-start checks. The only API operations observed were `management.catalog` and `proot.sessions.list`. No managed guest session started.

Firefox login can rewrite the PRoot-Distro-generated `etc/profile.d/termux-profile.sh` and `sysdata` in the guest. Before each live run, I snapshotted those exact paths in private Native temporary storage, then restored them and verified matching content, types, and modes. The final checker run reported `guest_state_rollback_exact: true`. The target was only the existing disposable `ternuxx-replay-p4` alias; the default Debian workload was refused by the checker.

## Visual record

The passing run saved these scoped Firefox screenshots:

- [Authenticated UI at the responsive viewport](2026-10-24-web-session-reload-reconnect-screenshots/web-752.png) — SHA-256 `8a54706222b43c67ef96f87fd5b44042850214774815164c6d4a00b2589f3885`
- [PRoot recovery action](2026-10-24-web-session-reload-reconnect-screenshots/web-proot-reconcile-control.png)
- [Shortcut restore controls](2026-10-24-web-session-reload-reconnect-screenshots/web-proot-shortcut-rollback-control.png)
- [Shortcut sync controls](2026-10-24-web-session-reload-reconnect-screenshots/web-proot-shortcut-sync-control.png)

The images were reviewed from the passing visible run. Their exact SHA-256 values are listed in `sha256sums.txt` beside the images.

This closes A18's same-runtime browser reload gap. It does not complete P4, qualify restart continuity, establish full Web mutation parity, or prove guest graphics/audio/package reproducibility.
