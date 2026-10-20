# Native Runit service status diagnostics — 2026-10-19

## Finding

The read-only `tx ssh inspect` report showed the managed `ternuxx-sshd` status as `unknown`, even though a direct `sv status` using the service directory reported it running. On this Termux Runit setup, `sv status ternuxx-sshd` fails because the service name is not resolvable from the default service directory; using `$PREFIX/var/service/ternuxx-sshd` succeeds and prints the absolute service path in the status line. The diagnostics parser only accepted the short service ID.

## Change

- `lib/ssh_diagnostics.py` now asks Runit for the exact fixed service directory under the detected Termux prefix.
- It accepts the exact absolute service path emitted by Runit, while retaining the short-name form for compatible Runit output. The parsed line is normalized before sanitized startup-timing analysis.
- The fixture asserts the absolute service path and returns the absolute-path status format.

## Verification

- Focused native SSH diagnostics tests: 11/11 passed.
- Live native `./tx ssh inspect --json`: managed service `running`; source/installed service definition hashes match; effective 8023 bind is loopback-only; SSH banner probe succeeds; startup timing is observed.
- Listener socket-to-process correlation remains `unknown` because native `/proc/net/tcp` and `/proc/net/tcp6` reads are permission-denied. The separate 8022 endpoint remains wildcard/password configured; no policy was changed.
- Historical full suite via managed loopback SSH 8023 passed 347/347 in 66.165 seconds. Following owner clarification that 8022 is the repo development shell, a fresh full suite via SSH 8022 passed 347/347 in 70.217 seconds; use 8022 for repo test qualification and 8023 for managed Ternuxx CLI/service behavior.

## Preservation

The checks were read-only. No SSH service/configuration, package, boot, desktop, Android setting, or Debian PRoot/rootfs state changed. The working tree remains uncommitted; earlier dirty work was preserved.
