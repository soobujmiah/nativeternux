# SKB knowledge synchronization

This project is authorized for internal, evidence-reviewed knowledge return to `soobujmiah/skb`. Read the current canonical `governance/KNOWLEDGE_RETURN_PROTOCOL.md`, `standards/automatic-knowledge-sync.md`, and `governance/DETERMINISTIC_STATE_SYNC_POLICY.md` from the verified SKB checkout before a substantive return.

## Two distinct paths

- **Deterministic repository state:** after onboarding, this repository's CI uses vendored SKB `tools/repo_knowledge` to update only this repository's `.repo/` using this repository's own `GITHUB_TOKEN`. SKB pulls registered state through its read-only registry integration. Never add an SKB write token or a cross-repository write workflow here.
- **Human-authored durable knowledge:** agents classify evidence and update the best canonical SKB state/technical/topic record when authenticated write access and current policy permit it. Otherwise preserve a structured pending return and report it. Never sync secrets, device credentials, transient logs, or unnecessary private payloads.

## Privacy and readiness

This repository is owner-reported private and SKB membership is restricted to internal projection. Do not publish its device-specific evidence or status. Membership eligibility and participation approval are recorded; the canonical readiness validator returned READY. Ternuxx's first state-contract and status-sync workflows passed on `735c1aa`, with build/test honestly unknown. Registry registration and first central App-backed pull are next. Repository instructions never supply credentials; agents must verify authenticated identity/access independently.

The local workflow and source boundaries are described in [Documentation, status, and SKB knowledge return](docs/KNOWLEDGE-SYNC.md). SKB is the authority for its protocol; this pointer does not copy or override that policy.

For central mechanical sync, the SKB Registry Reader App must be configured for this repository with read-only Contents access. The owner confirmed the selection was updated. The latest successful receipt's minted-token scope predates Ternuxx registration, so a pull after registration is the required effective-access verification. Do not add cross-repository credentials to this project.

Reference review found `ternux` in the receipt's selected repository list. Its locally inspected workflow revision had an optional cross-repository dispatch secret; Ternuxx intentionally omits that legacy pattern and relies on SKB's scheduled/manual pull under the current policy.
