# Native managed SSH service JSON repair — 2026-10-23

## Finding

The `ternuxx-sshd` Runit wrapper requested JSON by setting `TERNUXX_JSON=1` in the child environment. The `tx` entrypoint initializes that variable to `0` during startup, so the wrapper parsed human output as a JSON response and exited before launching its managed daemon. The service therefore repeatedly failed its Wake Lock acquisition handshake while Native SSH on port 8022 remained an independent service.

## Change

The wrapper now requests JSON through the supported global `tx --json` option, validates the response envelope and `ok` field, accepts only bounded error codes for logging, and fails closed on malformed responses. A fixture regression confirms that private error messages are not written to the service log and sshd is not started after a failed acquire.

## Live deployment and verification

- The exact Ternuxx deploy preview showed a change only to the fixed `ternuxx-sshd/run` service definition; deployment used the matching preview plan and preserved a rollback snapshot.
- A first apply preview expired when supervisor status changed between preview and apply. No definition was changed by that stale plan. A fresh preview was taken and its exact plan applied successfully.
- The subsequent restart operation returned a generic failure, but immediate read-only inspection verified the managed 8023 service running, installed/source definition hashes matching, and the 127.0.0.1:8023 SSH banner responding. The registered `native.sshd` Wake Lock owner was present with no stale or unknown owners.
- Native SSH 8022 configuration and the active Debian PRoot were not changed by this repair. Listener ownership for 8022 remains unknown where the OS denied observation.

## Verification

- `python3 -m unittest tests.test_native_service_scripts -v`: 6 passed.
- `bash scripts/repo_test.sh`: 888 passed, 1 skipped in 110.708 seconds.
- `bash tests/test_cli_help.sh`, shell syntax checks, `git diff --check`, document inventory check, and repository knowledge verification passed.

## Limits

The SSH inspection probe reported a banner only; no private key was read and no authenticated connection was attempted. Androids global Wake Lock state and 8022 listener ownership remain unknown. Restarts generic failure merits separate source-level audit despite the recovered running state. This is not a cold-boot qualification.
