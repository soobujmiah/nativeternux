# Native GTK management center visual review — 2026-10-22

Phase: `P4` — visual inspection evidence; no phase gate completed.

## Capture scope

- Reviewed the running `Ternuxx Management Center` window on Native X11 display `:1` using a window-only capture at 720×980 pixels.
- The visible Ternuxx window process was PID 17842 at capture time. Its title and dimensions were read through X11 window metadata before capture.
- Selected the `Services & background` category, inspected the `Termux Wake Lock` resource, then selected `Ternuxx SSH service · 8023`. No service, key, boot, or Wake Lock action was activated.
- Live repo was `main` at `66bf730`; GTK C source, management bridge, installed binary, launcher, and desktop-entry hashes matched the installed `management-center.identity` on the prior final parity check. The screenshot confirms the running app rendered its management UI, but the capture alone does not prove every action callback works.

## Findings

1. **Partial — category navigation wraps heavily at the tested width.** The 155-pixel sidebar makes long category names occupy two or three lines. The numbered list remains readable, but it consumes vertical space and makes category scanning slower.
2. **Unverified — less common SSH actions are not discoverable in the captured first view.** The selected SSH resource showed Start and Stop buttons. The source also defines Restart, key inventory/enroll/revoke, recovery-key generation, and autostart controls, but I did not scroll or invoke those controls during this read-only visual pass.
3. **P4 gap — Wake Lock is inspection-only in GTK.** The resource shows current lease details but no visible per-service policy control. Current Android lock-holder state remains explicitly unknown.
4. **Partial — diagnostic detail is readable but dense.** SSH status lists both the owner-managed 8022 endpoint and managed 8023 configuration. The labels are humanized, though the long result extends beyond the captured first viewport.

## Verification boundary

- PASS: a live Native GTK window was identified and visually inspected; the two target resource screens rendered.
- PASS: the app remained running and no management mutation was triggered.
- UNVERIFIED: scrolling, dialogs, confirmation/apply callbacks, keyboard/touch behavior, and smaller viewport behavior were not exercised.
- No screenshot or runtime state containing service details is committed. GUI selection is restored to the initial Graphics acceleration category after inspection.

## Follow-up

Improve narrow-screen category navigation and action discoverability; add a shared preview-first per-service Wake Lock policy where supported; then visually review the installed dialogs and their result states.
