# P4 next gate reconciliation — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Review

The P4 phase state previously named browser-rendered Web review of the isolated replay guest as the next action. That review is already complete: visible Firefox acceptance covers authenticated catalog/search, status controls, terminal rendering, action layout and responsive 390/752/1440 viewports. GTK replay-guest retirement/restore confirmation and same-session terminal interactions are also recorded as passed. The phase remains open; these results do not qualify remaining P4 gates.

## Remaining gates

- Complete the pinned isolated Debian replay and verify the requested package/configuration receipt and preservation of the protected default Debian rootfs.
- Verify exact replay-target retire/restore after the fresh setup finishes.
- Close remaining provider/configuration and distinct route acceptance, including honest nested graphics results.
- Complete Web mutation/client parity and Native-core failure-injection coverage for absent/broken PRoot.
- Continue the requirement-by-requirement source, installed-runtime, documentation and dirty/untracked review.

## Evidence

- [Visible Web acceptance](2026-10-22-web-ui-visible-acceptance.json) and screenshot.
- [GTK replay-guest apply](2026-10-22-gtk-replay-guest-apply.md).
- [Cross-client terminal handoff](2026-10-22-cross-client-terminal-handoff.md).
- [P4 phase audit](2026-10-22-p0-p4-phase-audit.md).
- [Current roadmap and P4 exit gates](../ROADMAP.md).
