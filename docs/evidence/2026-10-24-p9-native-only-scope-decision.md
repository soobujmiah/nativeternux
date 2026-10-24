# P9 optional isolated workload profile — 2026-10-24

Phase: `P9`

Gate: SKIP

## Acceptance criteria

- P9 is optional and requires a selected, documented isolation need.
- Native-only scope is active; no isolation gap is selected.

## Evidence

The owner selected Ternuxx as Native Termux-only and authorized complete PRoot retirement, including live guest removal. The active product decision is recorded in [ADR-0017](../architecture/decisions/ADR-0017-native-only-product-and-proot-retirement.md), and the removal audit records the implementation and live post-removal checks in [the Native-only PRoot removal audit](2026-10-24-native-only-proot-removal-audit.md).

No isolated guest workload or Native workload gap is selected for this optional phase. Reintroducing PRoot or another isolated provider would contradict the current owner-selected product scope. P9 is therefore skipped; any future isolation need requires a new explicit product decision and its own security/runtime qualification.
