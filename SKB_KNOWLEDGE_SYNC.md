# SKB knowledge synchronization

This project is authorized for internal, evidence-reviewed knowledge return to `soobujmiah/skb`. Read the current canonical `governance/KNOWLEDGE_RETURN_PROTOCOL.md`, `standards/automatic-knowledge-sync.md`, and `governance/DETERMINISTIC_STATE_SYNC_POLICY.md` from the verified SKB checkout before a substantive return.

## Two distinct paths

- **Deterministic repository state:** after onboarding, this repository's CI uses vendored SKB `tools/repo_knowledge` to update only this repository's `.repo/` using this repository's own `GITHUB_TOKEN`. SKB pulls registered state through its read-only registry integration. Never add an SKB write token or a cross-repository write workflow here.
- **Human-authored durable knowledge:** agents classify evidence and update the best canonical SKB state/technical/topic record when authenticated write access and current policy permit it. Otherwise preserve a structured pending return and report it. Never sync secrets, device credentials, transient logs, or unnecessary private payloads.

## Privacy and readiness

GitHub repository metadata reports this repository public (verified 2026-10-22). Private keys, credentials, runtime state and personal payloads remain excluded from publication and SKB return. This pointer does not certify central registry membership or a successful App-backed pull; verify those through SKB's canonical registry and receipts instead of treating earlier onboarding notes as current state.

The local workflow and source boundaries are described in [Documentation, status, and SKB knowledge return](docs/KNOWLEDGE-SYNC.md). SKB is the authority for its protocol; this pointer does not copy or override that policy.

Central mechanical synchronization uses the separately authorized SKB Registry Reader App with read-only Contents access. Effective access and the latest receipt must be verified in SKB. This project receives no cross-repository write credential.
