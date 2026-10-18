# Ternuxx security, privacy and supply-chain threat model

**Reviewed:** 2026-10-18. This is a design review of the current repository and planned website, not a penetration test or security certification. The off-home access requirements are architecture-only and have not been implemented or tested.

## Assets and trust boundaries

| Asset/boundary | Current or future data | Main risk |
|---|---|---|
| Android/Termux app sandbox | Package metadata, private CLI state, local processes, user-selected files | A shell tool can mutate packages, run arbitrary local commands or expose user files if its scope is wrong |
| Existing Ternux Debian PRoot | Rootfs, launcher, display/audio and current workloads | PRoot is not a kernel security boundary; a wrong integration can damage or terminate the owner-managed setup |
| Native ↔ PRoot handoff | Arguments, selected workspaces, environment, display/audio endpoints | Injection, unintended file exposure, credential crossing, duplicate lifecycle ownership |
| SSH/ADB (planned) | Keys, ports, pairing state, remote command surface | Unauthenticated/LAN exposure, secret leakage, persistent privileged shell |
| Package and release pipeline | APT metadata, Python dependency, Actions, source archives/artifacts | Compromised action/dependency, wrong repository/version, unverified binary, misleading checksum |
| Website/hosting | Public content, deployment secrets, access logs, possible future contact/analytics data | Supply-chain compromise, accidental private data publication, hostile form submissions, provider/account takeover |
| Support operation | Customer-selected logs/device facts, possible remote session | Overcollection, credential exposure, unauthorized change, unclear retention/liability |
| Proposed local management API / visualizer | Local configuration, model metadata, operation records, service actions | A hostile web origin, local webpage, CSRF, or compromised UI could trigger privileged local actions |
| Proposed inference gateway | Prompts, model inputs/outputs, provider credentials, routing policy | Prompt exfiltration, accidental cloud fallback, credential disclosure, expensive/unbounded requests |
| Proposed model library | User-selected model files, metadata, checksums and licenses | Path traversal, malicious/untrusted artifact, license violation, accidental shared-storage crawl |

## Proposed visualizer and AI-runtime controls (not implemented)

- Keep management and inference APIs separate. Management endpoints authorize workstation changes; inference endpoints cannot install packages, alter services, or access arbitrary files.
- The initial dashboard is same-origin and loopback-only. Validate Host and Origin, reject wildcard CORS, use CSRF/session defenses, limit request sizes/rates, and do not bind to LAN/public addresses. A local browser is not inherently trusted.
- Every mutation follows an exact preview, explicit confirmation bound to that plan and current state, an operation journal, and a verified outcome. Do not offer a generic shell or generic file-write route.
- Keep CLI and dashboard on the same application services and permission checks. A UI route cannot bypass preview, scope, provider ownership, or confirmation rules.
- Model paths are confined after canonicalization to the managed model directory or an explicitly selected file. Reject traversal/symlink escape; verify hashes and show source/license before download/use. Never scan shared storage by default.
- Do not expose provider keys to frontend code or return them from APIs. Store credentials only in a reviewed private mechanism; do not write them into URLs, operation logs, diagnostics, or exports.
- Do not log inference prompts, outputs, or cloud secrets by default. Cloud routing is opt-in and visible per request; never silently fall back from local to a cloud provider. Disclose data destination and potential charges.
- Tool execution is a named allowlisted capability registry. File deletion, package changes, external network changes, boot changes, and recovery require a preview and appropriate confirmation.
- Local operation history is bounded and redacted. Diagnostics export previews fields and removes serials, usernames, private paths and secret-like data before writing a user-selected export.
- No dashboard analytics/telemetry by default. Optional off-home access is an owner-approved product requirement in [ADR-0013](../architecture/decisions/ADR-0013-owner-controlled-remote-access.md), but its transport implementation and device enablement remain pending a threat review and explicit owner action. Keep it disabled by default, use a private VPN/tunnel path, and do not add direct WAN listeners or router port-forwards by default.

These are design requirements, not security controls already present or security certification. The proposed route and operation lifecycle is specified in [`../architecture/MANAGEMENT-API.md`](../architecture/MANAGEMENT-API.md); the full product boundary is in [`../architecture/UNIFIED-WORKSTATION.md`](../architecture/UNIFIED-WORKSTATION.md).

## Attacker and failure cases

1. Malicious or compromised Termux package/repository, OCI/rootfs image, GitHub Action or PyPI dependency.
2. Malicious issue/PR or compromised owner account modifying a shell workflow or release link.
3. PID reuse or process-name collision causing stop to target an unrelated session.
4. X11 socket/display conflict, partial startup or Android background limit leaving orphan processes.
5. Unsafe provider routing passing shell metacharacters or broad environment/credential state into the existing guest.
6. Customer or visitor submits SSH keys, tokens, private logs or shared-storage paths through support channels.
7. Unreviewed brand/logo/font/screenshot/binary/model introduced into source/site without redistribution rights.
8. A fake “GPU/NPU accelerated” or “secure sandbox” statement causes a user to trust an unverified backend or PRoot isolation.

## Current controls and gaps

**Present in docs/source:** explicit separation of Termux and PRoot providers; existing Ternux must remain untouched; package installer has preview/explicit `--yes`; native desktop state uses owner markers and PID start ticks; security policy rejects broad shared-storage scanning and unbounded cleanup; CI job permissions are mostly read-only with a narrow same-repo write job for generated `.repo` state; no SKB write token; no telemetry/form/payment system.

**Not established:** product tests, physical-device lifecycle test, PRoot adapter, recovery journal/backup implementation, SSH management, secure release signing/provenance, lockfile/SBOM, vulnerability response staffing/SLA, security scan, web host, privacy notice, customer-data policy and legal entity/payment readiness.

**Source review finding (corrected locally):** the previous `lib/help.sh` incorrectly described package installation/start as stubs while source paths can perform them. Help now discloses process/package mutation boundaries, and a CLI help contract test is wired into the repository-contract workflow. The workflow has not run remotely, and this does not qualify lifecycle or installation behavior; do not run `install --yes` without the separate operation authorization.

## Security requirements before release

- Treat PRoot as a userland/compatibility boundary, not a security sandbox. No privileged Android operation is implied by PRoot.
- Install is preview-first, repository-provenance checked, refuses unapproved upgrades/removals, and prints exact package set/scope. Re-check source and lock around transaction; document rollback limitations.
- Process control verifies process start identity, executable marker, owning state path and display. Ambiguous records fail closed. No broad `pkill`, wildcard socket deletion or `kill -9` fallback.
- Native↔guest execution uses argv arrays and allowlisted environment; no `eval`/shell concatenation. File sharing names explicit selected paths and never mounts all of `HOME`, `.ssh`, `.config` or shared storage by default.
- SSH defaults, if ever implemented, are loopback + keys + no root login + distinct host/guest configs; LAN binding is explicit. Wireless ADB remains off; no pairing keys/codes in logs.
- No automatic remote shell, silent privilege escalation, Shizuku watchdog restart loop or device setting change.
- Diagnostics redact Android serial, usernames, paths and locally identifying information before any user shares them. An export/report needs a preview and redaction policy.
- Threat model, dependency inventory and test evidence are updated with each new provider/service/website form.

## Website/privacy controls before production

- Static content only for the first release; no backend, login, form, cookies, analytics or payment.
- If contact forms are added later: collect only contact method, chosen request and necessary device profile; publish purpose, lawful basis, processor/host, data location, access, deletion/retention and contact for privacy requests after counsel review.
- Use server-side validation, rate limits, CSRF protection, output encoding, spam controls that minimize third-party data transfer; never accept credentials, private keys or full device dumps.
- Draft privacy notice/terms stay unpublished until approved; do not pretend a placeholder is final.
- Hosting account MFA, least privilege, domain lock/recovery, secret rotation, deployment review and immutable rollback artifact required.
- Set restrictive CSP and security headers if host permits; test rather than copying a generic policy. Disable inline scripts and third-party embeds unless required.
- No analytics by default; if approved, document provider, data categories, region, retention, consent/opt-out and access list.

## Release supply-chain requirements

1. Pin GitHub Actions by full commit SHA; review action source and permissions.
2. Lock Python/web dependencies and enable a controlled update/alert path.
3. Produce a software bill of materials and include license/notice manifest for distributed artifacts.
4. Build from a reviewed tag; attach checksum and signing/provenance record; verify from a clean download.
5. Ensure release source, website claims, compatibility evidence and actual artifact all identify the same version/commit.
6. Define compromised-artifact revocation and replacement notice process before publishing installers.

## Incident and vulnerability response

GitHub currently exposes `SECURITY.md`, but it gives only a generic private-reporting direction. Before release, choose a private channel and owner, triage schedule, disclosure coordination, evidence preservation and customer notification process. Do not promise an SLA until the owner can sustain it. Any incident involving credentials or device logs should rotate/revoke affected material first and remove/redact public copies through a controlled process; preserve enough audit trail without publishing secrets.
