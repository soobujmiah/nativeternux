# SSH key-change rollback — 2026-10-22

## Implementation

Confirmed SSH key enrollment and revocation now save the exact previous Native authorized_keys bytes, file existence, and mode in a private $HOME/.ssh/.ternuxx-key-recovery record before the atomic key-file mutation. Records use mode 0600 in a mode 0700 directory; they contain public authorized-key data only, never private key material.

Rollback is available through the shared management service and CLI, TUI, authenticated Web, GTK bridge, and GTK dialog. It requires an existing recovery ID, a fresh preview, and the exact plan ID with explicit confirmation. The write is refused if the current file no longer matches the recorded post-mutation content and mode; group/world-writable authorized_keys inputs are refused. It restores an originally absent file by removing the mutation-created file. Recovery records are retained and repeat rollback does not rewrite the key file.

## Verification

- Native Termux $HOME/ternuxx, base commit 907834b; working tree contains this paired source/docs update.
- Focused shared-service, authorization, client, bridge, and key-manager suite: 146 tests passed before the added CLI rollback contract test.
- Post-change CLI and key-manager suite: 23 tests passed.
- Full Native suite via bash scripts/repo_test.sh: exit 0; 834 tests passed in 107.740 seconds.
- ./tx ssh rollback-list: read-only; zero recovery records existed on the production account.
- ./tx ssh inspect: read-only; managed ternuxx-sshd was running with source/installed service-definition hash match, loopback-only 127.0.0.1:8023 policy, and an SSH banner. 8022 remains a separate owner-managed channel; its reported config is wildcard/password-enabled. Listener-to-process correlation for general diagnostics was unavailable due to procfs/netlink permission limits.
- ./scripts/install-management-center.sh: GTK app built and installed. App-menu entry is $PREFIX/share/applications/ternuxx-management-center.desktop, named Ternuxx Management Center. Installed C source hash cc975fc9c4a6f3bb56eee3d93784d38fe762e2b7d7a95962ce6649bfbbebc32a and bridge hash 6a78d7c92ed30847fb8ad68c2ece5d1ca24da186b72b3df82c11d13ea51b7344 match Native checkout; binary SHA-256 is e7e9f46a382ae5ec5f68303415a4b4ded0a3e9849213ca42464e199d8457e369.

## Limits

No production key was enrolled, revoked, or restored; this live account had no rollback records. Exact restoration, changed-content and permission conflict refusal, unsafe-mode rejection, and stale-plan handling are tested against disposable fixtures. Password recovery and cold-boot delivery remain separate acceptance items. This evidence does not prove a successful future GUI interaction or a cold-boot run.
