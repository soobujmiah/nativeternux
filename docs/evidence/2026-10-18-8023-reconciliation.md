# 8023 reconciliation gate — 2026-10-18

- **Baseline commit:** `3ad08378f6a39b509cacd93780e99419b968d783` (`main`, synchronized before edits).
- **Environment:** Native Termux on device over the owner-started SSH 8022 development shell; `$PREFIX=/data/data/com.termux/files/usr`; repository `$HOME/ternuxx`.
- **8022:** left untouched; remains separate manual development access.
- **Source drift:** source run file hash `1dc73681a09d606b265db8add60e4870c144a50b31da7b3ba0a7db3c7ab932f6`; installed file hash `ec59008a2cbe3a8b7d5e13c72e0a8274d28ae238cd02ff1750a5901a683efb69`. Installed bytes match historical same-path Git blob at `025023e`. Same service ID and matching config path; exact diff consists of four old/current environment-variable, log-directory, and chmod-target lines. **Cause: stale deployment**, not a different service definition.
- **Read-only runtime:** Runit `sv status` reports `run` (wrapper PID 13061); visible process ancestry includes runsv PID 13043 and sshd PID 13449, all Termux UID. Managed config mode 0600 and `sshd -t` passes; effective `ListenAddress 127.0.0.1:8023`. Service log records listening on that address. No service action occurred.
- **Listener ownership:** `UNVERIFIED`. Direct reads of `/proc/net/tcp`, `/proc/net/tcp6`, and the service PID network tables fail with `PermissionError`. `/proc/13449/fd` exposes socket inode 117876, but `lsof -nP -a -p 13449 -i` and `lsof -nP -iTCP:8023 -sTCP:LISTEN` returned exit 1 with no rows, so the inode cannot be mapped to port 8023. Listener ownership remains unverified. A banner/config/log are not ownership proof.
- **Deployment workflow:** implemented preview/hash/diff/validation, exact-plan apply, atomic write, private snapshot, journal, automatic rollback, explicit rollback, and generic recovery routes. Seven fixture tests pass, including partial apply, failed automatic restore, partial explicit rollback, and recovery. Full Native Termux suite passed 308/308 at final code state via `bash scripts/repo_test.sh`.
- **Applied reconciliation:** exact preview plan `b9c16f284f4aad2f6b3f12a4addd4337e0a92c747590dd2f780b452b0546f4e4` applied as operation `fffd3f74f9ce416f8b094a2cde019ce1`. Installed source hash now matches current source. Runit status remained `run` with PID 13061; loopback banner `SSH-2.0-OpenSSH_10.6` returned. SSH configuration hash stayed `c8441fabab4c7ee2dcc5c69fb03f11d3ac74062a6644cfc3b8b8605e2c48b609`. Rollback preview was read-only and showed the reverse diff to prior hash `ec59008a2cbe3a8b7d5e13c72e0a8274d28ae238cd02ff1750a5901a683efb69`; snapshot remains available. Device rollback was not applied.
- **Lifecycle qualification:** plan added; start/stop/restart/readiness/duplicate/failure cases remain untested on device. Reboot and reboot readiness remain `UNVERIFIED`; no reboot requested or performed.
- **PRoot preservation:** Debian 13 installed and `sbj` login plus `db`/`droot`, `x`, `xgo`, `killx` were inspected read-only. No PRoot files, packages, launchers, GUI or rootfs changed.
- **Cross-environment limit:** PRoot-to-native SSH authentication on both 8022 and 8023 was unavailable in this session; implementation and tests ran through authenticated Native Termux 8022 shell. No credential was stored. The active 8022 shell remained connected throughout reconciliation.


## Read-only bind follow-up — 2026-10-18 15:35 UTC

ADB `toybox netstat -ltnp` confirmed actual binds: 8022 on `0.0.0.0` and `[::]`, 8023 on `127.0.0.1`. The scoped process listing shows the 8022 sshd process and the 8023 Runit wrapper/sshd child under Termux UID. This is not socket ownership proof: `ss -ltnp` and `netstat -p` return no PID, and `/proc/13449/fd` is denied. The 8023 service remains running and was not restarted; 8022 was not changed. Exact socket-to-process mapping remains UNVERIFIED. See [continuation evidence](2026-10-18-live-session-state-reconciliation.json).


## Listener ownership resolved — 2026-10-18

The earlier permission limitation was resolved without elevated access or service changes. ADB shell supplied `/proc/net/tcp*` socket inodes, and Native Termux UID 10490 could read its own sshd FDs. PID 16337 FD 7 (`socket:[135149]`) matches `0.0.0.0:8022`; FD 6 (`socket:[135147]`) matches `[::]:8022`. Managed sshd PID 13449 FD 6 (`socket:[117876]`) matches `127.0.0.1:8023`; PID 13449 is the Runit service child (service PID 13061). Listener ownership and bind scope are VERIFIED for this observation. The service remained running and no lifecycle or SSH policy change was made. 8022 external reachability and reboot readiness remain untested; reboot still requires explicit owner approval. See [updated live evidence](2026-10-18-live-session-state-reconciliation.json).


## Later lifecycle qualification supersedes earlier checkpoint

The no-lifecycle and ownership-`UNVERIFIED` statements above accurately describe the earlier reconciliation checkpoint only. The later live qualification on the same date verified the 8023 listener inode against the managed sshd process, authenticated loopback readiness, two stop/start cycles, repeated-start idempotence, and 8022 continuity. It also fixed the service/CLI state variable mismatch through preview-first deployment. See [later lifecycle evidence](2026-10-18-8023-lifecycle-qualification.md). Reboot readiness remains `UNVERIFIED`.
