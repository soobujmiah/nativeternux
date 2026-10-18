# Native continuity, service recovery, and Wake Lock status

**Status:** Core native CLI and live service slice implemented; owner-operated
reboot observed, with automated service/authentication verification partial.
**Current test:** `TERN-20261017-RB03` (`boot_observed`; verification outcome
`verified_reboot_partial`; readiness remains `NOT_READY`).

RB02 remains preserved as an earlier same-boot inconclusive observer attempt.
The owner opened Termux:Boot once. Although the `pm path` wrapper fails on this
device, the direct `cmd package path` query now reports the Termux:Boot package
present. Package presence does not prove first-launch setup; RB03's changed-boot
observer record now confirms Termux:Boot script execution, while automated
service/authentication verification remains partial.

## Implemented components

- Native private checkpoints use a versioned schema, unique test IDs/nonces,
  pre-reboot boot ID, repository/task metadata, required post-boot checks and
  recovery instructions. Writes use a private lock and atomic same-directory
  replacement; checkpoint files are mode `0600`, private directories mode
  `0700`. `automatic_resume` is always false.
- A native boot observer records a matching pending test without starting an
  agent or arbitrary task. It distinguishes a changed, same, or unavailable
  boot ID. The 2026-10-18 owner-operated reboot changed the boot ID and the
  observer recorded it; the automated observer did not identify sshd or
  service health, so the verification remains partial.
- An allowlisted local management service exposes continuity, boot status,
  SSH inspection and Wake Lock status/acquire/release operations to the CLI.
  It is not an HTTP server; GUI and Web UI callers do not exist yet. Arbitrary
  shell execution is not exposed.
- Native `termux-services`/runit supervises one Ternuxx-owned SSH daemon using
  a separate loopback-only candidate config. Only that custom service is
  enabled. The official Termux:Boot entry starts the service supervisor, then
  checks readiness; the evidence observer runs separately.
- The Wake Lock coordinator stores private owner leases, checks process
  identity, drops stale process/boot leases, serializes writes, and releases
  the global Termux lock only after the last registered Ternuxx owner exits.
  The native SSH supervisor owns a persistent lease; `x.sh` uses the
  `proot.desktop` lease for its own lifecycle.

## Live target-device evidence (2026-10-17)

- Termux `0.119.0-beta.3`; native Python `3.14.6`.
- Existing unmanaged `sshd -p 8022` had wildcard IPv4/IPv6 effective policy.
  Its process was stopped only after the candidate on `8023` passed syntax,
  effective-policy, host-key, authenticated-connection, and native-repository
  checks. The original SSH config and host keys were not changed.
- Candidate `$HOME/.config/ternuxx/sshd_recovery.conf`: `Port 8023`,
  `AddressFamily inet`, `ListenAddress 127.0.0.1`; existing host-key paths;
  password, keyboard-interactive, and public-key auth allowed. Candidate
  `sshd -t` passed; `sshd -T` reported loopback only. The daemon log reported
  `Server listening on 127.0.0.1 port 8023`; authenticated same-device PRoot
  access succeeded before and after the old listener stopped. Host-key
  fingerprints matched the existing Termux host identity. Android procfs TCP
  tables are inaccessible and `netstat` reports no TCP support, so kernel
  socket enumeration and independent external-network probing are unavailable.
- `sv-enable ternuxx-sshd` enabled the single managed service; repeated enable
  kept the same runit service PID and the exact candidate daemon process count
  remained one. Package-provided `sshd` and `ssh-agent` services remain down.
- The service acquired `native.sshd`. A live acquire/release and a complete
  isolated `xgo` lifecycle added then removed `proot.desktop`; afterward only
  `native.sshd` remained and the SSH service stayed up. The coordinator
  reports Android's actual global lock-holder state as `unknown`; owner lease
  behavior, not platform-level lock state, is what was observed.
- Native `~/x.sh` is a local Termux home script, outside a Git repository.
  Its verified original backup is
  `~/x.sh.ternuxx-backup-20261017T163623Z`, SHA-256
  `196edaa59a8e7990198781a3551058b0c29d67961bad47d816102374fe90734a`.
  Only direct Wake Lock acquire/release calls changed. Shell syntax passed and
  `xgo` started X11/XFCE, then its own test session exited. Existing PRoot
  process remained alive. XFCE logged optional systemd/DBus/colord and Android
  procfs warnings; full desktop quality is not release-qualified. Launcher
  cleanup still broadly terminates X11/virgl/PulseAudio and must not be used
  while unrelated sessions are active.
- The native checkout remains at
  `soobujmiah/ternuxx`, branch `main`, commit
  `1a891faabc925136c1801f40194b0969d28041df`, with its pre-existing dirty
  state preserved. The PRoot rootfs and separate Ternux repositories were not
  changed. `db` remains a direct PRoot terminal alias; the existing PRoot
  process was present during the GUI lifecycle test.
- `$HOME/.termux/boot/00-ternuxx-services` is installed and executable. The
  older `ternuxx-recovery` observer remains. The Android Termux:Boot app was
  reported present in earlier device evidence, but current package-manager
  queries from Termux fail and the required first app launch/receiver state
  was executed during the owner-operated reboot on 2026-10-18, as recorded by
  RB03. The verification outcome is partial; a later read-only Doctor saw the
  managed service running and a separate loopback SSH probe authenticated to
  port 8023, but the observer did not ingest these later checks. Automatic
  startup and kernel listener ownership remain unverified by RB03. See the
  [postboot verification record](../evidence/2026-10-18-postboot-native-ssh-verification.json).

## Verification evidence and limits

The current host unit/mock suite includes Wake Lock ownership, management API,
checkpoint privacy, observer behavior, SSH diagnostics, and native service
script tests. Earlier suite state was 35 passing tests before these new tests;
the current full-suite result must be recorded in the dated implementation
evidence after rerun. Mock tests do not establish Android behavior.

The live pre-reboot test established the service/config/authentication and owner-lease
behavior described above. The later Android reboot changed the boot ID and the
Termux:Boot observer ran. A later authenticated loopback probe confirms the
service is reachable now, but the checkpoint's automated service/authentication
verification remains partial and does not prove automatic service startup or GUI
visibility at boot. No GUI/Web UI management client exists. A full
JSON Schema validator is not installed in the current development environment;
JSON syntax and application-level record validation are used unless a
validator becomes available.

See [the reboot guide](../testing/REBOOT-RECOVERY-GUIDE.md) and dated evidence
report for the current readiness gate, recovery steps, and test classifications.
