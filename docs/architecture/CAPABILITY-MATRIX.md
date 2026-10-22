# Management client coverage

This is a source/evidence overview, not proof that every action is live-qualified. The full per-operation/install audit remains open in [the worklist](../audit/REPOSITORY-AUDIT.md). The older detailed inventory is preserved as [dated history](history/2026-10-22-capability-matrix.md).

| Area | Implemented reach | Remaining work |
|---|---|---|
| Shared service | Typed operations, catalog, capability/session checks, plans and recovery primitives | Registry entries alone do not prove client controls, deployment or live qualification |
| CLI | Broadest grouped management commands and specialized modules; SSH authorized-key inventory and preview-confirmed client-key creation | Complete command/operation inventory and supported setup replay |
| TUI | Catalog/search/status, guided session picker, shared-service SSH enrollment/revocation/key rollback/client-key creation/autostart/next-start Wake Lock controls, Cron scheduler controls, and real terminal lifecycle on a separate guest | Full operation/action parity remains; CLI/TUI/Web/GTK same-session continuity has passed |
| Web | Authenticated local console; scoped desktop/graphics/monitoring/8023 lifecycle, key inventory/enrollment/revocation and exact rollback, Native recovery-key creation, SSH autostart and next-start Wake Lock preferences, apps/shortcuts/Cron actions, logs/history, and separate-guest terminal lifecycle; visible Firefox acceptance covers catalog/search/status controls/terminal rendering and 390/752/1440 layouts | Full mutation/client parity, broader configuration/scheduler/recovery writes, and action-by-action live qualification |
| GTK | Native GTK4/VTE resource console, typed bridge, app entry, shared-service SSH key inventory/enrollment/revocation/rollback and Native recovery-key creation dialogs; per-service SSH policy controls | Replay-guest terminal lifecycle and retire/restore passed; source/bridge/binary identity matches. Key-dialog and recovery-key visual review, action parity and full small-screen interaction review remain open |
| Navigation/actions | Shared category order; numbered lists; Web details scroll independently from actions; real mobile quick controls | Further GTK/TUI interaction refinement |
| Managed SSH 8023 | Native diagnostics, fingerprints, preview-confirmed lifecycle/deployment, public-key enrollment/revocation, recovery-key creation, durable rollback, autostart and next-start Wake Lock policy have shared four-client paths; disposable Native key authentication passed | Password login remains disabled; bounded recovery decision and cold-boot delivery verification remain open |
| Development SSH 8022 | Externally managed inspection | No product lifecycle/auth mutation; preserve this channel |
| Boot/Wake Lock | Native helpers/profiles, owner-scoped leases, diagnostics; SSH autostart and managed-SSH next-start Wake Lock preferences have four-client preview/apply controls | Android-global lock state remains unknown; current service lease is not changed by preference edits; next-boot observation of current recovery modules remains open |
| Cron | Persistent definitions, previewed mutations/history across clients; CLI/TUI scheduler controls | Web/GTK scheduler lifecycle, retry/cancellation/non-skip delivery and production recovery |
| GUI monitoring | Shared policy status/configuration; Native preview-first service install; idle live worker and private interval replay verified | Web/TUI/GTK registration controls; Android Activity/focus and later cold boot qualification |
| Timezone | CLI/TUI/GTK scheduling preference; Web status/zone reads | No Android system-time mutation; no Web timezone write scope |
| Logs/recovery | Fixed bounded logs/history in clients; broader CLI recovery | Full recovery-write parity; no arbitrary paths/Android-wide logs |
| Optional PRoot | Receipt-owned Debian Trixie replay setup, exact retirement/restore, direct Zink/Turnip, and receipt-bound VirGL GLX draw verified on Native :1 through installed tx; replay graphics env stays process-scoped | VirGL server stop remains fail-closed because Android cannot map socket clients; nested Xephyr :2 GLX remains failed; Web mutation/client parity, wider Native-independence injection, broader guest configuration replay, and full audit remain open |
| Software/AI | Package preview/apply foundation, catalog proposals and graphics diagnostics | Full software lifecycle, Wine qualification, inference/model/NPU integration |

Availability badges describe feature coverage; live service state is checked separately. Planned functions must not be simulated by active buttons.

See [current Native audit evidence](../evidence/2026-10-22-native-ui-and-audit-remediation.md), [the Firefox checker](../../tools/check_web_ui.py), and [qualification guidance](../testing/README.md).
