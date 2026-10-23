# Disposable SSH authentication qualification — 2026-10-22

## Setup

Used Native Termux OpenSSH and the checkout's actual `lib/ssh_key_manager.py` against a private temporary `.ssh` tree under Native `$HOME/.ssh`. The fixture generated two disposable Ed25519 client keys and one disposable host key, with an isolated `authorized_keys` and `sshd_config`. A temporary `sshd` listened only on `127.0.0.1` at an ephemeral port. Client attempts used batch mode, public-key authentication, a private temporary known-hosts file, and a command returning the authenticated Native username.

## Results

1. Shared-service manager preview/apply enrolled key A; the temporary server accepted A.
2. Unlisted key B was denied before enrollment.
3. Manager preview/apply enrolled recovery key B; the server accepted both A and B.
4. Manager preview/apply revoked A; the server denied A and continued accepting B.
5. Manager preview refused removing B as the last authorized key.
6. The temporary server process exited; both temporary fixture directories were removed. The production `ternuxx-sshd` remained at its pre-test PID 21035. No production authorized_keys, private keys, SSH configs, 8022/8023 endpoint, service, startup marker, or Wake Lock preference was changed.

## Scope

This is real Native OpenSSH authentication evidence for the current manager's enrollment, revocation, replacement-key continuity and last-key guard, using disposable credentials. It is not a test against production 8023, does not qualify a password recovery path or future cold boot, and does not provide durable rollback of an already-applied credential mutation. Durable rollback remains open.
