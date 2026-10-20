# P3 managed SSH 8023 read-only service check — 2026-10-21

Phase: `P3`

At 2026-10-20 18:45 UTC (2026-10-21 00:45 Asia/Dhaka), the managed CLI endpoint was reached over SSH to `127.0.0.1:8023` using the already provisioned key in noninteractive BatchMode. The endpoint accepted authentication and returned successful read-only CLI responses.

- `tx mng boot helpers status --json`: both installed helper files match checked-in source; both are mode 0700.
- `tx mng boot cron status --json`: the dedicated Cron script matches source; Termux:Boot package/receiver are enabled; scheduler reports running; actual device-boot delivery remains unverified.
- No boot file, service, scheduler, SSH setting, GUI process, PRoot session, or Debian guest state was changed.
- No reboot or application interaction occurred.

This verifies current loopback SSH authentication and CLI read-only behavior only. It does not prove socket-to-PID ownership or Android cold-boot delivery; those remain open P3 evidence items.

## Evidence

Command: `ssh -p 8023 -o BatchMode=yes 127.0.0.1 'cd "$HOME/ternuxx" && ./tx mng boot helpers status --json && ./tx mng boot cron status --json'`. The command completed with exit status 0; no credential or key material was recorded.
