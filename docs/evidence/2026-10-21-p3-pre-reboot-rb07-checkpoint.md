# P3 expanded pre-reboot verification checkpoint — RB07 — 2026-10-21

Phase: `P3`

Status: private checkpoint TERN-20261021-RB07 prepared; readiness is NOT_READY. The owner will restart Android. The agent did not trigger a reboot or run a boot script.

## Test marker

A private checkpoint was created with the supported command ./tx reboot prepare. It stores its nonce and previous boot identity only in Native Termux private state and disables automatic task resume. Do not copy either value into this note, Git, screenshots, chat, or logs. Use only TERN-20261021-RB07 for this reboot.

At preparation, the repository was on main at dfa3f63, with 14 modified tracked paths and 7 untracked paths. These owner changes are in scope for preservation; do not reset, clean, commit, or rewrite them during reboot verification.

## Current baseline and expanded test scope

Read-only Native Termux checks were captured at about 2026-10-21 16:43 Asia/Dhaka. After reboot, repeat the checks and report each result as pass, failed, unknown, or unchanged. A stopped or unverified component is not automatically supposed to become enabled.

| Area | Pre-reboot observation | Post-reboot verification |
|---|---|---|
| Android boot and Termux:Boot | The test marker is prepared. Termux:Boot package and receiver are enabled, while system delivery policy is unknown. | Verify boot identity changed and the actual observer recorded RB07. Never invoke the observer or boot scripts manually. |
| Boot helpers | Service and recovery helpers match source, mode 0700. Service SHA-256: 8dfa04273dd93cc0def5f26b70d496b9f80575f4608bcf079cea993eb04d3119. Recovery SHA-256: 702f4f21229495bf8725c6e7063877ccd47810fd20f0651ae1e9a79ae9fad64d. | Repeat helper status and verify exact hashes/modes remain matched. Check the fixed service and observer boot logs for a new record. |
| Native SSH 8023 | Runit service running; process identity and definition verified; config valid; loopback SSH banner passed. A PRoot-to-Native key-only SSH login to 127.0.0.1:8023 succeeded as u0_a490. | Repeat tx ssh inspect and the same key-only authenticated loopback check. Keep listener-to-port correlation separate; procfs and NETLINK_SOCK_DIAG were denied. |
| Development SSH 8022 | Separate owner-managed development channel. Doctor reports wildcard bind/password authentication enabled, daemon present, listener ownership and external reachability unknown. | Confirm the existing 8022 development connection works after the owner reconnects. Do not alter its configuration, authentication, bind, or exposure. |
| Desktop :1 | tx status reports stale: supervisor, X11, and XFCE absent; visibility unknown. | Record the status. The boot service helper only starts enabled runit services and does not start the desktop; do not repair or launch it during this test. |
| Cron scheduler | Boot script is configured and its identity matches; scheduler is stopped, there are zero jobs, and the last script result predates this checkpoint. | Check boot-script result and scheduler state. If startup fails or stays stopped, record that outcome; do not start or stop Cron manually. |
| Debian PRoot and legacy entrypoints | Debian is installed, but guest/process ownership is unverified. Inventory shows unverified host PRoot candidates; no guest was entered. | Repeat read-only PRoot inventory, verify the Debian rootfs and db/xgo/killx entrypoints remain available, and preserve all unverified processes. Do not enter Debian, signal processes, or change the rootfs. |
| Operation recovery and Wake Lock | Doctor reports no unresolved operations. Wake Lock coordinator lists native.sshd as its registered owner; Android platform lock state is unknown. | Repeat Doctor and Wake Lock status. Record ownership and unknown platform state without acquiring or releasing a lock. |
| ADB and Shizuku | No local ADB server response. Shizuku is present, but provider/Binder health and authorization are unknown. | Recheck the same read-only discovery status. Do not start ADB, invoke Shizuku, or change debugging settings. |
| GPU/NPU | Default Doctor skipped renderer workloads; NPU execution remains unverified. | Record their status only. Do not run graphics workloads, inference, or accelerator setup as part of reboot qualification. |
| Listener ownership | Both procfs and NETLINK_SOCK_DIAG listener observation were denied. | Recheck Doctor. Keep mapping unknown if still denied; do not infer ownership from process names or a banner. |

## Post-reboot procedure

After Android restarts, the owner opens Native Termux, starts Codex in Debian PRoot, reconnects to Native Termux using the existing 8022 development channel, and tells the agent the reboot is complete.

Then, from the Native repository, run:

1. ./tx reboot status TERN-20261021-RB07
2. ./tx reboot verify TERN-20261021-RB07
3. ./tx reboot resume-info TERN-20261021-RB07
4. Repeat the read-only commands: ./tx status --json; ./tx mng doctor --json; ./tx mng boot helpers status; ./tx mng boot cron status; ./tx mng cron status; ./tx ssh inspect; ./tx mng proot status; ./tx wakelock status.
5. From PRoot, repeat the key-only authenticated loopback SSH probe to 127.0.0.1:8023.
   Command: ssh -i "$HOME/.ssh/id_ed25519_termux" -p 8023 -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=5 u0_a490@127.0.0.1 id -un

The verifier records evidence only; it never resumes a task. Its output can contain private boot identifiers, so report only transition/outcome and sanitized health fields. Do not reproduce the nonce or boot identifiers. Read only these fixed log paths if present:

- $HOME/.local/share/ternuxx/continuity/boot-logs/ternuxx-services.log
- $HOME/.local/share/ternuxx/continuity/boot-logs/termux-boot.log

Do not change services, desktop state, Cron, SSH policy, boot settings, ADB/Shizuku, or PRoot during verification. If the 8022 channel is unavailable, the owner can open Native Termux locally and restore the existing channel; do not switch repository work to 8023. Do not repeat the reboot automatically. Keep P3 open for every failed or unknown required result.

## Evidence

- Reboot checkpoint contract: docs/testing/REBOOT-RECOVERY-GUIDE.md.
- Current P3 gates: docs/evidence/2026-10-21-p3-gate-review-followup.md.
- Installed helper reconciliation: docs/evidence/2026-10-21-boot-helper-reconciliation.md.
- Private checkpoint: TERN-20261021-RB07; nonce and boot identity intentionally omitted.


## Owner wait instruction — 2026-10-21

The owner asked the agent to wait until the owner is ready to restart Android and explicitly tells the agent. No restart has been initiated. Keep RB07 as the sole pending checkpoint; do not prepare another checkpoint, invoke reboot helpers, or perform post-boot verification before the owner reports the restart complete and reconnects on 8022. P3 remains open and P4 must not start before RB07 verification and P3 confirmation.


## Superseded for the next reboot - 2026-10-21

RB07 later reached private state boot_observed / NOT_READY and verification history contains verified_reboot_service_unqualified. It remains intact as historical evidence. It cannot identify the owner's next reboot; unique checkpoint RB08 is prepared for that event. See [RB08 pre-reboot baseline](2026-10-21-p3-pre-reboot-rb08-checkpoint.md).
