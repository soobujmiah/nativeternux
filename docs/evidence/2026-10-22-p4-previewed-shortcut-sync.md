# P4 previewed PRoot application shortcut synchronization

Date: 2026-10-22
Phase: `P4`
Environment: Native Termux, aarch64, through the owner-provisioned SSH 8022 development shell.
Scope: source/service/UI and read-only live preview. No shortcut write was required by the live preview.

## Change

The former proot.shortcuts.sync route performed a bulk menu/launcher write and removed stale generated entries without an explicit client preview. It is now split into proot.shortcuts.sync.preview and proot.shortcuts.sync.apply. Preview runs the existing synchronization logic against a private temporary copy of only the Ternuxx-owned launcher/menu targets, returning exact relative paths and before/after hashes. Apply recomputes the preview and requires its exact plan ID plus confirmation. Unowned launcher conflicts are reported and preserved. If the writer raises after partial changes, captured pre-state is restored for all touched paths.

CLI tx mng papps sync displays the change list and asks before applying; non-interactive use requires --yes. Authenticated Web has the same preview/confirm/apply path with the existing scoped capability, CSRF and idempotency handling. The desktop supervisor obtains a fresh plan and applies that plan during Native desktop startup, preserving the existing automatic menu refresh behavior. It logs a bounded skip message on failure.

## Evidence

- python3 -m py_compile on changed Python service/runtime/catalog modules: passed.
- python3 -m unittest tests.test_proot_shortcuts tests.test_management_authorization tests.test_management_http_runtime -q: 45 passed, 1 skipped in the previous focused run.\n- bash scripts/repo_test.sh: exit 0; 860 tests ran, 859 passed and 1 skipped in 142.436 seconds. The runner emitted the known GUI-monitor Native-only diagnostic JSON after the successful suite; the process exit remained zero.
- bash -n lib/management.sh lib/desktop-supervisor.sh: passed.
- Native live read-only proot.shortcuts.sync.preview: 35 desktop entries discovered, zero changes, zero conflicts, plan 189028598bf1757155f9d225; no guest login or file mutation.
- Exact installed command tx mng papps sync: reported 35 discovered and already synchronized; no apply occurred.\n- Visible Firefox 153.5.0 review on the existing Native X11 display passed at a 742x881 content viewport; the sync action was visible in the action pane and did not execute. Screenshot/report: docs/evidence/web-shortcut-sync-visual/.
- git diff --check: passed at this checkpoint.

## Limits

The failure path restores changed bytes synchronously, but the plan/snapshot is not yet a durable post-crash rollback journal or user-triggered undo. There is no multi-process lock spanning preview and write. GTK and TUI do not yet expose the bulk sync action. The complete shortcut wizard, editable per-app configuration, enable/disable, duplicate handling, restore history, and all-client action parity remain open. This evidence is not a full shortcut-manager acceptance.
