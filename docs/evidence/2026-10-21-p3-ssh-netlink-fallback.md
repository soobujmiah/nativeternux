# P3 SSH listener diagnostic fallback — 2026-10-21

Phase: `P3`

## Change

Added a bounded read-only Linux `NETLINK_SOCK_DIAG` fallback for TCP listener inventory when either `/proc/net/tcp` or `/proc/net/tcp6` is incomplete. It requests only `TCP_LISTEN` records over IPv4 and IPv6, decodes the local address, port, and kernel socket inode, and feeds those records into the existing exact runit-process-tree FD correlation. Both address-family dumps must complete before the fallback reports a complete inventory. Permission denial, interrupted dumps, malformed responses, and partial results fail closed and cannot qualify ownership.

The fallback uses only Python's standard `socket` and `struct` modules. It adds no package dependency, does not alter SSH policy or services, and does not use process command lines as port evidence. The protocol structures and constants follow the Linux UAPI definitions for [`inet_diag_req_v2` and `inet_diag_msg`](https://github.com/torvalds/linux/blob/master/include/uapi/linux/inet_diag.h), [`SOCK_DIAG_BY_FAMILY`](https://github.com/torvalds/linux/blob/master/include/uapi/linux/sock_diag.h), and [`NETLINK_SOCK_DIAG`](https://github.com/torvalds/linux/blob/master/include/uapi/linux/netlink.h).

## Evidence

Source: `lib/ssh_diagnostics.py`; fixtures: `tests/test_ssh_diagnostics.py`; architecture: `docs/architecture/SSH-LIFECYCLE.md`.

## Verification and limits

- `python3 -m unittest tests.test_ssh_diagnostics -q` passed **15/15** using synthetic procfs and fake netlink responses.
- Fixtures cover IPv4/IPv6 listener decoding, exact request shape, complete multipart dumps, partial-procfs fallback, and permission denial.
- `git diff --check` passed.
- At the initial implementation checkpoint, no live netlink query had been made. The later native check is recorded below; it found permission denial for both procfs and netlink, so listener-to-PID ownership remains open.
- No SSH service/configuration, boot state, PRoot guest, active `tx db` Codex session, or 8022 connection was changed. No install, restart, reboot, commit, or push occurred.

P3 remains active. Cold-boot delivery remains a separate owner-window gate.

## Native Termux check

At `2026-10-21T08:07:06Z`, the installed `tx mng doctor --json` entrypoint dispatched to this checkout and returned `read_only: true`. The managed `ternuxx-sshd` process identity and loopback SSH banner passed, while listener-to-port correlation remained `unknown` with `tcp observation=permission_denied`. This is a live result from the diagnostic path; it does not establish whether Android denied `/proc/net`, the netlink socket, or both. The fallback therefore remains unqualified on this device, and no ownership or external reachability claim follows from the pass results.

The doctor reported no unresolved operation journal entries. It did report a stale recorded desktop session (`:1`) whose supervisor, X11, and desktop processes were absent. The doctor took no repair action. This desktop record is separate from the current Codex PRoot session.

No service, process, SSH configuration, boot state, PRoot guest, or active `tx db` session was changed. No reboot, installation, commit, or push occurred.

## Diagnostic provenance follow-up

The follow-up implementation keeps the compatibility field `tcp_listener_observation` and adds `tcp_listener_procfs_observation`, `tcp_listener_netlink_observation`, and `tcp_listener_source`. Doctor now includes those source fields in `NTX-SVC-001`. A second native read-only run at `2026-10-21T08:08:56Z` reported `tcp observation=permission_denied; procfs=permission_denied; netlink=permission_denied; source=none`. This identifies that both observation paths were denied, with no listener rows available. The SSH service process identity and loopback banner still passed independently.

This update ran Doctor against the live working tree. No automated test suite was run during this follow-up. `git diff --check` is the remaining static whitespace check.
