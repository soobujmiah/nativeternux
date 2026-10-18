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
