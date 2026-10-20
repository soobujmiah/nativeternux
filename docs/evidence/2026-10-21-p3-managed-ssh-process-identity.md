# P3 managed SSH process identity recheck — 2026-10-21

Phase: `P3`

## Scope

This increment separates the Ternuxx runit-to-`sshd` process identity from TCP listener ownership. It is read-only against the live Native Termux service. No SSH config, service, boot helper, GUI, Debian guest, or device setting was changed; no process was restarted and no reboot was performed.

## Implementation

`ssh.inspect` now reports `managed_service.process_identity` independently from `listener_daemon_correlation`. The process check accepts only the current-UID `runsv ternuxx-sshd` parent, its `bash ./run` child in the exact fixed service directory, and a direct same-UID `sshd -D -e -f <managed-config>` child. It checks PID/start-time identities again before reporting `verified`. An unreadable or incomplete procfs view stays `unknown`; an observable mismatch reports `not_verified`. This does not infer a port from the process command line.

Doctor exposes process identity and listener-to-port correlation as separate fields. An observable process-chain mismatch is a warning; unavailable procfs evidence remains explicit without claiming a listener owner.

## Evidence

Native Termux:

- Runtime was Native Termux on Android 16 / `aarch64`, Termux `0.119.0-beta.3`, checkout `$HOME/ternuxx`.
- Read-only `/proc` inspection observed the `runsv ternuxx-sshd` parent, the fixed `bash ./run` wrapper, and the managed `sshd -D -e -f $HOME/.config/ternuxx/sshd_recovery.conf` child. All three reported the exact service-directory working directory.
- `./tx mng doctor --json` reported `NTX-SVC-001` severity `pass`, managed process identity `verified`, config syntax `valid`, and an SSH banner at the configured loopback endpoint.
- The same report kept listener-to-port correlation `unknown` because `/proc/net/tcp*` returned `permission_denied`. Doctor overall remains `warning` because the separate native SSH 8022 config reports wildcard bind and password authentication; that policy was not changed.
- The existing owner-started 8022 development shell and managed 8023 service were left running. No external network reachability was tested in this increment.

## Verification

- `python3 -m py_compile lib/ssh_diagnostics.py lib/doctor_report.py` — passed.
- JSON schema parse with `python3 -m json.tool` — passed.
- `git diff --check` — passed.
- Focused SSH diagnostics and Doctor tests — **40/40 passed**, including exact service-directory validation and the warning on an observable process identity mismatch.
- `bash scripts/repo_test.sh` on Native Termux — **638/638 passed** in 93.351 seconds.
- `python3 -m tools.repo_knowledge verify` — **0 findings**.

## Remaining boundary

This verifies the managed process chain, not kernel socket ownership. Listener inode-to-port mapping remains unverified on this device while Android denies the TCP procfs tables. P3 remains active; cold-boot/Termux:Boot delivery is still unqualified and remains outside this read-only check.
