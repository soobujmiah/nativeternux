# Native Termux reboot recovery guide

# Current P3 reboot test — RB08 review, 2026-10-22

RB08's owner-operated restart was observed: the boot identity changed, the
matching Native observer record exists, the native service boot log reported
ready, and postboot read-only checks verified the managed 8023 service and an
authenticated loopback SSH client. The client ran inside the existing Debian
guest, but the service, host keys, authorized-keys file, config, and boot path
are owned by Native Termux. This did not make the service depend on PRoot.

The RB08 checkpoint remains `boot_observed`, `NOT_READY`, and
`automatic_resume=false`; its automated observer snapshot did not capture
managed-service health. Independent manual checks are documented in the
[P3 postboot exit audit](../evidence/2026-10-22-p3-rb08-postboot-exit-audit.md).
After RB08, current recovery modules were installed to the canonical
`$PREFIX/lib/ternuxx` path; the next boot is needed to observe that module
version executing. A separate pre-canonical module directory
was preserved. Do not invoke boot observers manually or resume tasks
automatically.

The generic Cron status field still says `actual_device_boot_delivery` is
`not_yet_verified`; the timestamped Native boot and observer records are the
direct delivery evidence for RB08. Android's system-wide background policy
and listener-to-port ownership remain unknown.

Historical preparation note: RB08 superseded RB07 for the restart and remains a private checkpoint. Its baseline is in [the RB08 checkpoint record](../evidence/2026-10-21-p3-pre-reboot-rb08-checkpoint.md). Do not reuse either checkpoint for another restart; prepare a fresh unique checkpoint if a future reboot test is needed. Do not invoke boot observers manually or resume tasks automatically.

**RB03 status: reboot observed; automated verification partial. No further reboot is needed to complete RB03.**
**Prepared test:** `TERN-20261017-RB03`
**Checkpoint:** native private storage at `$HOME/.local/share/ternuxx/continuity/reboot-tests/TERN-20261017-RB03.json`
**Reboot policy:** only the owner may reboot through Android's normal power menu; no agent or shell command may reboot the phone.

The owner-operated reboot took place on 2026-10-18. RB03 records a changed boot
and a Termux:Boot observer event. `ternuxx reboot verify` returned
`verified_reboot_partial` because that observer did not identify sshd/service
health; authenticated connectivity and kernel socket binding were not captured
by the verifier. Later read-only native checks found the Runit-managed
`ternuxx-sshd` service running with valid loopback configuration, and a
separate password-authenticated loopback SSH probe returned its success marker.
This proves current postboot reachability, not automatic startup. The checkpoint
remains `NOT_READY`, and no task resumes automatically. See the
[sanitized postboot verification record](../evidence/2026-10-18-postboot-native-ssh-verification.json).

The owner opened Termux:Boot once from Android's app launcher. The official
Termux:Boot setup instructions say this first launch enables the app to run at
boot ([official README](https://github.com/termux/termux-boot#how-to-use)). The
`pm path` wrapper still fails on this device, but Doctor's direct
`cmd package path` query reports the app present. RB03's changed-boot observer
record confirms that the Termux:Boot script path ran; automated service health
was not captured and remains partial as described above.

`TERN-20261017-RB02` is retained as an earlier inconclusive attempt: its
observer was manually invoked on the same Android boot and wrote `inconclusive`
at 17:07:53Z. The boot ID did not change. It is not reboot evidence and has
not been overwritten. RB03 is also used; any future test needs a fresh unique
checkpoint ID.

## What is now configured

- Native `termux-services`/runit is installed. Only the Ternuxx-owned
  `ternuxx-sshd` service was enabled; the package-provided `sshd` and
  `ssh-agent` services remain down.
- The managed SSH service uses the private candidate config
  `$HOME/.config/ternuxx/sshd_recovery.conf`, listens on `127.0.0.1:8023`,
  and uses the existing Termux host keys. The original OpenSSH config and
  host keys were not changed.
- The candidate passed `sshd -t` and `sshd -T`; the daemon log reported
  `Server listening on 127.0.0.1 port 8023`. Password-authenticated access
  succeeded from the same-device PRoot side. Host-key fingerprints matched
  the existing native host keys. The native repository remained reachable at
  commit `1a891faabc925136c1801f40194b0969d28041df`; its pre-existing dirty
  paths were preserved.
- After that candidate path worked, the old unmanaged daemon on port `8022`
  was stopped. Its original configuration and credentials remain untouched.
  Current management access is through loopback port `8023`.
- Native `~/x.sh` has a verified byte-identical backup at
  `~/x.sh.ternuxx-backup-20261017T163623Z`. Its two global Wake Lock commands
  now use the Ternuxx owner coordinator. Other launcher behavior was kept.
- A separate `xgo` session started X11/XFCE and then exited. While it ran,
  managed Wake Lock owners were `native.sshd` and `proot.desktop`; after
  cleanup only `native.sshd` remained, and the SSH service stayed up. The
  existing PRoot process was still present. XFCE emitted expected optional
  systemd/desktop-service warnings; visual/audio quality is not release-
  qualified.
- Native Wake Lock status can show Ternuxx leases, but Android's app-global
  lock-holder state remains unobservable through the current adapter.
- The existing `db` alias still resolves to direct Debian PRoot login without
  starting a GUI. The pre-existing PRoot process remained active during the
  `xgo` test; no extra `db` session was started.

## Private checkpoint

RB03 was written and read back with state `prepared`, previous boot ID
captured, and `automatic_resume=false`. The checkpoint's readiness field is
always initialized to `NOT_READY`; the human-readable gate in this guide is the
readiness decision. Its unique nonce remains only in Native Termux private
state; do not copy it into Git, logs, screenshots, or chat. RB01 and the
inconclusive RB02 are retained unchanged.

## Native boot path

The intended sequence is:

`Android boot → Termux:Boot → ~/.termux/boot/00-ternuxx-services → official Termux service startup → enabled runit service → loopback sshd on 8023 → later-sorted ternuxx-recovery observer`

The runit service acquires the persistent `native.sshd` Wake Lock lease,
validates the candidate SSH config, runs one foreground `sshd`, records its
log, and releases only its own lease when the supervised process exits. The
boot entry starts the service supervisor and waits up to 20 seconds for the
managed service. Neither path enters PRoot or starts an agent/model. This
sequence has been exercised in the live session up to the running service;
manual execution of the startup hook returned ready without changing the
service PID, and the observer dry-run retained `RB02` as prepared with
`state_written=false`. Termux:Boot receiver execution after Android boot is
still unverified.

## Owner-operated reboot procedure for a future checkpoint

1. Prepare and review a fresh unique checkpoint ID. RB03 has already been
   used; do not reuse it. Do not share a checkpoint nonce; the verifier reads
   it from Native Termux private storage.
2. Reboot using Android's normal power menu. Do not use a shell reboot command.
   SSH and the PRoot agent will disconnect.
3. Let Android and Termux:Boot run. Startup duration has not been measured
   across reboots; do not assume a fixed time. Open Native Termux after Android
   finishes starting, then allow its startup scripts and runit service to
   settle before checking connectivity. No fixed wait time is guaranteed.
4. If Native Termux is not reachable through SSH, open it directly and use the recovery
   steps below. Do not rebuild or reset Debian PRoot.
5. From Native Termux, inspect `ternuxx reboot status <test-id>`, then run
   `ternuxx reboot verify <test-id>` and `ternuxx reboot resume-info
   <test-id>`. Verification records evidence only; it never resumes tasks.
   Treat `NOT_READY` or partial verification as incomplete and review the
   missing service/authentication evidence manually.

## Recovery if port 8023 is not ready

Open Native Termux locally. Inspect:

```sh
sv status ternuxx-sshd
tail -n 60 "$HOME/.local/share/ternuxx/log/sshd-runit.log"
tail -n 60 "$HOME/.local/share/ternuxx/continuity/boot-logs/ternuxx-services.log"
tail -n 60 "$HOME/.local/share/ternuxx/continuity/boot-logs/termux-boot.log"
```

If the candidate service is simply down and its config validates, run
`sv up ternuxx-sshd`, then check `sv status ternuxx-sshd` and the service log.
For supervised-start failure, a local foreground recovery is:

```sh
"$PREFIX/bin/sshd" -t -f "$HOME/.config/ternuxx/sshd_recovery.conf"
"$PREFIX/bin/sshd" -D -e -f "$HOME/.config/ternuxx/sshd_recovery.conf"
```

Keep that Termux session open while reconnecting from same-device PRoot to
`127.0.0.1:8023`. If Termux:Boot did not run, open Termux and start the
service manually; do not change Android debugging, network exposure, keys,
or the existing PRoot installation as a shortcut.

## Rollback boundaries

- The candidate uses a separate config and port; the previous OpenSSH config
  and keys were not edited. Port `8022`'s old daemon is stopped, not configured
  to autostart. Do not restart it casually: its earlier effective policy was
  wildcard IPv4/IPv6, while actual exposure could not be measured.
- From local Native Termux, `sv-disable ternuxx-sshd` disables and stops only
  this managed service. Do this only after arranging another access path.
- The exact original launcher is preserved in the backup above. **Do not
  restore it while `native.sshd` relies on the coordinator:** its old EXIT
  hook calls Termux's global `termux-wake-unlock`.
- Keep checkpoint and logs for diagnosis. No PRoot rootfs rollback is needed.

## Evidence standard

A reboot passes only if the saved previous boot ID differs from a new boot ID,
the matching test marker is observed by the Native Termux boot path, and native
SSH readiness is verified afterward. A new SSH connection, shell, PRoot login,
timestamp, or service restart by itself is not proof. Kernel listener
enumeration remains unavailable; loopback is supported by the candidate's
effective configuration, daemon bind log, and authenticated same-device
connection, while independent external-reachability testing was not performed.
At the time this pre-reboot checklist was written, the Android package service
prevented independent package-state reporting and the owner had confirmed
opening the app, but no physical reboot had yet been performed. RB03 was later
run on 2026-10-18; its partial result is recorded at the top of this guide.


## Historical RB05/RB06 follow-up — readiness retry verification (2026-10-18; superseded for the next reboot by RB07)

RB05 was prepared but superseded before reboot because its private baseline
incorrectly recorded Termux:Boot startup policy as enabled; live diagnostics
report that policy as unknown. No reboot was performed against RB05. Its
checkpoint is retained for audit history and must not be verified.

Use only private checkpoint `TERN-20261018-RB06`, prepared at mode 0600. It
records the corrected `unknown` policy, current native Ternuxx display `:1`,
existing PRoot allocation `:0`, Debian inventory without guest entry, managed
SSH 8023 running with verified definition/config, and the transient readiness
retry in `lib/reboot_recovery.py` as the behavior under test. RB06 starts at
`NOT_READY`; automatic resume is disabled. See [RB06 preparation
evidence](../evidence/2026-10-18-p3-reboot-rb06-prepared.json) and [RB05
supersession record](../evidence/2026-10-18-p3-reboot-rb05-prepared.json).

The owner performs the Android UI reboot. On return, reconnect through the
existing native SSH route (current work-shell port 8022), then inspect and
verify only RB06:

```sh
./ternuxx reboot status TERN-20261018-RB06
./ternuxx reboot verify TERN-20261018-RB06
./ternuxx reboot resume-info TERN-20261018-RB06
```

Do not invoke `boot-observe` manually: that cannot establish Termux:Boot
delivery. Collect read-only managed 8023 readiness/authenticated loopback,
desktop status, PRoot inventory and `db`/`xgo` preservation, and Wake Lock
owner status. Keep the checkpoint `NOT_READY` if any required check is missing
or unknown. Never copy its nonce or boot IDs into Git, screenshots, logs, or
chat. No agent-triggered reboot or service/desktop/boot-setting mutation is
part of this test.


## Current checkpoint - RB08 (2026-10-21)

Owner is initiating the next Android restart through the normal UI. RB08 is the unique prepared checkpoint; RB07 remains preserved as the earlier observed test. Use the 8022 Native development channel after reconnecting, and follow the [RB08 pre-reboot record](../evidence/2026-10-21-p3-pre-reboot-rb08-checkpoint.md).
