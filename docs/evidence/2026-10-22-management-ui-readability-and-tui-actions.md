# Management UI readability and TUI action parity — 2026-10-22

**Source reviewed:** `05e70eb64a50eae287d76da8ec4698447ba24d4d` (`origin/main`)
**Execution environment:** PRoot Debian source checkout; Native Termux SSH 8022 login rejected with `Permission denied (publickey,password,keyboard-interactive)`. Changes below are source-only and were not deployed to the phone.

## Changes

- Added shared human-facing field/state labels and a report formatter for TUI and GTK inspection. Credential-like fields are omitted.
- Web operation responses now include a readable summary while preserving the technical JSON response in its existing collapsed section.
- Sorted categories and resources and added visible numbering in GTK, Web, and TUI.
- Added alphabetical/numbered category/resource lists, direct 1–9/0 resource selection, and page navigation in TUI. Added guided TUI startup-profile status, preview, enable, and disable flows. Enable requires a ready preview and explicit confirmation. Added Cron scheduler status/start/stop prompts with bounded 1–60 second polling and explicit confirmation.
- Added TUI Wake Lock status inspection. Direct acquire/release is deliberately not exposed because the existing caller-owned lease does not have a reliable process-exit cleanup contract for interactive clients.
- Added a 8023 login-key explanation and recovery requirements. Key enrollment/removal, password changes, and an SSH-specific boot toggle remain unsupported. Current boot entry starts the Runit supervisor, which starts enabled services including managed SSH.

## Verification

- Focused TUI, GTK bridge, HTTP adapter/runtime, and catalog tests: 90 passed.
- Python compilation for the changed Python modules: passed.
- Web UI JavaScript syntax check with Node: passed.
- `git diff --check`: passed.
- `python3 -m tools.repo_knowledge verify`: 0 findings before this evidence note was added.
- Full `bash scripts/repo_test.sh`: 690 tests ran; 9 failed/errored in Native desktop/VirGL lifecycle fixtures in this PRoot environment. These failures require rerun on Native Termux; this run is not a passing full-suite result.
- GTK/VTE development packages are unavailable in this PRoot environment, so the GTK C source was not compiled.
- 8023 password-only authentication probe for `u0_a490` was rejected with `Permission denied (publickey)`. No credential, service, boot, Wake Lock, or PRoot state was changed.

## Continuation — app launcher and TUI navigation

- Added a native desktop application entry to `scripts/install-management-center.sh`, so the GTK Management Center appears in the XFCE application menu after installation. The installer records its SHA-256 in the existing identity file and refuses to overwrite a modified/unowned desktop entry. This is a source change only; it has not been installed on-device.
- TUI action summaries now occupy one clipped row, and the feedback area has a fixed two-row slot so changing action details does not move the resource list anchor. Added coverage for this layout invariant.
- Added arrow-key/number/Enter menus for GTK desktop lifecycle, managed SSH 8023, graphics checks/backend selection, PRoot workload actions, and Cron actions. Destructive or persistent changes retain explicit confirmation and exact preview flow.
- Rechecked Native 8022 in batch mode; it still rejects authentication with `Permission denied (publickey,password,keyboard-interactive)`. User-provided `66234446` was not accepted by 8023, which advertises public-key auth only. Credential recovery/enrollment cannot proceed without a valid provisioned login key or a local Native Termux console; no authentication settings were changed.
- Focused terminal UI and GTK bridge tests after these changes: 61 passed. Installer `bash -n` and `git diff --check` passed.

## Live Native Termux implementation — 2026-10-22

- Native 8022 became reachable through the configured `termux` SSH alias. The Native checkout was one repository metadata commit behind; its four pre-existing modified files were preserved in a named stash, the checkout was fast-forwarded to `05e70eb`, and the stash was replayed before reconciling source. No dirty change was discarded.
- Added a mandatory live/repository parity rule to this repository's `AI_ASSISTANT.md`: implement and verify in Native Termux and update the canonical repository in the same task; source-only or device-only work is not a completed handoff.
- Synchronized the implementation and documentation through Native Termux. Full Native repository suite: **692 tests passed**. Focused TUI/GTK bridge suite after the follow-up human-readable error improvement: **62 passed**. GTK compilation (`clang -fsyntax-only`) and installer shell syntax passed.
- Built and installed the GTK app through `scripts/install-management-center.sh`. The verified installed GTK binary SHA-256 is `c235fd1dc863e1f80233c93c58d3f435eea7af07650819273e6010b0f3ae7b75`. Installed source SHA-256s match the Native C and Python bridge source hashes recorded in `management-center.identity`.
- Installed `$PREFIX/share/applications/ternuxx-management-center.desktop`; `desktop-file-validate` passes after choosing one primary `Settings` category. The Ternuxx Management Center window was launched on the already-running Native X11 `:1` session and its window title/geometry were observed. A scoped screenshot review confirmed numbered navigation, human-readable status, and visible action controls. That review exposed one raw unavailable-status error; it was converted to readable text, focused tests rerun, and a second screenshot confirmed the raw code was gone. Temporary screenshots were removed from the device.
- No PRoot filesystem, process lifecycle, SSH authentication/service, boot, or Wake Lock state was changed.

## Follow-up — concise GTK capability details

- Removed the duplicated raw supported-operation list, redundant live-state sentence, and repeated capability caveat from the GTK detail pane. It now shows capability level, availability, short description, and only the actions exposed by the GTK app; generic entries say “Status and details only.”
- Shortened each action summary and confirmed the updated GTK binary rebuilt/installed through the ownership-checked installer. Native X11 `:1` relaunched it successfully. A second scoped screenshot confirmed the unsupported-status case now uses a human-readable message and does not expose an operation code.
- GTK syntax compilation and installed artifact identity verification passed. The app remains open on the existing X11 session.
- Applied the same cleanup to Web: removed expanded supported/planned operation inventories, left actual context-valid controls as buttons, and collapsed SSH recovery help. Raw diagnostics remain under the optional collapsed “Technical API response.”
- Web-focused static/runtime test passed, inline JavaScript passed `node --check`, and the active loopback Web server returned HTTP 200 with the updated action container and without supported/planned capability inventories.

## Remaining qualification

Remaining product gaps include SSH key recovery/enrollment, SSH-specific startup controls, client-parity work for controls not implemented in a given frontend, and workload-bound Wake Lock controls. The GTK app is now live-installed and visually reviewed; the focused interface changes and the rest of the current repository suite pass in Native Termux. Do not generalize this completed app deployment into proof that every roadmap feature or frontend action is implemented.

## Follow-up — prevent catalog operation inventory duplication

- Traced the remaining Web duplicate to catalog-load output: the UI displayed the full catalog in the human-readable result pane and again in the collapsed technical API response. This exposed supported_operations and planned_operations even though resource-specific action buttons already represented what the UI could do.
- Catalog load now renders only a concise resource/category count in the result area and a short confirmation in the technical panel. The original catalog remains in memory for action gating and resource selection; API behavior and available controls are unchanged.
- The Web server is on-demand and was not running during this edit (127.0.0.1:8765 refused the connection). The Native checkout is the server's source path, so the updated page will be served when tx web starts next.
