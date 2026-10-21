# P3 pre-reboot checkpoint - RB08 - 2026-10-21

Captured: 2026-10-21T23:57:40+06:00 from Native Termux Ternuxx checkout over owner-managed SSH development channel port 8022. No repository record was written from PRoot. Owner said they are initiating Android normal reboot. Agent did not reboot device or invoke a boot script.

## Checkpoint identity and repository baseline

- Private checkpoint: TERN-20261021-RB08; state prepared; readiness NOT_READY; automatic resume false.
- RB07 retained as history: status already boot_observed / NOT_READY, earlier observer result verified_reboot_service_unqualified. RB08 is the unique checkpoint for the upcoming reboot.
- Native checkout: branch main, HEAD dfa3f63; 21 modified tracked paths and 10 untracked paths at capture. Existing owner changes preserved and uncommitted. No commit or push.
- Checkpoint nonce and boot ID are private runtime data and intentionally omitted.

## Latest Native pre-reboot observations

| Area | Observation | Post-reboot check |
|---|---|---|
| Native boot helpers | Both helpers match source, mode 0700; status is read-only; device delivery not qualified. | Compare source/install identity and mode; inspect fixed observer logs for fresh RB08 record. |
| Cron boot entry | Identity match, integration script_configured; Termux:Boot app/package/receiver enabled. Last result is historical CLI could not be executed at 2026-10-21T17:23:36Z. | Confirm whether boot execution writes a new result; never run helper manually. |
| Cron scheduler | Stopped, zero jobs; no scheduler start/stop for checkpoint. | Record state as found; do not start manually. |
| Managed SSH 8023 | Runit service running; identity and definition verified; config valid; effective bind loopback-only, public-key auth only; banner probe succeeds. Listener-to-port correlation unknown because procfs/netlink observation denied. | Recheck service/config/loopback SSH; keep socket ownership unknown if denied. |
| Development SSH 8022 | Evidence session is connected through 8022. SSH inspection reports wildcard bind and password auth enabled; listener owner and external reachability unknown. No policy changed. | Owner reconnects through existing 8022 channel; do not alter policy. |
| Native XFCE :1 | Running; supervisor, X11 and XFCE live; GUI foreground visibility unknown. Earlier stale session was restored after RB07 snapshot. | Record status without restarting. |
| Debian PRoot | Inventory says Debian installed, guest/session ownership unverified, and no guest entered. Recorded sessions stopped/released; host process candidates unverified. | Repeat inventory only; preserve unknown processes and do not enter guest. |
| Wake Lock | Coordinator reports registered owner native.sshd; Android platform lock state unknown. No acquire/release action. | Recheck without changing ownership. |
| Doctor | Read-only: 15 pass, 16 info, 1 warning, 0 errors. Sole warning is 8022 wildcard/password config; listener owner/external reachability unknown. | Repeat read-only report; do not change SSH policy. |
| Android boot/accelerators | Termux:Boot package and receiver enabled; system startup policy unknown. GPU workload probes skipped; NPU execution unverified. | Record boot observation; do not run graphics or inference workloads. |

## Reproduction and boundaries

Read-only commands were run from ~/ternuxx via port 8022: ./tx status --json, ./tx mng doctor --json, ./tx mng boot helpers status --json, ./tx mng boot cron status --json, ./tx mng cron status --json, ./tx ssh inspect --json, ./tx wakelock status --json, ./tx mng proot status --json, and ./tx reboot status. RB08 was prepared with ./tx reboot prepare; it initialized NOT_READY and disabled automatic resume. Only sanitized checkpoint fields are recorded.

After Android starts, reconnect through 8022 and inspect/verify/resume-info for RB08. Repeat the read-only checks above. Do not use PRoot to write records, execute boot scripts/observers manually, start Cron, alter SSH or Android settings, restart GUI, enter Debian, or repeat reboot automatically. Keep P3 open if any required evidence is failed or unknown.
