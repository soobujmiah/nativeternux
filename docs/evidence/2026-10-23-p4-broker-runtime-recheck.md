# P4 persistent terminal broker runtime recheck

Date: 2026-10-23
Runtime: Native Termux through SSH 8022

## Observed

- Runit service: $PREFIX/var/service/ternuxx-terminal-broker
- Exact scoped service restart returned PID 17148; runit status reported it running.
- Installed service run script and repository run script SHA-256 both matched: cd6a3f107bad6bb434ca6770ac3f28de8386b8afa582f45809d7c45855881eb4.
- Shared operation terminal.broker.status returned ok=true, pty_relay=not_connected, generation 721666220699389682.
- proot.sessions.list returned nine historical records; all nine were stopped, and no guest session was started by this check.
- The broker service module runs from the Native checkout under $HOME/ternuxx. It was restarted after proot_sessions.py changed, so the new process imports current repository source.
- The existing owner-managed Codex PRoot session, Native desktop, SSH 8022/8023, and default rootfs were not targeted by the broker restart.

The Web terminal replay remains covered by [the live replay evidence](2026-10-22-web-terminal-replay.md), which passed start, browser I/O, observed resize, detach, reattach, exact close, and preservation checks on the separate replay guest. This does not qualify every viewport or a permanent Web listener.

## Result

Persistent Runit wiring and the current idle broker process are verified. The Web terminal client lifecycle passed on its isolated replay target. P4 still has other open gates, including GTK shortcut-action human interaction, full shortcut wizard/client parity, safe VirGL cleanup, broken-rootfs and cold-boot qualification, and the full source/document audit.
