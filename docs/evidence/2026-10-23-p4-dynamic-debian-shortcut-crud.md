# P4 dynamic Debian shortcut CRUD — 2026-10-23

Phase: `P4`

## Change

The shared PRoot shortcut preview/apply operation now accepts exactly one fixed app_id or discovered desktop_id. Dynamic entries are generated only from current runnable Debian desktop inventory. Add/remove uses the same inter-process lock as bulk sync and rollback. Modified, unowned, symlink, or stale targets fail closed and remain untouched. An unchanged Ternuxx-owned launcher can be removed after its guest app becomes unavailable, while adding that unavailable app is refused.

CLI, TUI, Web, GTK and the local GTK bridge pass the stable desktop_id through the shared management operation. GUIs show localized/friendly app names; confirmation does not expose internal desktop IDs. Menu-wide sync/rollback remains separate.

## Evidence

- Dynamic shortcut add and remove completed against an isolated test rootfs and temporary Native home; exact owned generated launcher was created, recognized, then removed.
- A modified launcher at the exact generated target was preserved; removal preview refused it.
- Native read-only preview for Firefox ESR returned its friendly name, exact target, exact plan ID and read_only=true; no live shortcut was applied.
- GTK client and bridge installed on Native. C source, Python bridge and installed binary hashes match the installer identity record.
- Focused tests across shortcut service, management service, Web, GTK bridge, and TUI: 152 passed, 1 skipped.
- Full repository suite after dynamic CRUD, unavailable-app cleanup, and schema changes: 884 passed, 1 skipped in 128.703 seconds.
- Native GTK 4.24.1/VTE 0.84.1 build and self-check passed; installer identity matches source C, bridge and installed binary.
- Native management CLI and GTK bridge both returned exact read-only preview for live Firefox ESR at .local/share/applications/ternuxx-proot-app-firefox-esr.desktop.
- Repository knowledge verification: zero findings.

## Limits

No GTK UI click was injected. Actual launch or shortcut changes were not performed in the owner's existing Debian guest. Individual per-app mutations do not have their own rollback receipt; exact preview/apply and bulk sync rollback remain available. Broken-rootfs recovery, cold boot, rootfs migration and P4 exit remain open.
