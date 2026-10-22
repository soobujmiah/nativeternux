# Management client coverage

This is a source/evidence overview, not proof that every action is live-qualified. The full per-operation/install audit remains open in [the worklist](../audit/REPOSITORY-AUDIT.md). The older detailed inventory is preserved as [dated history](history/2026-10-22-capability-matrix.md).

| Area | Implemented reach | Remaining work |
|---|---|---|
| Shared service | Typed operations, catalog, capability/session checks, plans and recovery primitives | Registry entries alone do not prove client controls, deployment or live qualification |
| CLI | Broadest grouped management commands and specialized modules | Complete command/operation inventory and supported setup replay |
| TUI | Catalog/search/status, guided supported resource workflows and terminal client | Full action parity/current managed guest attach |
| Web | Authenticated local console; scoped desktop/graphics/monitoring/8023/apps/shortcuts/Cron actions; history/logs and terminal dialog | Credentials, per-service boot/Wake Lock policy, broader configuration/scheduler/recovery writes |
| GTK | Native GTK4/VTE resource console, typed bridge, app entry and supported dialogs | Source/bridge/binary identity verified after rebuild; remaining workflows/terminal attach need qualification |
| Navigation/actions | Shared category order; numbered lists; Web details scroll independently from actions; real mobile quick controls | Further GTK/TUI interaction refinement |
| Managed SSH 8023 | Native service/config diagnostics and preview-confirmed lifecycle/deployment paths | Key generation/enrollment/removal, password/recovery, and per-SSH boot policy across clients |
| Development SSH 8022 | Externally managed inspection | No product lifecycle/auth mutation; preserve this channel |
| Boot/Wake Lock | Native helpers/profiles, owner-scoped leases, diagnostics, selected CLI/TUI controls | Uniform service policies/client controls and next-boot observation of current recovery modules |
| Cron | Persistent definitions, previewed mutations/history across clients; CLI/TUI scheduler controls | Web/GTK scheduler lifecycle, retry/cancellation/non-skip delivery and production recovery |
| GUI monitoring | Shared policy status/configuration; Native preview-first service install; idle live worker and private interval replay verified | Web/TUI/GTK registration controls; Android Activity/focus and later cold boot qualification |
| Timezone | CLI/TUI/GTK scheduling preference; Web status/zone reads | No Android system-time mutation; no Web timezone write scope |
| Logs/recovery | Fixed bounded logs/history in clients; broader CLI recovery | Full recovery-write parity; no arbitrary paths/Android-wide logs |
| Optional PRoot | Inventory/probes, named apps/shortcuts, fixed broker and four transport paths | Disposable replay, managed attach lifecycle, concurrency/nested presentation/preservation acceptance |
| Software/AI | Package preview/apply foundation, catalog proposals and graphics diagnostics | Full software lifecycle, Wine qualification, inference/model/NPU integration |

Availability badges describe feature coverage; live service state is checked separately. Planned functions must not be simulated by active buttons.

See [current Native audit evidence](../evidence/2026-10-22-native-ui-and-audit-remediation.md), [the Firefox checker](../../tools/check_web_ui.py), and [qualification guidance](../testing/README.md).
