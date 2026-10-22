# Terminal close attachment authorization — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Implementation

I found that terminal close preview/apply checked guest ownership but skipped attachment authorization. A request carrying a stale generation, foreign attachment token or different authenticated principal could reach the close callback in isolated dispatcher tests. All six negative cases failed before the fix. The dispatcher now requires the current exact writer lease before either callback. Rejected requests preserve the real writer; accepted close still requires current guest ownership and the exact fresh stop plan.

## Evidence

- Focused broker tests: 11/11 passed after the change, including all six negative subcases and the existing valid close path.
- Full Native source suite: 733/733 passed in 102.713 seconds. [Source-bound record](2026-10-22-terminal-close-regression.json).
- Before live reload, the installed run definition matched source, broker status was `not_connected`, and every managed session record was terminal (`stopped` or `failed`). Only the exact `ternuxx-terminal-broker` Runit service was restarted. Its generation changed, status returned successfully and remained `not_connected`. No SSH, desktop or working PRoot lifecycle command ran.
- No guest terminal lifecycle is inferred from an idle service reload.

## Related audit finding

Reading the installed PRoot-Distro 5.9.0 dependency confirmed that `commands/login/__init__.py` invokes `inject_termux_profile` for normal containers regardless of isolated/minimal mode; only the PATH append is mode-dependent. The [GPU procedure](../PROOT-GPU.md) now discloses that a fixed read-only probe payload does not make its launcher filesystem-read-only. A29 tracks result metadata and management preview/authorization correction; no working guest was entered to establish this source fact.

The separate guest was still unpacking packages at this checkpoint. Its final preservation and setup outcome, four-client terminal acceptance and the [full audit](../audit/REPOSITORY-AUDIT.md) remain open.
