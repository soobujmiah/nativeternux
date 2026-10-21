# Native SSH connection and lifecycle contract

**Status:** Partial native CLI/service implementation; owner-operated reboot observer ran, but automated recovery verification remains partial
**Owner requirement:** Native Termux is authoritative. Debian PRoot is optional and must never gate native SSH or recovery.
**Related:** [management API](MANAGEMENT-API.md), [operations](../OPERATIONS.md), [native autonomy ADR](decisions/ADR-0010-native-termux-autonomy.md), [shared management ADR](decisions/ADR-0004-three-interfaces-shared-management.md).

The read-only `ssh.inspect` operation and owner-scoped Wake Lock operations use the local allowlisted management service. A separate Ternuxx-managed native OpenSSH service is now supervised by Termux runit and has been tested on the target phone. SSH setup wizard, general connection-profile management, HTTP, GUI, and Web UI callers remain unimplemented.

### Login key meaning and recovery

For port 8023, a login key is a **client identity** used by the computer or PRoot shell that connects to Native Termux. The private half stays with that client; only its public half belongs in the Termux account's `authorized_keys`. It is separate from the SSH server host key, which identifies the server. Losing the client key does not recover access by itself: use an already working password login or the local Termux app session to enroll a replacement public key. Keep password login available until a fresh key-only connection to `127.0.0.1:8023` has succeeded. Never delete the old authorized key or rotate a host key as part of enrollment.

The current product exposes managed SSH status and confirmed service start/stop only. Key generation/enrollment/removal, password changes, key inventory/revocation, and SSH-specific start-at-boot policy are **not implemented in CLI, TUI, Web, or GTK**. These controls must be added through `native_ssh` and the shared management contract; client-side direct writes to `authorized_keys`, direct `passwd` invocation, or boot-script edits are forbidden. Until then, guide users to retain their existing password/local-Termux recovery route and label these controls unavailable. General boot-profile preview does not configure SSH startup. The existing installed Ternuxx service boot entry starts the Runit supervisor, which starts enabled services including managed SSH; a separate SSH start-at-boot toggle is not implemented. The managed SSH service currently uses a persistent `native.sshd` Wake Lock lease; user-selectable Wake Lock policy is not implemented.
The diagnostic reports the package-default OpenSSH policy separately from the `ternuxx-sshd` runit service. The latter is checked against `$HOME/.config/ternuxx/sshd_recovery.conf` with read-only `sshd -t`/`sshd -T` calls and `sv status`; raw configuration and credentials are never returned. When the effective managed config has an explicit loopback `ListenAddress`, it also makes a one-second unauthenticated connection to that exact endpoint and reads an SSH protocol banner. The probe never targets non-loopback addresses, does not authenticate, and reports reachability separately from ownership. A process-chain check can verify the exact same-UID runit service process, fixed `./run` wrapper in the service directory, and direct `sshd` child with the configured executable and config argv. That proves which managed daemon process is running; it does not prove which TCP port that process owns. Procfs socket-table visibility and socket-inode-to-port correlation remain separate checks and can stay unknown when Android denies `/proc/net/tcp*`.

When either procfs TCP table is unreadable, the diagnostic now has a bounded read-only Linux `SOCK_DIAG` fallback. It requests TCP listeners for IPv4 and IPv6, records each local endpoint and socket inode, and reuses the existing exact process-FD and configured-endpoint correlation. A complete result requires successful completion for both address families; denial, interruption, malformed data, or partial visibility remains `unknown` for ownership. The report preserves separate `tcp_listener_procfs_observation`, `tcp_listener_netlink_observation`, and `tcp_listener_source` fields alongside the combined status. The latest native doctor run reported `procfs=permission_denied`, `netlink=permission_denied`, and `source=none`, so the fallback remains unable to qualify listener ownership on this Android build. The service-definition SHA-256 check compares the fixed installed run script with repository source; a mismatch or unsafe unit path is reported without changing the service. The source resolver honors `TERNUXX_REPO_ROOT`; otherwise it uses the module checkout when present and falls back to the documented native checkout at `$HOME/ternuxx`, so an installed diagnostic module can compare against the repository-owned run script rather than an absent path under `$PREFIX`.

## 1. Current evidence and boundary

The original native listener used an unmanaged `sshd -p 8022` process. Read-only inspection found wildcard IPv4/IPv6 policy, but Android denied access to `/proc/net/tcp*` and the available `netstat` could not show TCP listeners. After an isolated candidate was validated, the unmanaged daemon was stopped. Its original OpenSSH config and host keys were left unchanged.

The managed candidate is `$HOME/.config/ternuxx/sshd_recovery.conf`, owned by the native Termux user with mode `0600`. It uses existing host keys, port `8023`, `AddressFamily inet`, `ListenAddress 127.0.0.1`, and allows the existing password flow plus public-key and keyboard-interactive methods. The Termux OpenSSH build rejected `UsePAM`; that directive was removed from the candidate and `sshd -t` then passed. `sshd -T` reported only `127.0.0.1:8023`, the supervised daemon log reported `Server listening on 127.0.0.1 port 8023`, and same-device PRoot authenticated successfully using the expected host-key fingerprints. A fresh connection also succeeded after stopping the old daemon. This verifies the configured loopback listener through the daemon's own log and authenticated connection; procfs socket-table enumeration and external reachability tests remain unavailable and are not claimed.

The native `termux-services` runit package is installed. Only the Ternuxx-owned `ternuxx-sshd` service is enabled; it runs one foreground daemon using the separate candidate config and acquires a persistent `native.sshd` Wake Lock lease. Package-provided `sshd` and `ssh-agent` services remain disabled. A Termux:Boot entry starts the official service supervisor and waits for the managed SSH service. A second sorted entry runs the continuity observer. The owner-operated reboot on 2026-10-18 changed the boot ID and produced a boot-observer record. RB03 automated verification is `verified_reboot_partial`: the observer did not identify the sshd process or service health. Later read-only Doctor/SSH inspection found the managed runit service running with valid loopback configuration, and a separate password-authenticated loopback probe to `127.0.0.1:8023` succeeded. The observer did not ingest those later results, so automatic startup and kernel socket ownership remain unverified by that checkpoint.

Native `~/x.sh` was backed up byte-for-byte and its two direct global Wake Lock calls were redirected through the Ternuxx coordinator. A separate live `xgo` session started X11/XFCE and exited; the transient `proot.desktop` lease was removed while `native.sshd` remained registered and the SSH service stayed running. Android exposes only an app-global Wake Lock through these commands, so platform holder state remains unknown even though Ternuxx owner accounting was verified. The launcher retains its pre-existing broad X11/virgl/PulseAudio cleanup; do not invoke it while unrelated graphical/audio workloads are active.

The native repo checkout remains at the recorded commit and its pre-existing dirty paths were preserved. The PRoot rootfs was not modified; its existing `db` alias remains a direct terminal entry, and the existing PRoot process remained present during the isolated `xgo` test. The owner-operated reboot was performed on 2026-10-18. RB03 remains `NOT_READY` with automatic resume disabled because the automated observer did not capture the required service/authentication evidence; RB02 remains the earlier same-boot inconclusive attempt. See [postboot verification evidence](../evidence/2026-10-18-postboot-native-ssh-verification.json).

Native Termux uses the app's Android/Termux identity for its processes. Ternuxx must not assume it can create arbitrary Linux OS users. Keep these identities distinct:

- **Native login principal:** the existing Termux app user that runs `sshd` and native processes.
- **SSH client identity:** the selected client key/user that authenticates to the native SSH endpoint.
- **SSH server identity:** the existing `sshd` host keys that authenticate the endpoint to clients.
- **Ternuxx management principal:** the locally authorized owner/API session allowed to request service operations. It is not a new Android/Unix user, and an SSH login does not automatically grant this management scope.
- **PRoot identity:** a separate guest-side user and SSH configuration. It is not the native login principal.

SSH public-key authentication is the preferred new setup. The current candidate preserves the known password workflow while permitting public-key use; no private key is created or copied. Existing authentication policy must be detected and preserved during discovery/migration; do not silently disable password authentication, replace keys, rotate host identity, change the login principal, or switch ports. Never print private key material. Ternuxx configuration contains references and fingerprints only, not secrets.

## 2. One shared service, multiple adapters

The application service `native_ssh` is the single authority for configuration validation, plan generation, authorization, service ownership, lifecycle transitions, connectivity tests, operation history, and recovery. CLI calls this service directly. Web and X11 GUI call the versioned management API adapter for the same service. No client may write `sshd_config`, `authorized_keys`, boot scripts, key files, or process state directly, and no interface may implement its own SSH lifecycle or launch an unrestricted shell.

Public command shape (namespaced; illustrative until CLI ADR approval):

```text
ternuxx ssh status [--provider native|proot]
ternuxx ssh inspect --provider native
ternuxx ssh setup plan --provider native
ternuxx ssh setup validate --plan <id>
ternuxx ssh setup apply --plan <id> --confirm <token>
ternuxx ssh test --provider native --target loopback|configured-peer
ternuxx ssh start|stop|restart --provider native --plan <id> --confirm <token>
ternuxx ssh boot status|plan|enable|disable --provider native
ternuxx ssh doctor --provider native
```

The final CLI names must follow the project's command conventions. Each CLI/GUI/API operation maps to a named application-service method and stable operation kind, e.g. `ssh.inspect`, `ssh.setup.plan`, `ssh.setup.validate`, `ssh.setup.apply`, `ssh.connectivity.test`, `ssh.service.start`, `ssh.service.stop`, `ssh.service.restart`, `ssh.boot.set`, and `ssh.recover`. Provider is explicit for mutations. Native SSH remains available even when PRoot is absent; a guest-target operation then returns `provider_unavailable` without failing native service health.

Proposed API additions under `/api/v1`:

| Route | Behavior |
|---|---|
| `GET /ssh/providers` | Redacted per-provider service/configuration summary and capability state. |
| `GET /ssh/native/config` | Return the validated Ternuxx-owned policy only; no keys, secrets, arbitrary user config, or full sensitive paths. |
| `POST /ssh/native/inspect` | Read-only discovery of package, active service owner, effective redacted policy, endpoint and connectivity status. |
| `POST /ssh/native/setup/plan` | Produce a no-side-effect compatibility/migration plan and exact impact. |
| `POST /ssh/native/setup/validate` | Validate a staged candidate without replacing the active config or interrupting the existing session. |
| `POST /ssh/native/connectivity-test` | Run a bounded authentication/connection check for a configured target; return structured result without credentials. |
| `POST /ssh/native/service/{start,stop,restart}/plan` | Preview ownership, target, listener impact, active sessions, boot and Wake Lock effects. Apply only by the common single-use plan confirmation flow. |
| `POST /ssh/native/boot/plan` | Preview a Termux:Boot change, rendered native-only script, disable/rollback path, dependencies, and Wake Lock policy. Does not write the boot directory. |

These routes are candidates, not implemented endpoints. They reuse the plan/confirm/operation contract and the local-web security rules in [MANAGEMENT-API.md](MANAGEMENT-API.md). No generic command or shell route is allowed.

## 3. Configuration, secrets, runtime state

Use three separate stores, all under Native Termux private app storage with restrictive permissions:

1. **Desired configuration:** versioned non-secret policy, using [native SSH config schema](../../schemas/native-ssh-config.schema.json). It records provider, login principal kind, selected auth method, endpoint/bind policy, auto-start preference, Wake Lock policy, migration provenance, and opaque secret/key references if applicable. It does not contain private key bytes, passwords, recovery codes, full `sshd` output, or raw user configuration.
2. **Secret/key material:** separate secret store or user-selected existing key location referenced by opaque ID. Host private keys and client private keys have distinct roles and references. Never copy/overwrite an existing key. If a new key is explicitly requested, generate only at a new unused path after consent and verify permissions; disclose passphrase handling and recovery. If no protected secret-store capability is available, use an owner-selected private file with restrictive permissions and say that it is file-protected, not hardware-backed. Never place secrets in Git, public logs, screenshots, ordinary Doctor output, operation records, or backups by default.
3. **Observed runtime and continuity state:** ephemeral service status plus durable, sanitized operation/checkpoint records following [native SSH service-state schema](../../schemas/native-ssh-service-state.schema.json). Record owner/provider, opaque operation ID, PID identity needed for stale-process checks, effective endpoint, health timestamp, auth-policy label, boot attempt, Wake Lock lease owner, and redacted result. No secret values or private key contents.

The existing OpenSSH configuration and host identity are external until verified and explicitly adopted. Discovery must distinguish `external_unmanaged`, `ternuxx_managed`, and `unknown_owner`. Do not run duplicate `sshd` instances on one endpoint. Adoption is opt-in, previewed, backed up within private storage without copying secret material into public evidence, and reversible. A new config is staged separately and syntax-checked. A connectivity/authentication smoke test must succeed on a controlled loopback test endpoint or another validated non-conflicting endpoint before any active endpoint cutover. If the old and replacement services cannot coexist during validation, defer cutover and explain the interruption window; do not stop the old service first.

## 4. First-install and migration workflow

The wizard is a UI for application-service plans, not a privileged shell script.

1. **Inspect, read-only:** identify Termux/native context, OpenSSH presence/version, current `sshd` process/service manager, active endpoint, redacted effective auth policy, host-key fingerprints, client-key fingerprints available by explicit selection, existing boot hook ownership, and current connectivity. Do not enumerate unrelated files or dump key/config contents into logs. Unknown fields stay `UNKNOWN`.
2. **Classify:** determine whether no service exists, a Ternuxx-owned service exists, or an external/manual service exists. If ownership is ambiguous, stop before mutation and offer read-only guidance.
3. **Select identity/auth:** retain the existing Termux login principal. Prefer public-key auth. The user may select a known existing client identity or explicitly request a new one at an unused destination. Preserve working auth until replacement validation and cutover are approved. Never create an OS user implicitly.
4. **Plan:** show selected key fingerprint (never key bytes), endpoint/bind/port, auth transition, host-key impact, boot changes, Wake Lock policy, existing sessions affected, rollback, and exact paths owned by Ternuxx. Keep LAN binding off unless explicitly selected and separately confirmed. No configuration is persisted during inspect or plan.
5. **Stage and validate:** write candidate files only to a private staging location. Validate schema, `sshd` syntax, file ownership/mode, provider/identity, port availability, host-key continuity, and the selected authentication method. Test a real authenticated client connection to the candidate on a bounded temporary loopback endpoint where feasible. A failed check deletes only the candidate and retains the old active policy/service unchanged.
6. **Confirm and apply:** require an explicit, session-bound, single-use confirmation for the exact plan hash. Recheck state to detect drift. Persist the validated desired configuration atomically only after the candidate has passed the authenticated connectivity test. Apply by starting the replacement and verifying authenticated connectivity on its configured endpoint before retiring any Ternuxx-owned old process. Never terminate an external process by name. If same-port cutover cannot preserve the active session, present the interruption and rollback plan and wait for a separate user-approved maintenance window.
7. **Verify and recover:** verify the expected client can authenticate, the server identity is stable, the listener is on the approved address, unauthorized access is rejected, and status is consistent. On failure restore the last validated Ternuxx-owned config and service state; never restore over an external config without a new plan/confirmation. Emit a sanitized report.
8. **Enable boot separately:** only after successful manual service validation, preview a native-only Termux:Boot entry and require explicit enablement. It must not call `db`, `xgo`, `~/x.sh`, PRoot login, or an agent. Repeated boot invocation is idempotent. Termux:Boot absence leaves manual SSH and CLI service controls available and reports auto-start unavailable.

## 5. Service state and transitions

Desired policy and observed process state are separate. Use the state record schema and allow only these transitions:

```text
unconfigured → inspecting → plan_ready → staging → validating
validating → plan_ready (validation failed; active service unchanged)
validating → ready_to_apply → starting → health_check
health_check → running (authenticated check passes)
health_check → recovery_required (candidate fails; retain/restore validated old state)
running → stopping → stopped
running → restarting → starting
any observed state → degraded | failed | unknown_owner
booted → inspecting → starting native services → health_check → running|degraded
```

Transitions are journaled before a mutation. Retried requests use an idempotency key/operation ID and must not start duplicate daemons or create repeated boot hooks. `stop` and `restart` act only on a process whose recorded owner, executable, PID start time, config identity, and listener match. External/ambiguous processes are never killed. `stop` must reject if it would sever the caller's only active management session unless the user has an out-of-band recovery path or explicitly confirms a narrowly described disconnect.

Errors use stable codes compatible with the management API: `provider_unavailable`, `not_installed`, `unknown_owner`, `active_config_unreadable`, `auth_policy_conflict`, `key_reference_invalid`, `host_key_changed`, `listener_conflict`, `candidate_invalid`, `authentication_failed`, `permission_denied`, `plan_expired`, `state_changed`, `service_not_ready`, `boot_unavailable`, `wakelock_unavailable`, `recovery_required`, and `operation_timeout`. Errors must identify the provider and safe recovery action without returning passwords, private key paths, raw config, full environment, or sensitive Android paths.

## 6. Authorization and local interface security

- Native CLI actions run under the existing Termux app identity and still require the command's configured confirmation policy. Do not imply that Termux app identity is root or a new OS-user boundary.
- Local Web UI session authentication is a separate management credential/session. It is short-lived, unpredictable, not placed in URLs or localStorage, scoped by action, protected by same-origin/Host validation and CSRF defenses, and never accepted as SSH login proof.
- X11 GUI uses the same application service and authorization decision. A local GUI button cannot bypass the API/service layer or raw-command restrictions.
- SSH client authentication proves the client key controls a permitted SSH principal; it does not alone authorize Ternuxx management. PRoot-to-native diagnostics use a named allowlisted request with independent operation authorization, bounded arguments and timeouts.
- Remote/LAN management UI remains disabled unless a separate threat model and owner-approved scope exist. SSH listener exposure and management UI exposure are distinct settings.
- Logs and events record authentication method/status, key fingerprint when necessary, provider, target, operation and outcome; they do not record secrets or full request payloads.

## 7. Termux:Boot, Wake Lock, and PRoot

Native Termux:Boot is the recovery owner for native SSH. Its entry point invokes the native orchestrator directly, checks whether `sshd` is already healthy, and records an idempotent result in native private storage. It does not depend on PRoot, Debian systemd, a guest-mounted state file, or a live agent. Boot auto-start is a separate opt-in from installing/configuring SSH.

Wake Lock policy defaults to `never`. If an owner enables `while_owned_service_active`, the native service acquires a uniquely identified lease only for the verified active workload that needs it, journals the lease owner, renews/monitors it within Android constraints, and releases only that lease on stop/health completion. A PRoot stop cannot release a native SSH/other native service lease. Multiple workloads require reference-counted distinct leases; a broad global release is forbidden. If Termux:API Wake Lock support is unavailable, report the limitation and continue without silently changing the policy.

PRoot can use a configured native SSH endpoint for authorized bounded diagnostics. The endpoint must reject shell injection, unknown operation IDs, out-of-scope paths, stale authorization, missing timeout, and repeated/expired requests. Native service status and continuity remain available when PRoot stops. Guest task checkpoints are written by the native management layer; after reboot, the agent resumes only after a fresh guest session is started and the owner asks it to continue.

## 8. Test contract and fixtures

Contract tests must run against a fake service adapter and temporary private state, then physical-device tests must verify only the supported Termux behaviors. CI/mocks cannot qualify Android boot or a real SSH connection. Fixture layout is under [`tests/fixtures/ssh/`](../../tests/fixtures/ssh/README.md); it must contain synthetic metadata only, never real keys or the owner's current config.

| Test ID | Scenario | Required assertion |
|---|---|---|
| SSH-01 | Fresh native setup with no existing service | Correct Termux principal, selected key auth, candidate validation, authenticated test, then atomic config persistence. |
| SSH-02 | Invalid candidate / failed connectivity | Old active config/service/session remains unchanged; staging is removed or marked for bounded recovery; no success state. |
| SSH-03 | Existing manual password or mixed-auth setup | Read-only inventory redacts values; migration plan preserves current auth/key/host identity and listener until replacement has passed and the owner confirms. |
| SSH-04 | Existing client/host keys already at destination | Refuse overwrite; offer explicit alternate path or reuse by selected fingerprint. |
| SSH-05 | Authenticated client connection | Correct selected public key authenticates to the expected Termux principal and stable server fingerprint; no password/key bytes in output. |
| SSH-06 | Wrong/unauthorized key | Authentication rejected; no Ternuxx management operation is authorized. |
| SSH-07 | CLI/API/GUI parity | Same config revision, service status, operation ID and policy result from each available interface; GUI/Web never write config directly. |
| SSH-08 | Repeated restart/setup/boot invocation | Idempotent; no duplicate daemon, boot hook, listener, or Wake Lock lease. |
| SSH-09 | Termux:Boot recovery with PRoot absent | Native sshd and continuity recover without guest entry/agent; PRoot-target operations alone report unavailable. |
| SSH-10 | Wake Lock ownership | Correct lease acquired/released; stopping SSH or PRoot cannot release another workload's lease; default is no lock. |
| SSH-11 | Native/PRoot independence | Stop PRoot and verify native SSH/continuity; restart native SSH and verify PRoot rootfs/session/state unchanged. |
| SSH-12 | Continuity verification | After a reboot, a new process reads the native checkpoint and classifies pending guest work; no assumption that the previous agent survived. |
| SSH-13 | Unauthorized API and cross-provider request | Missing/expired session, CSRF/origin failure, unauthorized operation ID, unbounded input, or absent confirmation is rejected at backend boundary. |
| SSH-14 | Interface unavailable | CLI can inspect/manage authorized service when GUI/Web/X11 is unavailable; unavailable interfaces do not change service state. |
| SSH-15 | External process/port conflict | Unknown `sshd` is reported and not killed, adopted, or displaced; no port takeover. |

Fixtures must cover: `fresh_unconfigured`, `external_manual_key_auth`, `external_manual_password_auth` (synthetic metadata only), `unknown_owner`, `candidate_invalid`, `listener_conflict`, `stale_pid`, `host_key_changed`, `boot_missing`, `pr​​oot_unavailable`, and `wakelock_owned_by_other_service`. Each fixture has expected state transitions and redaction assertions.

## 9. Interface implementation status

| Interface | Current status | Evidence needed before claiming SSH management |
|---|---|---|
| CLI | Partial fixed-unit lifecycle exists: inspect plus preview/apply start and stop for ternuxx-sshd after exact source/installed-definition identity checks; plans are journaled before sv up/down. SSH setup, config migration, authenticated post-action health, and caller-session correlation remain incomplete. | Fixture transition/journal tests plus read-only target preview and identity evidence exist. Still required: separately authorized target start/stop, authenticated health, conflict/session-disconnect tests, and provider/interface parity. |
| Web Visualizer | No management HTTP server/client exists per [management API status](MANAGEMENT-API.md). | Authenticated API contract, local security tests, and UI workflow using the same service. |
| X11 GUI | No Ternuxx management GUI exists per [unified architecture](UNIFIED-WORKSTATION.md). | UI calls shared application service; smoke/physical-device evidence and parity check. |

Do not label any interface's SSH management as implemented based on this design, a schema, or a backend-only test. The repository's current manual SSH setup must be inspected read-only and redacted before migration implementation is planned. The pre-existing workflow baseline (`xgo` graphical launch and `db` PRoot entry) remains protected and should be checked as part of regression qualification.

## 8023 source reconciliation (2026-10-18)

The installed Runit `run` file was read-only compared with the repository source. Its SHA-256 matched the historical Git blob for the same path at `025023e`, while the current source had a different hash. The diff was four old/current environment-variable, log-path, and permission-target lines; it did not identify a different service unit. This is confirmed stale deployment after repository identity/path cleanup. The new `ssh.service.deploy` workflow validates the source shell syntax and managed SSH config, emits a hash-bound plan and exact diff, then atomically replaces only the fixed run file after exact-plan confirmation. It snapshots the old bytes, journals the operation, verifies the write, and automatically restores on failure. Explicit rollback is preview-first. Neither path calls Runit up/down/restart, changes sshd config, or affects port 8022. Fixture tests cover write failure and manual recovery.

The current managed config and service log indicate loopback `127.0.0.1:8023`; Runit reports the service running and process ancestry is visible. Android denied reads of `/proc/net/tcp` and `/proc/net/tcp6`, preventing socket inode to process-FD correlation. Listener ownership therefore remains `UNVERIFIED`. No live start/stop/restart or reboot was performed. See [8023 deployment and lifecycle qualification](../testing/8023-deployment-and-lifecycle.md) and [current gate evidence](../evidence/2026-10-18-8023-reconciliation.md).


## Current 8023 lifecycle result (2026-10-18)

The earlier reconciliation and listener-ownership notes above are historical checkpoints and are superseded for the current boot by [8023 lifecycle qualification evidence](../evidence/2026-10-18-8023-lifecycle-qualification.md). The later CLI/state continuation supersedes the installed-entrypoint details here. `$PREFIX/bin/ternuxx` now dispatches through Termux Bash to the source checkout; prior-name executable and module aliases remained intact at that checkpoint. The service source and installed definition match at SHA-256 `1dc73681a09d606b265db8add60e4870c144a50b31da7b3ba0a7db3c7ab932f6`. Current service and loopback SSH banner pass; stale lease PID 12951 was cleared only after kernel-confirmed absence, while ambiguous identity fails closed. A later owner-provided interactive loopback SSH probe returned `authenticated-loopback-ok`; ADB socket inode 2372520 maps to managed sshd PID 22443 FD 6 and Runit ancestry. Current authenticated readiness and listener ownership are VERIFIED. 8022 listener inode 135149 maps to PID 16337 FD 7 and remained active. No SSH policy change or reboot occurred. See [CLI/state evidence](../evidence/2026-10-18-cli-entrypoint-state-reconciliation.md).
