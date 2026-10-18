# Ternuxx product and commercialization readiness

**Audit date:** 2026-10-17
**Repository audited:** `soobujmiah/nativeternux` before owner-authorized rename; current identity is [`soobujmiah/ternuxx`](https://github.com/soobujmiah/ternuxx), public, `main` at `1a891fa`
**Canonical product brand:** Ternuxx (owner-fixed spelling)
**Repository at original audit snapshot:** `soobujmiah/nativeternux` (public). Owner-authorized rename to `soobujmiah/ternuxx` was completed and verified on 2026-10-17.
**Document status:** internal planning draft; research, not legal/accounting advice
**Boundary:** the original audit was read-only research. Subsequent owner-approved local work corrected repository identity/help documentation, added rename and CLI-help checks, and updated the repository-contract workflow. It has not selected or added a license, changed external repository settings beyond the already approved rename, built a website, collected data, accepted payment, deployed, or touched the Android/PRoot environment.

## Read this first

The repository is public but has no license file or published release. Public visibility does not make the code open source. The first committed README and code headers asserted a noncommercial license plus a separate commercial-use addendum; the referenced files were absent from the initial tree and remain absent. This needs legal review before anyone treats the old statement as either a valid grant or a cleanly superseded draft.

The owner-authorized GitHub rename to `soobujmiah/ternuxx` is complete and verified. `ternuxx` is now the canonical source-checkout command; `nativeternux` remains a compatibility entry point. The deterministic repository-knowledge project ID and existing installed state/library paths still use the legacy identifier until a separately validated migration is approved. Historical records keep their captured names. See the [migration inventory and implementation addendum](NAME-MIGRATION-INVENTORY.md).

## Documents

- [Repository and implementation evidence matrix](REPOSITORY-AUDIT.md)
- [Pre-edit name migration inventory](NAME-MIGRATION-INVENTORY.md)
- [Bangladesh-first legal, IP, and license research](LEGAL-IP.md)
- [Product positioning, alternatives, business model, service and pricing hypotheses](PRODUCT-MARKET-COMMERCIAL.md)
- [Website, portfolio integration, SEO, hosting, releases, and maintenance](WEBSITE-SEO-OPERATIONS.md)
- [Security, privacy, and supply-chain threat model](THREAT-MODEL.md)
- [Free-core boundary, payment, entitlement, and premium delivery design](PREMIUM-DISTRIBUTION.md)
- [CPU/GPU/NPU testing and evidence documentation](../testing/README.md)
- [Owner decision register and approval-gated backlog](DECISIONS-AND-PLAN.md)

## Evidence labels

`VERIFIED` means directly observed in the audited repository, GitHub metadata, or an official source on the audit date. `PARTIALLY_VERIFIED` means the source or one workflow is present but important runtime/customer evidence is missing. `PLANNED` means a project document describes a future feature. `NOT_IMPLEMENTED` means the audited source does not implement it. `UNKNOWN` means evidence was insufficient. `DECISION_REQUIRED` is reserved for an owner or professional decision.

## Addendum audit coverage and gate

| Area | Audit outcome | Remaining gate |
|---|---|---|
| Repository visibility/history/releases/license | Verified public repo; no releases/license; historical PolyForm/addendum claim recorded | Counsel review and approved license/provenance decision |
| Ternuxx naming | GitHub slug is `soobujmiah/ternuxx`; `ternuxx` checkout command is present; `nativeternux` compatibility command retained | Installed path/state migration and SKB internal project ID remain legacy; no migration applied to existing device |
| Third-party and source provenance | Initial dependency/runtime inventory and internal SKB code reuse documented | Exact build-resolved SBOM and redistribution matrix require a real release candidate |
| Core versus premium | No premium SKU exists; free-core intent and no-lock boundary documented | Legal review of public history and any future component before sale |
| Payment, entitlement, fulfillment | Provider-neutral server-side state machine and secure artifact design specified | No provider, seller, SKU, backend, private artifacts, refund policy or privacy notice approved |
| Website, portfolio, SEO, downloads | Sitemap, evidence rules, host options, SEO map and portfolio boundary documented | No site exists; portfolio change and preview/production deployment require separate scope |
| Services, packages, pricing | Hypotheses and unvalidated BDT arithmetic identified | No service is offered; demand, terms, tax, payment and owner capacity unknown |
| Security/privacy/recovery | Threat boundaries and minimum web/payment controls recorded | No product tests, release signing, staffed disclosure route, or approved customer-data operations |
| Roadmap/manifest/ADR/SKB | Existing roadmap and deterministic workflow identified | Stable `nativeternux` internal project key must not change until registry migration is approved |
| CPU/GPU/NPU inference and evidence | Current code and dated hardware evidence audited; runtime candidates and test method documented in `docs/testing/` | No backend implementation, report, or measurement; exact hardware/backend acceptance remains owner-operated |

**Readiness result:** the research and planning documents specify a future design, but the commercial-readiness acceptance criteria are not fully met. The repository rename is complete; the compatible CLI/internal state names remain; no license, premium artifact, legal terms, or real offer has been approved. The website, payment, and legal publication gates remain closed. Product-source work is being tracked separately from this commercialization research and must retain its own tests and device-approval gates.

The next repository tasks are to complete the safe current-facing naming audit, keep the CLI compatibility path documented, and continue isolated tests for the native lifecycle and provider contracts. Remote CI remains unverified until the owner commits and pushes. License, seller/payment route, trademark, and customer terms remain separate owner/professional decisions.

## Recommended sequence

1. Resolve license-history/provenance and brand/trademark decisions with qualified counsel before any license, product-site legal copy, contribution invitation, or commercial distribution.
2. Complete and physically qualify the minimum safe workstation path, including the existing Ternux PRoot adapter without changing Ternux itself.
3. Add recovery and release evidence. Then create a static, evidence-led product site on hosting suitable for commercial promotion.
4. Validate demand with a small number of consent-based, manually scoped service pilots before considering premium modules or payments.

The repository rename is complete; CLI/path migration, SKB registry identity update, website implementation, and payment backend are separate tasks. No production deployment is claimed by this audit.

Nothing in this folder is an approved legal policy, final price list, customer commitment, or product capability claim.
