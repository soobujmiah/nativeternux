# Native SSH contract fixtures

These fixtures are synthetic metadata for contract tests. Never put real host/user keys, passwords, Termux home paths, IP addresses, device identifiers, active `sshd` output, or the owner's manual configuration here.

The SSH lifecycle tests should construct fixture instances from these cases and validate them against:

- `schemas/native-ssh-config.schema.json`
- `schemas/native-ssh-service-state.schema.json`

Example synthetic records are `fresh-native-config.json` and `external-manual-state.json`. The latter records only that legacy password auth was observed; it contains no password and represents an unmanaged service that must not be taken over automatically.

| Fixture ID | Synthetic setup | Expected result |
|---|---|---|
| `fresh_unconfigured` | No service, no existing policy, Termux principal available | Plan may be created; state is not persisted until candidate and authentication checks pass. |
| `external_manual_key_auth` | External owner, public-key policy, opaque fingerprints only | Read-only status; no takeover; migration plan preserves host identity and active endpoint. |
| `external_manual_mixed_auth` | External owner, public-key/password/keyboard-interactive methods reported as legacy metadata only; no credential values | Preserve existing policy while staging; no auth downgrade until replacement validates and owner confirms. |
| `unknown_owner` | `sshd` listener/process does not match an ownership record | Fail closed; do not stop, adopt, or reconfigure. |
| `candidate_invalid` | Staged config syntax or selected key check fails | Keep old configuration/service unchanged and report stable error. |
| `listener_conflict` | Candidate endpoint already bound | No process is stopped; plan returns conflict. |
| `stale_pid` | PID reused or start-time/executable mismatch | Treat process as external/unknown; never signal it. |
| `host_key_changed` | Candidate host identity differs from recorded identity | Require explicit identity-change review; never silently rotate. |
| `boot_missing` | Termux:Boot unavailable | Manual native service remains usable; auto-start is reported unavailable. |
| `proot_unavailable` | PRoot stopped while native sshd is healthy | Native SSH remains healthy; only guest operation returns `provider_unavailable`. |
| `wakelock_owned_by_other_service` | Another service owns an active lease | SSH/PRoot stop cannot release that lease. |

Test suite cases and required assertions are defined in [SSH lifecycle contract](../../../docs/architecture/SSH-LIFECYCLE.md#8-test-contract-and-fixtures). These are fixture definitions, not test results or implementation evidence.
