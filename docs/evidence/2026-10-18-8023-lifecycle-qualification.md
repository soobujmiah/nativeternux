# 8023 lifecycle qualification evidence (2026-10-18)

## Scope and baseline

- Tested repository: Native Termux checkout `$HOME/ternuxx`, branch `main`, base HEAD `5232a20b63c5f9f66d8f3e74208ed5bff8c4340a` (working tree already contained unrelated active changes; no commit or push).
- Test environment: Native Termux on the Android device, entered through the owner-started 8022 development SSH session; ADB was used read-only for kernel socket tables.
- Existing Debian PRoot process PID 16526, native GUI `:1`, and 8022 were preserved. No reboot was performed.
- 8022 remains the manual development daemon on wildcard IPv4/IPv6 listeners; the established 8022 shell remained active throughout the managed-service tests.

## Confirmed state-path drift and correction

The installed `ternuxx` dispatcher delegated wake-lock operations to an installed CLI that reads `NATIVERNUX_STATE_DIR`, while the Runit wrapper exported only `TERNUXX_STATE_DIR`. This was directly reproduced: the checkout CLI reported no active owner while the installed CLI reported `native.sshd` active in `~/.local/share/nativeternux/wakelock/owners.json`. The old state tree was preserved. After the managed service was stopped, both CLIs reported no active owner, confirming its lease cleanup.

The service source now exports `NATIVERNUX_STATE_DIR="$TERNUXX_STATE_DIR"` for that installed CLI boundary. A fixture regression test asserts the forwarded state path. The exact preview diff was applied with operation `92c2a0c0155345b9b1e7d8e3060a81d5`; source and installed run-file SHA-256 are both `2fd14437efc472c6ff4526600e6278bc2c55fb742a1eb25fc36fb8bc1dd7094b`. The deployment snapshot is retained. Rollback preview was read-only, showed the exact reverse diff to SHA-256 `1dc73681a09d606b265db8add60e4870c144a50b31da7b3ba0a7db3c7ab932f6`, and was not applied.

After restart, the checkout CLI and the installed CLI when invoked with the service-provided `NATIVERNUX_STATE_DIR` override reported the same single active `native.sshd` owner in the shared Ternuxx state. Direct invocation of the installed compatibility command without the override still defaults to the old state path. Its old state file remains present and empty; reconciling that installed entrypoint is a separate follow-up. The `termux-wake-lock` platform lock itself remains unobservable through the manager (`platform_lock_state=unknown`), so this evidence verifies registered lease consistency, not Android's global wakelock state.

## Live lifecycle tests

| Test | Procedure / expected | Actual | Status |
|---|---|---|---|
| Source/installed identity | Read-only preview shows exact diff and service/config hashes | Preview generated; config hash unchanged | PASS |
| Deployment | Apply exact reviewed plan; preserve current process until explicit lifecycle action | Atomic deployment operation `92c2a0c0155345b9b1e7d8e3060a81d5`, `service_restarted=false`, running status preserved | PASS |
| Stop | Exact-plan stop affects only managed Runit service; 8022 remains | Service stopped; ADB table had no 8023 LISTEN row; 8022 wildcard listeners and established connection remained | PASS |
| Start / restart | Exact-plan start restores one service and readiness | Runit wrapper PID `12951`, child `sshd` PID `12983`; valid config and loopback SSH banner | PASS |
| Authenticated readiness | Password-authenticated loopback SSH command succeeds | `authenticated-loopback-ok`, SSH exit status 0; password not stored in evidence | PASS |
| Listener bind and ownership | ADB socket table says loopback; inode matches managed sshd FD and Runit ancestry | `127.0.0.1:8023`, inode `2273711`, UID `10490`; same-UID `/proc/12983/fd` contains `socket:[2273711]`; PID ancestry `12951 -> 12983` | PASS |
| Duplicate instance / repeated start | Read-only repeat-start plan is no-op; only one managed sshd remains | `requires_confirmation=false`, no plan ID; process inventory shows one `sshd -D -e -f ...sshd_recovery.conf` | PASS |
| Stop/start repeated cycle | Repeat exact-plan stop and start; preserve 8022 | A second stop/start cycle completed after the deployment; 8022 remained established | PASS |
| Deployment failure/rollback/recovery | Isolated fixtures exercise partial write, automatic restore, recovery and exact rollback | `tests/test_runit_deployment.py` passed within the complete suite; no live failure injection | PASS (fixtures) |
| Reboot readiness | Requires explicit owner-approved reboot and postboot checks | No reboot performed | UNVERIFIED (approval pending) |
| External/LAN reachability | Separate network-route test | Not tested; 8023 is configured loopback-only | UNVERIFIED / not in scope |

## Automated evidence

- `bash -n scripts/termux-services/ternuxx-sshd/run`: PASS.
- `python3 -m unittest tests.test_native_service_scripts -v`: PASS, 2/2 after fixing the fixture's f-string escaping during test authoring.
- `bash scripts/repo_test.sh`: PASS, 315/315 tests in 67.132 seconds. This includes isolated Runit deployment partial-failure and recovery fixtures.
- Direct `./scripts/repo_test.sh` invocation was denied because the existing file is not executable; invoking it with `bash` succeeded. File mode was not changed.

## Result and limits

The 8023 Runit lifecycle, process/socket ownership, loopback bind, password-authenticated local readiness, duplicate-start behavior, registered wake-lock lease path, and preview/rollback record are verified for this running boot. Port 8022 remained operational. Reboot readiness is still `UNVERIFIED`; no reboot was performed. Android's global wakelock state is also not observable through the current manager. See [deployment and lifecycle procedure](../testing/8023-deployment-and-lifecycle.md) and [SSH lifecycle architecture](../architecture/SSH-LIFECYCLE.md).
