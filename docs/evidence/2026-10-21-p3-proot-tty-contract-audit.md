# P3 interactive PRoot TTY ownership contract audit — 2026-10-21

Phase: `P3`

## Evidence

Reviewed `lib/proot_sessions.py`, `tests/test_proot_sessions.py`, `docs/architecture/PROOT-SESSIONS.md`, and the P3 gate in `docs/ROADMAP.md`. This is a source/fixture audit only; it did not enter the Debian guest, create a live TTY login, or signal a PRoot workload.

The checked contract covers:

- Host process ownership by PID, process start ticks, session/process-group leader, same host UID, per-session marker, and exact rootfs/launcher device+inode.
- Guest identity through fixed `sbj` login arguments, numeric UID/GID parsed from the selected rootfs passwd file, and rootfs working-directory device+inode. Ambiguous or missing evidence fails closed.
- Fixed command argv and a controlled launch environment. No caller shell string is accepted; inherited `LD_*`, display, graphics, and audio overrides are stripped, then only validated display/audio/backend arguments are added by the selected Native handoff.
- Foreground TTY requirement, input/output relay, `SIGWINCH` window-size forwarding, saved/restored terminal attributes and handlers, master-PTY cleanup, and persisted exit status.
- No detached attach/reconnect support. Stop can send `SIGTERM` only to the freshly revalidated recorded Ternuxx session process group; it waits boundedly and never sends a force signal. Unknown/live-unverified records are retained without signaling or adoption.

`python3 -m unittest tests.test_proot_sessions -q` passed **34/34** on Native Termux. The full Native suite on the same source commit passed **638/638**. `python3 -m tools.repo_knowledge verify` returned **0 findings**.

## Live qualification remains separate

The latest project evidence records three TTY-bound login attempts that failed before exposing a guest shell: the launcher/process marker and process group were observed, but the expected guest cwd and numeric guest identity checks did not match. No shell input was sent. After each attempt, the PID was proven absent and its record reconciled by an exact preview; no process signal or rootfs repair occurred. The failure is documented in [PRoot session architecture](../architecture/PROOT-SESSIONS.md). Therefore the contract is fixture-verified, while normal live interactive TTY usability, detach/reconnect, and general PRoot workload management are not qualified.

P3 stays active. The native SSH process-chain check is verified separately; its TCP listener-to-port mapping remains unknown because procfs is permission-denied. Native cold-boot delivery remains unqualified and owner-window gated.
