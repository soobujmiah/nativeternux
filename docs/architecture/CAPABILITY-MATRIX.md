# Management client coverage

Current supported scope is Native Termux-only. PRoot and interactive guest-terminal actions were retired on 2026-10-24; their old coverage reports are retained in [dated history](history/2026-10-22-capability-matrix.md). This table summarizes current source reach, not live acceptance for every operation.

| Area | Current reach | Remaining work |
|---|---|---|
| Shared service | Typed Native operations, capability/session checks, catalog, exact plans and recovery primitives; shared `inference.cpu.*` status/model/run operations | Audit every Native operation and complete live qualification |
| CLI | Native desktop, package, SSH, recovery, graphics, Cron, guided setup, and `tx ai` CPU status/model preview/install/remove/run | Complete command-level acceptance and clean-device replay |
| TUI | Native catalog/search/status and guided management, including CPU model setup/removal, bounded local inference, Cron job inspection, next-run previews, and execution details through the shared service | Complete broader action parity and accessibility review |
| Web | Authenticated loopback UI, Native desktop/graphics/monitor/SSH actions, logs, history, Cron create/update/remove, job inspection, next-run previews, execution details, and shared CPU model preview/apply/run | Complete broader mutation parity and live visible acceptance after migration |
| GTK | Native GTK4 management center and typed service bridge, including shared CPU model preview/apply/run, Cron job inspection, next-run previews, and execution details | Complete broader action parity and visual acceptance |
| SSH | Managed product SSH on 8023 and separate development SSH on 8022 | Cold-boot delivery verification and remaining bounded credential recovery decision |
| Boot/Wake Lock | Native helper/profile controls, scoped leases and diagnostics | Android-global lock state and next-boot verification remain unobserved |
| Backup/recovery | TUI/Web/GTK provide backup inventory/detail, preview-confirmed backup creation, restore apply, restore rollback apply, unresolved operation resolution, operation inspection, and continuity status through the shared service | Continuity checkpoint preparation/verification and reboot-test preparation/verification remain CLI-only; no reboot test is run by a client |
| Cron | Persistent definitions, all four schedule types, previewed mutations, job detail, next-run preview, execution history/detail, and confirmed scheduler start/stop controls across CLI/TUI/Web/GTK | Validation forms, production recovery, cancellation, retry, boot delivery, and broader live client acceptance remain limited |
| GUI monitoring | Shared policy status/configuration and Native service | Android Activity/focus and later cold-boot qualification |
| Timezone | CLI/TUI/GTK/Web scheduling preference through shared `timezone.set` | No Android system-time mutation |
| Graphics/audio | Native status/draw probes and backend preference controls; the system path is CPU `llvmpipe` on the observed device, while KGSL remains experimental and device-local | Workload-specific graphics/audio qualification; candidate distribution remains unsupported |
| Software/AI | Curated htop/tmux/tree lifecycle and HOME-scoped tree name listing across CLI/TUI/Web/GTK; pinned bounded CPU model lifecycle and inference across all four clients | File-content handoff and Android shared-storage access are unsupported; Wine, model-quality, sustained-resource, and offline qualification remain open; GPU/NPU inference is unavailable |

CLI, TUI, Web and GTK must keep unsupported actions visibly unavailable and route supported actions through the same shared service, authorization, and preview/confirmation contract. CPU inference now follows that shared path. Broader client parity and visual acceptance remain open. See [Native-only migration audit](../evidence/2026-10-24-native-only-proot-removal-audit.md) and [qualification guidance](../testing/README.md).
