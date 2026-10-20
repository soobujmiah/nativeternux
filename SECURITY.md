# Security and privacy

Ternuxx manages local desktop processes, optional network listeners, Android-facing integrations, and user-selected files. This is a high-risk local operations tool. Ternuxx must preserve Android security boundaries and must never imply that PRoot is a security sandbox.

## Scope and data

The tool may inspect Termux package metadata, its own session state, process metadata needed to validate ownership, and explicitly selected files. It must not scan `/sdcard`, `/storage/emulated/0`, or other shared storage by default. User file handoff must name exact paths and actions. SSH private keys, passwords, tokens, app payloads, and unredacted private logs must never be copied to documentation, SKB, or diagnostic output.

Ternuxx state and backups remain under Ternuxx-owned paths. Before reset/restore/removal, show exact affected paths and preserve user data by default. Never delete, minimize, upgrade, or repair the independent Ternux rootfs/launcher.

## Service security

- SSH services are separate host and guest providers with distinct accounts, keys, configs, logs, and ports.
- Default to loopback binding and key authentication; deny root login. LAN exposure requires explicit provider, address, port, firewall/network context, and authentication review.
- Do not adopt, stop, or overwrite an unmanaged SSH daemon/configuration.
- PRoot shares the Android app's network context and is not a network/security boundary.
- Wireless ADB stays disabled unless a separately reviewed, explicit owner operation configures the Android-supported pairing. Never expose pairing codes or ADB credentials in logs.

## Android integrations and automation

Termux:Boot and Termux:API are optional, least-privilege integrations. Shizuku is optional and may expose elevated Android operations; every capability must be enumerated, previewed, and separately authorized. A watchdog must use bounded retries and cannot bypass Android's own permissions, SELinux, thermal protections, or user consent.

Read-only Doctor is the default. Mutations require an exact plan, user-visible provider/scope, a durable pre-operation journal, and an explicit confirmation. Recovery must fail closed if process identity or path ownership is ambiguous. Do not use broad `pkill`, wildcard socket deletion, or unbounded cleanup.

## Logging and network

Logs exclude secrets, private file contents, and unnecessary identifiers. Remote software catalog entries use official upstream/project release URLs and integrity metadata where applicable. Never execute remote install scripts through a pipe or allow a website catalog to invoke shell commands. Network fetches and package operations need a current source/version and transaction preview.

## Reporting

Report suspected vulnerabilities privately through the repository owner's existing GitHub contact channel. Do not publish exploit details or device credentials in public issues.

## Current limits

No public release, supported device matrix, implemented remote service management, NPU path, or broad app compatibility is claimed. See [research](docs/RESEARCH.md), [operations](docs/OPERATIONS.md), [security decisions](docs/architecture/decisions/), and [current status](CURRENT_STATE.md).


### 2026-10-18 managed SSH observation

The 8023 managed service configuration and its startup log showed loopback `127.0.0.1:8023`; its effective configuration has password, public-key and keyboard-interactive authentication enabled, and root key login is not denied. The source/install run-file drift was reconciled without changing SSH configuration or restarting the active service. The Runit process ancestry was visible, but Android denied reads of `/proc/net/tcp` and `/proc/net/tcp6`, so socket-to-process ownership and listener exposure beyond the observed loopback configuration remain `UNVERIFIED`. Configuration text, an SSH banner, and a visible process tree are not listener ownership proof. The separately owner-started 8022 development channel remains a separate manual endpoint; its inspected configuration is wildcard-bound and password/keyboard-interactive enabled, while actual listener ownership and external reachability are unknown. Neither endpoint's exposure or authentication was changed in this gate. See the dated [8023 evidence](docs/evidence/2026-10-18-8023-reconciliation.md).


### 2026-10-18 live bind follow-up

ADB `toybox netstat -ltnp` on device `[redacted device serial]` observed actual 8022 listeners on `0.0.0.0` and `[::]`, and the managed 8023 listener on `127.0.0.1`. This confirms the bind addresses, not the owning PID. The 8022 wildcard listener is a current exposure risk; its authentication/configuration and active development workflow were not changed. Android shell lists no PID for either socket and denies `/proc/13449/fd`, so socket-to-process ownership remains UNVERIFIED. See the [dated evidence](docs/evidence/2026-10-18-live-session-state-reconciliation.json).


### Listener ownership correlation follow-up — 2026-10-18

The previous observation's ownership limitation is superseded for the current listener snapshot. ADB `/proc/net/tcp` and `/proc/net/tcp6` exposed socket inodes and binds; the Native Termux shell (UID 10490) could inspect same-UID process FDs. Inodes `135149` (IPv4 wildcard 8022) and `135147` (IPv6 wildcard 8022) map to sshd PID 16337 FDs 7 and 6. Inode `117876` (`127.0.0.1:8023`) maps to managed sshd PID 13449 FD 6 under Runit PID 13061. Thus listener ownership and binds are verified for this snapshot. The 8022 wildcard/password-enabled posture remains a risk; external reachability was not tested and no policy was changed. See the [live evidence](docs/evidence/2026-10-18-live-session-state-reconciliation.json).


### 2026-10-20 managed SSH authentication follow-up

After key-only loopback access was verified, the managed ternuxx-sshd configuration on 127.0.0.1:8023 was changed to public-key-only authentication; password and keyboard-interactive authentication are disabled and root login is denied. The prior exact config is retained in a mode-0600 rollback file under the Termux home. sshd -t, effective sshd -T, managed Runit readiness, post-change key-only login, and recovery through unchanged 8022 passed. External reachability was not tested. See current execution evidence at docs/evidence/2026-10-20-workstation-qualification-execution.md.
