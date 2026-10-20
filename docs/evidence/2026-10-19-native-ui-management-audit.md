# Native management UI audit — 2026-10-19

## Verified current state

- Target environment: Native Termux repo `$HOME/ternuxx`; current branch `main`; owner worktree remains dirty and preserved.
- `lib/management_web_ui.html`: one 147-line page. Its controls are diagnostic/status reads plus the shared GUI monitoring policy editor. HTTP Web capability is currently limited to diagnostic reads and `desktop.monitor.configure`.
- `lib/terminal_ui.py`: curses interface with five fixed summary views. Generic `o` prompts for raw operation ID and JSON arguments and then displays the complete nested response; this is powerful for developers but not a guided, category-first product UI.
- `lib/management_catalog.py`: current domain catalog reports provider maturity and operations; coverage includes desktop, SSH, PRoot, autoboot, backup/recovery, diagnostics, add-ons, and API backends. Several deployment/resource-management operations remain planned or absent.
- `lib/management_authorization.py` and `lib/management_http_runtime.py` use explicit capabilities/default deny; Web mutation access is intentionally narrow. Expanding controls requires operation and transport security work, not merely adding buttons.
- No standalone Native Ternuxx graphical management app entry point was found. The existing XFCE desktop is a workload/session manager target, not a management application.
- `.superdesign/init/` now contains six non-empty repository discovery files for the existing single-page Web UI and TUI. No `.superdesign/resume.json`, project, or design draft has been created for this target.

## Accepted UI scope

All four clients—CLI, TUI, Web UI, and a separate Native graphical management app—should use the same categorized resource vocabulary and authoritative management core. They should support the operations available to each client: service/server add/remove, deploy, config, foreground/background lifecycle where supported, boot enable/disable, health, logs, dependency details, and safe recovery. The default presentation should be concise and task-oriented, with technical evidence and JSON available on demand. Destructive actions require an explicit review/confirmation path. SSH 8022 remains manually managed and excluded; managed SSH remains 8023.

## Current blocker before visual drafting

The Superdesign skill requires external canvas design before local UI implementation, plus owner review of the resulting design before code changes. It also requires showing the exact source context-file list and size before any repository code is uploaded. The initial Web/TUI/catalog/security/management-API bundle was 551 lines and 31,248 bytes at audit time. The currently proposed design bundle below is measured from current source and has not been uploaded. No source files were uploaded, no external draft was generated, and no UI source was changed during this audit.


## Catalog implementation follow-up

- Native repo: `$HOME/ternuxx`, Termux prefix `/data/data/com.termux/files/usr`; branch `main`, dirty worktree preserved.
- Added typed categorized catalog response schema v2 and category/query/status filtering through `management.catalog` and `tx management catalog list`.
- Native CLI smoke: `./tx management catalog list --category networking --query 8022`; exit 0, response `ok=true`, schema version 2, only `network.ssh.manual-8022` returned.
- Native CLI smoke: `./tx management catalog list --category services --status implemented`; exit 0; two resources returned.
- `python3 -m py_compile lib/management_catalog.py lib/management_service.py`: exit 0.
- Focused catalog/API and GUI monitoring schema regression tests: 43/43 passed in 0.376 seconds (including management service tests).
- Resource descriptors remain discovery metadata; catalog does not assert live health. Cold boot, audio ownership, and PRoot process ownership remain unverified.


Phase: `P3`
Gate: BLOCKED

## Acceptance criteria

- A truthful, typed resource inventory is available through the shared management core, API, and CLI.
- Catalog filtering does not invoke resource lifecycle or Android Activity/focus probes.
- 8022 is classified as external/read-only; 8023 is classified as the managed service.

## Evidence

- Native focused catalog/API/monitoring tests: 43/43 passed in 0.376 seconds; full suite: 392/392 passed in 80.202 seconds (exit 0).
- Cold boot, audio ownership, PRoot lifecycle ownership, and full UI parity remain unverified or incomplete.


## Current design-context bundle (not uploaded)

- `lib/management_web_ui.html` (full): 147 lines, 6,512 bytes
- `lib/terminal_ui.py` (full): 246 lines, 9,504 bytes
- `lib/management_catalog.py` (full): 158 lines, 27,080 bytes
- `lib/management_authorization.py` (full): 84 lines, 3,451 bytes
- `lib/management_http_runtime.py` lines 20–44: 25 lines, 1,083 bytes
- `docs/architecture/MANAGEMENT-API.md` lines 1–17: 17 lines, 6,949 bytes
- Total: 677 lines, 54,579 bytes.

Owner approval is required before this source context is sent to the external Superdesign canvas. The intended design targets are the current Web UI and a separate Native graphical management application.

## Superdesign source upload and initial canvas draft

- Owner approved the exact source context list and total (677 lines / 54,579 bytes) before upload.
- The six approved source files/excerpts were staged from Native Termux to a private temporary directory. Their line/byte counts and SHA-256 hashes matched source before canvas use; no additional repository files were uploaded.
- Created a new project, `Ternuxx Management Center`, extending the existing Beam design system. The unrelated `Ternux Capability Website Redesign` project was inspected read-only and left unchanged.
- Generated Web Console draft: https://superdesign.dev/teams/76b0128f-275a-4704-b598-2ee6a691b91f/projects/bffeaec6-1dc0-46b7-ab17-15bd942d8fad?node=draft-variant-5ca7aabc-6cf0-425e-97a1-5e27c8e138af
- Draft ID: `5ca7aabc-6cf0-425e-97a1-5e27c8e138af`; preview: https://p.superdesign.dev/draft/5ca7aabc-6cf0-425e-97a1-5e27c8e138af
- Superdesign reported 21.5 credits consumed for this generation. No additional generation was requested.
- Read-only source inspection found the draft visually organizes category navigation and resource cards, but it does not meet acceptance yet: 8022/8023 are omitted, action buttons expose raw operation IDs, static green availability may imply live health, the requested warm neutral palette was not followed, and there is no separate Native management application draft. Do not implement from this draft until owner review and a corrected design direction.
- Native repository source/UI remains unchanged by canvas generation. No Activity/focus poll, service action, reboot, or PRoot operation was performed.

### Refined design-only drafts

- Added a task-first light Web Console design (version 2) and a separate Native Desktop Management App design to the new `Ternuxx Management Center` project.
- Web Console: https://p.superdesign.dev/draft/a91e57db-d1a6-4812-a792-5d7a0c831076
- Native Desktop app: https://p.superdesign.dev/draft/884f7b60-5665-4c3f-b5b7-ce7e375c8c09
- These HTML artifacts were authored manually and imported through Superdesign's documented no-AI/no-credit import path. They are visual prototypes, not connected to the management API and not installed in Native Termux.
- Both drafts visibly distinguish SSH 8022 (external/read-only) from 8023 (managed), keep GUI Activity monitoring disabled, label audio/PRoot/boot uncertainties, and show future deployment/AI controls as planned. The Web draft labels its data and controls as illustrative.
- No further AI generation or credit-consuming iteration was performed after the initial 21.5-credit draft. UI implementation remains gated on owner review of these designs.
- Added a keyboard-first TUI design prototype (version 2): https://p.superdesign.dev/draft/a11c47c7-b98b-4f0a-84e6-2c5e257e96a2
- Final review set: Web Console v2, Native Desktop app v1, and TUI v2. The first AI-generated console remains an exploratory draft in the project; use the refined links above for review.
