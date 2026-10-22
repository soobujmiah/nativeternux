# P4 next gate reconciliation — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Review

The P4 phase state previously named browser-rendered Web review of the isolated replay guest as the next action. That review is already complete: visible Firefox acceptance covers authenticated catalog/search, status controls, terminal rendering, action layout and responsive 390/752/1440 viewports. GTK replay-guest retirement/restore confirmation and same-session terminal interactions are also recorded as passed. The phase remains open; these results do not qualify remaining P4 gates.

## Remaining gates

- **Complete:** a clean preview-bound Debian Trixie replay recorded all requested package versions; apt-get check, dpkg --audit, locale/user checks, and protected-default-rootfs identity passed.
- **Complete:** the receipt-owned replay guest passed exact private retire/restore with the same container/rootfs identity and no deletion.
- **Complete for direct Zink:** installed tx verified Native :1 X11/audio and Zink/Turnip GLX drawing on the fresh replay alias.
- **Complete: receipt-bound VirGL replay draw:** the installed tx route and bounded verifier rendered VirGL on Native :1; a final Zink recheck still passed on the same replay rootfs. **Open: exact VirGL stop/client visibility:** Android lsof/fuser cannot prove socket-client ownership, so the lifecycle correctly refuses stop and the Ternuxx-owned service remains running. Nested Xephyr :2 graphics remains unqualified/failed. See [VirGL route and cleanup evidence](2026-10-22-p4-virgl-route-recheck.md).
- **Open:** Web mutation/client parity, wider Native-core failure-injection for absent/broken PRoot, and requirement-by-requirement source/installed-runtime/full-repository audit.

## Evidence

- [Visible Web acceptance](2026-10-22-web-ui-visible-acceptance.json) and screenshot.
- [GTK replay-guest apply](2026-10-22-gtk-replay-guest-apply.md).
- [Cross-client terminal handoff](2026-10-22-cross-client-terminal-handoff.md).
- [P4 phase audit](2026-10-22-p0-p4-phase-audit.md).
- [Clean replay setup and graphics evidence](2026-10-22-p4-replay-download-timeout.md).
- [VirGL route recheck](2026-10-22-p4-virgl-route-recheck.md).
- [Current roadmap and P4 exit gates](../ROADMAP.md).
