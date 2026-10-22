# SSH 8023 shared key lifecycle source slice

## Implemented in the Native checkout

This source slice adds preview-confirmed enrollment and revocation for public SSH keys in the fixed Native Termux account file, $HOME/.ssh/authorized_keys. Both owner-managed SSH 8022 and Ternuxx SSH 8023 use this shared file, so every plan discloses both effects.

The shared service operations are ssh.keys.add.preview/apply and ssh.keys.remove.preview/apply. Apply requires explicit confirmation and the exact current preview plan, which is bound to before/after file hashes. The manager rejects symlinked/wrong-owner files, a non-private .ssh directory, oversized or malformed content, unsupported authorized_keys policy options, malformed key blobs, and control characters. Writes use a private lock file and same-directory atomic replacement with mode 0600. Revocation removes every exact matching fingerprint record, preserves unrelated/comment/invalid lines, and refuses to remove the final valid authorized key; enroll and verify a replacement first.

The CLI reads enrollment data from stdin so the public line is not placed in process arguments. The authenticated Web UI uses a dedicated ssh.credentials.manage capability, CSRF, and the durable idempotency layer; key request bodies are not retained by the request store. The TUI selects an owned, regular Native .ssh/*.pub file or a key from the redacted shared inventory. Client confirmation names both SSH ports.

## Checks

On Native Termux, 2026-10-22:

- Focused manager, service, authorization, session, catalog, Web, and TUI regressions passed.
- python3 -m py_compile on the changed Python modules and focused tests: PASS.
- bash tests/test_cli_help.sh: PASS.
- PYTHONPATH=lib python3 -m unittest discover -s tests: **791 tests passed**.
- Read-only source-checkout command TERNUXX_JSON=1 ./tx ssh keys-list reported status available and the fixed managed authorized-key path verified. Only status/count metadata was summarized; fingerprints and labels were not emitted in this evidence.
- Empty-stdin CLI enrollment probe was rejected with “Expected one public-key line on stdin.” No write was attempted.
- No key, password, SSH config, service lifecycle, boot policy, or Wake Lock state was changed.

## Remaining acceptance

This is a partial source implementation, not A10 completion. GTK enrollment/revocation controls are now implemented and installed; see [GTK SSH key-control evidence](2026-10-22-ssh-gtk-key-controls.md). TUI can enroll only a public key already present as a Native .pub file. Secure keypair generation, recovery/re-enrollment wizard, durable rollback snapshot, key-authentication testing (new/invalid/revoked key), password lifecycle policy, per-service boot/Wake Lock controls, visual UI review, authenticated Web client execution against the live session, installed component parity, and 8023 end-to-end post-change qualification remain open. The manager has fixture evidence only for mutations; the production authorized_keys file was not modified.
