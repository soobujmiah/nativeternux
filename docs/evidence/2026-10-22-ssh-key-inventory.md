# Native SSH authorized-key inventory

## Scope

Added a read-only `ssh.keys.list` operation for the managed Native SSH credential view. It is separate from `ssh.inspect`, requires the `ssh.credentials.read` Web capability, and is available from `tx ssh keys-list`, the guided TUI, authenticated Web UI, and GTK Management Center. The managed SSH resource is 8023; 8022 remains externally managed and read-only. The current effective configs for both endpoints use this same Termux-account key file.

Read-only `sshd -T` checks for both the managed 8023 config and the current 8022 config reported `AuthorizedKeysFile .ssh/authorized_keys`. Before reading, the operation reruns bounded `sshd -T` for the managed loopback login context and refuses a missing/invalid config or any key path other than `.ssh/authorized_keys`. It then reads only `$HOME/.ssh/authorized_keys` and returns each valid key's algorithm, SHA-256 fingerprint and sanitized comment. Raw public-key bytes, private keys, passwords, comments containing controls, and config text are never returned. Invalid lines are counted without echoing their contents. File and directory symlinks, wrong owner/type, oversized files and excessive line counts fail closed. This operation does not enroll, revoke or generate credentials.

## Implementation and verification

- `lib/ssh_key_inventory.py` performs bounded, read-only parsing and derives fingerprints from the SSH wire-format key blob.
- `lib/management_service.py`, `lib/management_authorization.py`, `lib/management_sessions.py` and `lib/management_catalog.py` add the typed operation, dedicated read scope, read-only session classification and resource capability.
- CLI, TUI, Web and GTK each expose the same operation and label its shared-account scope. The GTK bridge calls the shared management service; no client reads the file directly.
- `tests/test_ssh_key_inventory.py` covers absent files, valid entries, invalid-line redaction, symlink rejection and the file-size limit, and reject algorithm-looking text in malformed records.
- Additional service, authorization, catalog, TUI, bridge and Web regressions cover shared routing and scope.

Native Termux checks passed:

- Focused syntax checks and the seven-module regression set passed: **151 tests**. After fixing a comment-sanitization regression found in review, focused inventory/authorization tests passed: **12 tests**. The post-fix full suite `python3 -m unittest discover -s tests` passed: **772 tests**.
- `bash tests/test_cli_help.sh`: **PASS**.
- `git diff --check`: **PASS**.
- `python3 -m tools.repo_knowledge verify`: **0 findings**.
- Live `tx ssh keys-list --json` returned `ok=true`, `status=available`, `authorized_keys_path_verified=true`, one valid authorized entry, zero invalid entries and mode `0600`. Fingerprint and comment were redacted from the captured summary.
- `bash scripts/install-management-center.sh` built and installed the Native GTK app. Installed source-C, bridge and binary hashes matched the checked-out source and identity record; `management-center --version` returned `0.1`.

## Limits

No key material was changed and no authentication policy, 8022 service or 8023 service was restarted. Key generation, enrollment, removal/revocation, password/recovery workflow, per-service boot/Wake Lock controls and recovery/rollback qualification remain open. The newly installed GTK control has not received a new owner-operated visual review; the current testing policy reserves application input and visual UX judgment for the owner.
