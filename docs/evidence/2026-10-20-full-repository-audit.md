# Full repository and runtime audit — 2026-10-20

## A. Executive summary

The repository is a substantial, actively developed Native Termux management tool with shared CLI/API policy, newer TUI/Web/GTK clients, JSON-backed management state, desktop supervision, Cron and PRoot lifecycle modules. The working tree is heavily dirty from preceding implementation work, but its current changes are attributable only to “pre-existing at audit start”; Git cannot establish individual authorship/provenance for untracked files. No audit source changes, service operations, live PRoot operations, GUI operations, database mutations, boot changes, or tests were performed. Repository history/HEAD were not changed.

Implementation can continue in isolated fixtures after the highest-risk contract gaps below are corrected. Live workstation qualification is blocked: the prior interactive PRoot attempts failed closed; the installed `proot-distro` login path can write shared rootfs/container state; the active process context could not be attributed safely; GUI and true reattachment remain unqualified. AJ-managed peer-to-login and TXDB could not be found in this repository and require precise target identification.

Status definitions: PASS = directly verified; FAIL = established contradiction/defect; BLOCKED = safety/dependency prevented; UNVERIFIED = evidence insufficient.

## B. Baseline and integrity

- Actual checkout: Native Termux `$HOME/ternuxx`, resolved `/data/data/com.termux/files/home/ternuxx`; inspected over the existing SSH alias `termux` on manually managed port 8022. The local command shell itself is Debian PRoot (`/home/sbj`) and is not the target checkout.
- Branch `main`; HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`; origin is `https://github.com/soobujmiah/ternuxx.git`; `HEAD...origin/main` is `0 0`; only this worktree was listed.
- Audit-start Git state: 172 porcelain entries, no staged entries, no conflict/rename entries: 73 changed tracked paths (63 modified, 10 deleted) and 99 untracked status entries. `git ls-files` reports 419 tracked paths; `git ls-files --others --exclude-standard` reports 104 untracked files. `git diff --stat`: 73 paths, +3264/-714. The difference between status-directory entries and file inventory is directory collapsing (not missing files).
- Ignored inventory: 112 ignored Python bytecode files under `__pycache__`, covered by `.gitignore`; left untouched. Other `.gitignore` rules cover `.state`, `logs`, `*.log`, editor/OS debris. No repository-wide scan of ignored runtime directories beyond relevant repository operation was performed.
- No staged diff; no commit, push, reset, checkout, restore, stash, clean, branch change, or ref creation. The existing snapshot ref `snapshot/2026-10-20-pre-workstation-lifecycle` was observed at HEAD and left alone.
- The initial tracked/untracked path inventories were captured with `git diff --name-status` and `git ls-files --others --exclude-standard`. Modified/deleted tracked files and every untracked path are listed in the companion inventory appendix at the end of this report (generated from those commands at audit start). Existing dirty work was preserved exactly as found; there is no independent baseline snapshot to prove provenance or detect external changes that predated the audit.

## C. Dirty-worktree file audit

All 73 modified/deleted tracked paths and 104 untracked files existed at audit start and were left intact. The current tree contains changes spanning entrypoints, docs/state, management API/auth, desktop/session safety, PRoot, Cron/boot, tests, schemas, and CI. New/untracked code includes the shared management presentation/UI surfaces, GTK client/bridge, PRoot sessions, Cron runtime, GUI monitoring, Hermes read-only adapter, timezone support, boot manager, launch/TUI modules, and related tests/schemas. There are also 16 `.repo/events` records, six `.superdesign/init` scaffold files, and dated evidence documents. These have unknown individual provenance; none was classified disposable.

Relevant rename state: old tracked `bin/ternuxx`, root `ternuxx`, and `scripts/ternuxx-installed` are deleted; new `bin/tx`, root `tx`, and `scripts/tx-installed` are untracked. The installed `$PREFIX/bin/tx` exists and delegates to `$HOME/ternuxx/tx`; the current canonical entrypoint is `tx`. No `ternuxx` executable exists in the current checkout. This is a possible compatibility break for scripts/users invoking the old binary name; no evidence establishes whether such callers exist. `tx management` remains a deprecated alias for canonical `tx mng`.

Sensitive-data scan was limited to bounded credential/key/token patterns and did not print values. Matches were in source/test code paths that appear to handle or test credential labels; no obvious embedded private key, cloud key, or access token was identified. This is not a secret scanner guarantee. Repository events and evidence may include operational metadata; no values were copied into this report. No file contents were changed.

### Complete changed-path inventory

The authoritative full paths are the exact start-of-audit output of `git diff --name-status` and `git ls-files --others --exclude-standard`; grouped here by subsystem to keep this report readable:

- CLI/install/legacy: `.github/workflows/repo-contract.yml`, `bin/ternuxx` (deleted), `bin/tx`, `scripts/ternuxx-installed` (deleted), `scripts/tx-installed`, `tx`, `ternuxx` (deleted), `scripts/cli_entrypoint.py`, `lib/help.sh`, `lib/management.sh`, `lib/launch.sh`, `lib/tui.sh`.
- Docs, state, architecture, evidence, design scaffolding: `.repo/STATUS.md`, `.repo/project.yaml`, all `AI_ASSISTANT.md`, `CURRENT_STATE.md`, `README.md`, `docs/**`, `.repo/events/**`, `.superdesign/init/**`, `project/phase-state.json`, `tools/phase_docs.py` (path-level details remain in the captured Git inventory; no audit-created snapshot was made).
- Shared management/API/auth/catalog: `lib/management_authorization.py`, `management_catalog.py`, `management_http_adapter.py`, `management_http_runtime.py`, `management_http_server.py`, `management_service.py`, `management_sessions.py`, `management_presentation.py`, `management_web_ui.html`, `scripts/management_desktop_bridge.py`, `apps/management-center/management-center.c`, related management schemas and tests.
- PRoot/desktop/GUI: `lib/proot_sessions.py`, `desktop_session_state.py`, `gui_monitoring.py`, `desktop.sh`, `proot.sh`, `proot_shortcuts.py`, `proot-xfce-wrapper.sh`, `x11_display.py`; X11/GUI scripts, policy schemas, docs and tests.
- Cron/boot/timezone: `lib/cron_{daemon,execution,registry,scheduler}.py`, `termux_boot_cron.py`, `timezone_support.py`, `scripts/termux-boot/20-ternuxx-cron`, timezone/Cron schemas, docs and tests.
- Other existing service/continuity/recovery files: `lib/boot_profiles.py`, `continuity.py`, `continuity.sh`, `doctor.sh`, `doctor_report.py`, `phases.sh`, `reboot.sh`, `reboot_recovery.py`, `ssh_diagnostics.py`, native boot and runit scripts, shell shortcut scripts, plus their tests.

No reliable per-file authorship history exists for untracked paths. The `git status` inventory, rather than this condensed grouping, is the complete accounting source.

## D. Architecture and data flow

### Subsystem inventory and entrypoint/dependency map

- Native shell entry: root `tx` Android shell shim → `bin/tx` → `lib/*.sh`; `tx mng` routes into `lib/management.sh` → `lib/management_service.py`. `tx management` is a warning-emitting compatibility alias.
- Shared management: operation registry/validation in `management_service.py`; capability mapping and default-deny policy in `management_authorization.py`; catalog and presentation adapters supply CLI/TUI/Web/GTK choices. GTK C calls a typed Python bridge, which invokes shared service operations. TUI uses `terminal_ui.py`/`tui.sh`. Web uses a loopback HTTP runtime/server, request policy, adapter, request store and static HTML. Web mutation scope is intentionally narrower than the shared API and excludes PRoot/Cron/boot mutations. Web is not a generic shell interface.
- State: private JSON registries beneath `$TERNUXX_STATE_DIR` (default `$HOME/.local/share/ternuxx`), with subsystem locks and atomic writes where implemented. No TXDB/SQLite database or migration system was found. Existing Debian files are outside this management-state boundary and can be modified by `proot-distro` itself.
- Desktop lifecycle: `lib/desktop.sh` delegates session identity inspection/reconciliation to `desktop_session_state.py`; X11 display artifact checks live in `x11_display.py`; runit service wrappers supervise configured services. Discovery does not imply Ternuxx ownership.
- PRoot: CLI and shared management operations dispatch to `proot_sessions.py`; profile, registry, launcher/rootfs identity and process evidence are tracked. The module checks pid/start/group, argv, marker, rootfs and launcher identities, and uses preview/confirmation for mutations. Existing unmanaged processes are not adopted. Current login mode is foreground TTY; no verified terminal reattachment/persistent independent supervisor exists.
- Cron: CLI/shared service → Cron registry JSON → scheduler lease and execution ledger → fixed action allowlist through the management service. Termux:Boot helper is a separate optional integration script; actual user boot directory has no `20-ternuxx-cron` file. Cron production is not started by this audit.
- Legacy: `.bashrc` retains `db`, `droot`, `x`, `xgo`, `killx`; `db` invokes `proot-distro login debian --shared-tmp --user sbj`; `x.sh` delegates to `scripts/proot-x11-app.sh`. These files were inspected, not executed or modified.
- Test/CI: unittest suite under `tests/`, `scripts/repo_test.sh`, and `.github/workflows/repo-contract.yml`; docs/knowledge tooling has repository event side effects that were not invoked during this audit.

### State, permission and trust boundaries

Local CLI/GTK use same-user native processes and typed operation allowlists; local user access is the trust boundary. HTTP has loopback binding, exact host/origin checks, bounded request/body/rate policy, authentication, capability authorization, CSRF, idempotency, and persisted payload-free audit metadata. Capability checks are default-deny. Reads map to diagnostic capabilities; mutations map to subsystem capabilities and preview-confirm flows. Port 8765 listener ownership was not verified (native `/proc/net/tcp*` was unreadable and `ss` was absent), so no live service attribution is claimed.

PRoot process ownership depends on multiple corroborating identities, not PID/name alone. Stop revalidates and signals a specific verified process group; any ambiguity fails closed. Residual TOCTOU between final verification and `killpg` is inherent and should be reduced through pidfd/group design if platform support can be safely established; no live signal was sent. Recovery state files are sensitive private state and must not be treated as proof of process ownership without current kernel evidence.

## E. AJ-managed peer-to-login and TXDB

Repository-wide targeted searches for `AJ-managed`, `peer-to-login`, `TXDB`, and likely naming variants found no corresponding implementation, schema, command, or tests. Search results were limited to docs/evidence, ordinary SSH configured-peer text, the `tx db` command, and unrelated timezone database references. No `AJ` expansion or feature purpose is inferred.

- AJ peer-to-login: **BLOCKED / NOT FOUND IN THIS REPOSITORY**. Cannot establish initiator, owner, auth, resume, failure, or arbitrary command behavior without the actual named component or external repository. No live peer login attempted.
- TXDB: **BLOCKED / NOT FOUND IN THIS REPOSITORY**. `tx db` is a PRoot login command, not a database subsystem. Ternuxx management state is JSON-backed. No schema, migration, import/export, or database recovery implementation was found. No live database touched.

## F. Findings register

### F-01 — PRoot launcher mutates shared rootfs/container side state

- Severity: High; confidence: High; status: FAIL (contract contradiction), blocks live interactive qualification.
- Evidence: installed `proot-distro` package source at `$PREFIX/lib/python3.14/site-packages/proot_distro/commands/login/env.py` writes `/etc/profile.d/termux-profile.sh` for normal logins (`inject_termux_profile`, `_write_profile_snippet`); login path invokes it for normal distro. Debian login also runs fake sysdata setup and ensures `.l2s` state. Current hook exists at `/data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/rootfs/etc/profile.d/termux-profile.sh`, mode 0644, owner `u0_a490`, size 4762, mtime 2026-10-20 02:07:36 +0600, SHA-256 `207ae921b332045519681b0765669fb58e360d0beb5a6fd7b4fa2b260fdcd467`. Current source/docs (`tx db` help and PRoot profile contract) claim no rootfs change. No pre-test hash exists, so cause/time of current file’s creation cannot be attributed to any prior test.
- Impact: a normal login can write shared rootfs and container sidecar state. A “disposable” session is not filesystem-disposable merely because its process/registry is disposable.
- Recommendation: design a launch path that avoids proot-distro mutation, or explicitly preview and qualify every known side effect with owner-approved shared-rootfs scope; update contract/docs. Do not patch/restore the live rootfs in an audit.
- Acceptance: isolated copy/fixture proves exact writes and cleanup; then separately authorized production qualification establishes before/after inventory without touching active sessions.

### F-02 — Previous interactive session verification failure remains unresolved

- Severity: High; confidence: Medium; status: BLOCKED; blocks Gate B.
- Evidence: prior same-project evidence reports process-start, group, marker, argv, rootfs and launcher checks matched but `_verified` rejected the interactive process on current cwd/rootfs and guest ID checks. Current launcher source transforms the public login into `--change-id=<uid>:<gid>` and rootfs cwd; historical runtime process no longer exists, so exact discrepancy cannot be reproduced safely. Historical report and current environment are not proof of current process identity.
- Impact: no safe Ternuxx-managed interactive login can currently be claimed; weakening checks risks signaling an unrelated/shared PRoot process.
- Recommendation: compare a synthetic isolated launcher fixture against installed proot-distro argv/proc behavior, including marker propagation, process group/session, cwd and guest IDs; preserve fail-closed production behavior until it passes.

### F-03 — Ternuxx PRoot environment allows `LD_PRELOAD`

- Severity: Medium; confidence: High; status: FAIL (static finding).
- Evidence: `lib/proot_sessions.py` builds an inherited environment allowlist that includes `LD_PRELOAD` (inspect `_login_environment`, around the profile/environment helpers); installed proot-distro login source explicitly removes inherited `LD_PRELOAD` before launching guest processes. Ternuxx reintroduces it. This may load a host-provided shared object into a managed login and expands code injection across the boundary.
- Recommendation: remove `LD_PRELOAD` from the allowed PRoot environment and add a fixture test proving it is absent. No live environment was inspected for a value or changed.

### F-04 — Boot helper does not prove override state path is beneath HOME

- Severity: Medium; confidence: High; status: FAIL (static finding; script not installed in actual boot directory).
- Evidence: `scripts/termux-boot/20-ternuxx-cron:14-20` only uses `HOME.startswith(...)`; lines 29-35 climb parents checking symlinks but exit at filesystem root even if HOME was never reached. Lines 37-43 then create log/lock paths at the accepted state directory. A `TERNUXX_STATE_DIR` outside HOME can therefore pass this containment check (subject to path access), contrary to intended private-home boundary.
- Impact: an opted-in boot invocation can write logs/locks outside the expected state tree. The script is repository-only; `$HOME/.termux/boot/20-ternuxx-cron` is absent, so no current boot execution is implied.
- Recommendation: canonicalize and require a strict child path under canonical HOME, validate every component and ownership, fail if HOME was not reached. Exercise only in isolated temporary HOME tests.

### F-05 — PRoot read-only operations create a registry lock file

- Severity: Low; confidence: High; status: FAIL (read-only side-effect mismatch).
- Evidence: `lib/proot_sessions.py:174-183`, `_RegistryLock.__init__` opens lock with `O_CREAT`; read/list/health/recovery paths use it. A first read can create `$TERNUXX_STATE_DIR/proot/.sessions.lock` even when state did not exist. Process/record state may remain unchanged, but filesystem is not strictly read-only.
- Recommendation: document this narrow filesystem side effect or use a noncreating read lock path for reads and retain creation only for mutations; add temp-state test.

### F-06 — Cron schema accepts policies/runtime targets not executed by scheduler

- Severity: Medium; confidence: High; status: FAIL (validation/runtime mismatch).
- Evidence: `lib/cron_registry.py:153-176` accepts `environment=debian-proot`, retries 1..10, capability lists and policy values; `new_job` exposes these parameters around lines 211-231. Current executor/scheduler supports only native fixed actions, one attempt, skip missed runs, skip-overlap. `environment` and `required_capabilities` are not used to select execution identity or enforce authorization. Startup trigger fields are policy-preview state and are not delivered by a boot/recovery source.
- Impact: valid persisted job records can imply semantics the runtime does not provide; scheduler may reject jobs after persistence or run them in the native action context.
- Recommendation: reject unsupported nondefault policies and environment/capability claims at write time until implementations exist, or implement typed adapters and explicit authorization. Keep production Cron stopped.

### F-07 — Reconcile-stale desktop operation has a check/replace race and no separate audit event

- Severity: Medium; confidence: Medium; status: UNVERIFIED risk.
- Evidence: `desktop_session_state.py::reconcile_stale` verifies absence, rereads record, inspects again, then replaces session record; processes can theoretically appear after final inspect and before replace. It stores a status/error field but does not create an independent append-only reconciliation event. No concurrent race test was run here.
- Recommendation: consider a persistent audit event and a stronger serialized lifecycle lock shared by start/reconcile, then test a controlled process-appearance race in temporary fixtures. It sends no signal and only reconciles when all recorded processes/artifacts are absent.

### F-08 — Old `ternuxx` executable names removed

- Severity: Low; confidence: High; status: UNVERIFIED compatibility impact.
- Evidence: tracked old wrappers are deleted; `tx` replacements are present and installed `/prefix/bin/tx` points to the new root wrapper. Legacy shell aliases remain. No repository references established whether external scripts invoke `ternuxx`.
- Recommendation: decide whether a compatibility shim is required; test upgrade behavior without changing current installed state.

### F-09 — AJ peer-to-login and TXDB targets absent

- Severity: Informational; confidence: High; status: BLOCKED.
- Evidence: targeted repository searches and source/schema/test inventory found no feature. `tx db` is a login command; no database backend identified.
- Recommendation: identify exact component/repository and interfaces before implementation or threat assessment.

### F-10 — GUI, peer, boot and listener production qualification is not established

- Severity: Medium; confidence: High; status: UNVERIFIED/BLOCKED.
- Evidence: no live GUI or PRoot action was run; SSH alias is inspection-only; no `ss` executable and `/proc/net/tcp*` reads failed with permission denied. SSH 8022, 8023 and 8765 ownership cannot be asserted from this audit. The current inspection SSH shell had no DISPLAY variables, which does not describe the active GUI process.
- Recommendation: keep all lifecycle operations gated; request a separately scoped qualification with a disposable session and verifiable ownership.

## G. Runtime and subsystem status

### PRoot/rootfs/session

- Installed rootfs resolves to `/data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/rootfs`, directory mode 0755, owner `u0_a490`, dev/inode `65086:3240111`, mtime 2026-10-05. The profile hook metadata/hash are in F-01. No contents were edited, and no causal attribution is possible without a pre-test baseline.
- Prior current project state: headless disposable PRoot lifecycle was verified in isolated registry; interactive attempts failed closed on cwd/guest-ID. Treat headless probe evidence as isolated probe only. No production login/start/stop was performed during this audit.
- PRoot registry schema in current untracked implementation is version 3 (historical docs also contain schema-v2 snapshots); it records profile/launcher/rootfs/process/group/marker identities and rejects malformed or ambiguous ownership. Marker is supplementary to other checks. No automatic adoption or forced stop.
- Foreground TTY login is the only interactive mode. No detached independent supervisor or verified terminal multiplexer/reattach adapter. True reattach is not implemented. GUI/X11 compatibility and GPU acceleration remain unqualified.

### Desktop/GUI

- `$DISPLAY` and graphics variables were absent in the read-only SSH shell; this cannot establish the floating GUI’s environment. No GUI process/window/server was inspected or changed in this audit. No GPU claim is made.
- `desktop_session_state.py` uses pid start ticks, command marker, UID, group/session and X socket/lock ownership; ambiguous states fail closed. Its `ensure-state` action creates/chmods a directory, and stale reconciliation writes `session.json`; callers must not label those mutating operations read-only. Existing display inspection behavior avoids deleting stale artifacts.
- Native active GUI state was preserved; GUI acceptance is BLOCKED pending separately authorized disposable qualification.

### Cron and Termux:Boot

- Scheduler daemon/lease/registry/ledger are implemented in source and isolated test evidence exists; current production scheduler status was not invoked in this audit. No process name match for cron/scheduler was found in a limited process snapshot, which is not proof of absence.
- Actual `$HOME/.local/share/ternuxx/cron/scheduler.json` and `$HOME/.termux/boot/20-ternuxx-cron` were absent. Existing boot scripts `00-ternuxx-services`, `10-ternuxx-profile`, and `ternuxx-recovery` were observed and left unchanged. Repository-only `20-ternuxx-cron` starts Cron, not PRoot, and was not run or installed. Termux:Boot receiver/app state was not reverified in this audit; no boot change or reboot occurred.
- Job allowlist and isolated ledger/daemon tests provide fixture/runtime evidence only; unsupported policy semantics are F-06. Production Cron/boot acceptance remains UNVERIFIED.

### Networking and SSH

- Existing SSH alias uses user `u0_a490`, host `127.0.0.1`, port 8022 and `~/.ssh/id_ed25519_termux`. A read-only SSH inspection was used; no server settings/lifecycle changed. Native `/proc/net/tcp` and `tcp6` were unreadable and `ss` unavailable, so 8022/8023/8765 listeners were not attributed. Port 8765 is only a static Web default in source; this audit did not claim a live listener.

### Legacy compatibility

- `.bashrc` aliases and `x.sh` were inspected read-only: `db` → Debian login as `sbj` with shared tmp; `droot` → root login; `x`/`xgo` → `x.sh`; `killx` is explanatory only and does not kill GUI processes. `~/db/droot` was absent. Existing files/workflows were not invoked or altered.
- `tx db` is a new command implemented by argument-vector invocation of `proot-distro login`; it is not TXDB. `tx mng` is canonical and `tx management` remains an alias. Potential old `ternuxx` executable break is F-08.

## H. Acceptance matrix

| Gate / milestone | Status | Evidence / limitation |
|---|---|---|
| Repository identity/worktree preservation | PASS | Native path, main/HEAD/remotes/worktree and full status inventory captured; no Git operation changing history. |
| Every dirty/untracked path accounted | PASS with provenance limitation | 73 tracked changes + 104 untracked files enumerated; provenance of untracked files cannot be established. 112 ignored pyc files left intact. |
| AJ-managed peer-to-login | BLOCKED | No implementation/schema/test found; exact target not identified. |
| TXDB compatibility/migration | BLOCKED | No TXDB implementation found; `tx db` is PRoot login and state is JSON. |
| PRoot ownership reconciliation | UNVERIFIED | Fail-closed checks exist; prior marker-loss report exists. This audit did not signal/adopt/reconcile a live record. Need isolated fixture review. |
| Interactive TTY Debian login | BLOCKED | Historical attempts failed cwd/guest-ID checks; no live retry. Shared launcher writes rootfs state. |
| Persistent supervision/reconnect | FAIL / UNIMPLEMENTED | Foreground only; no proven detach/reattach or independent persistence. |
| Exact safe stop | PARTIAL | Code has plan and identity checks; no live stop in audit; residual race needs isolated review. |
| GUI/X11 window and cleanup | BLOCKED | No test; active GUI left untouched; shell DISPLAY absent is not GUI evidence. |
| GPU acceleration | UNVERIFIED | No diagnostic evidence and no GUI test. |
| Cron isolated implementation | PARTIAL | Historical isolated tests/evidence; not rerun. Runtime policy mismatch in F-06. |
| Cron production lifecycle | UNVERIFIED | Not queried/started/stopped; production remains untouched. |
| Termux:Boot integration | PARTIAL/UNVERIFIED | Manager/script exists in repo; 20-script absent from installed boot directory; receiver not reverified. Existing scripts unchanged. |
| Legacy db/x workflows | PASS for source preservation | Aliases/wrapper inspected and unchanged; behavior not exercised. |
| Web/API authorization boundaries | PARTIAL | Static source reviewed; no live server requests. Web mutation scope constrained. |
| Full test suite | NOT RUN in this audit | Existing evidence from immediately prior work reports 506 passed; not recertified here. Test source was sampled for fixture isolation; repository-knowledge tooling not run because it can write event metadata. |
| P3 | IN PROGRESS | `project/phase-state.json` says P3 in progress; current state accurately notes interactive login fail-closed and GUI/reattach unqualified. |
| P4/workstation general qualification | UNVERIFIED | No completed end-to-end workstation, persistence, GUI, Cron boot, or listener gates. Do not promote. |

## I. Test and tool accounting

Commands/inspections used: read-only `pwd`, `git status --short --branch`, `git diff --name-status`, `git diff --stat`, `git diff --cached --stat`, `git ls-files`, `git ls-files --others --exclude-standard`, `git worktree list`, `git remote -v`, `git rev-list --left-right --count`; source/doc/schema searches and numbered file reads; read-only native process snapshot; environment variable names/presence only; read-only filesystem metadata/hash; installed proot-distro source read; read-only SSH alias resolution and SSH inspection. `ss` was unavailable; `/proc/net/tcp*` access denied. No repository tests, CI, package actions, documentation generators, live CLI mutations, boot commands, service commands, PRoot login, X11 client, or database operations were run during this audit. This avoids test side effects and is explicit in the acceptance matrix.

Prior evidence in dirty files reports a full test run (506 tests in immediately preceding work) plus focused tests, but these are historical evidence, not a run by this audit. Exact historical commands/results must be read from their evidence files before reusing as a release gate. Test suite safety was sampled for fixture Popen/kill behavior and temporary state; full-suite global side-effect proof was not completed, so full tests remain NOT RUN.

## J. Risk-ranked continuation plan

### 1. Immediate blockers and safety defects

1. Fix the boot helper state path containment check (F-04). Prerequisites: add isolated temp HOME tests; files: `scripts/termux-boot/20-ternuxx-cron`, `tests/test_termux_boot_cron.py`. Risk: low when isolated; no install/boot changes. Done when outside-HOME, symlink, sibling-prefix, and HOME traversal cases all fail before mkdir/open and valid private child succeeds.
2. Remove PRoot `LD_PRELOAD` inheritance (F-03). Prerequisites: isolated env construction tests. Files: `lib/proot_sessions.py`, `tests/test_proot_sessions.py`. Risk: low; no live login. Done when allowlist excludes it and fixture verifies no inherited value.
3. Make Cron schema reject unsupported environment/retry/capability/trigger policy or implement explicit typed handlers (F-06). Prefer narrowing acceptance first. Files: Cron registry/scheduler/executor, schema, API and tests. Risk: medium because JSON compatibility; design migration/read compatibility before changing existing records. Done when every accepted job’s declared semantics match executor behavior.
4. Define PRoot launcher write contract (F-01) and isolatedly reproduce ownership verification (F-02). No production rootfs operation. Files: `lib/proot_sessions.py`, architecture docs, fixture tests. Done when exact launcher effects/argv/process evidence are reproduced in disposable rootfs and manager fails closed on all identity mismatch cases.

### 2. Isolated diagnostic work

5. Expand desktop stale-reconcile concurrency/audit trail tests (F-07), with temp proc/session/display fixtures and shared start/reconcile lock behavior. Do not test against active GUI.
6. Inspect all remaining dirty diffs subsystem-by-subsystem and validate docs/schema/test parity; provenance remains unknown. No cleanup.
7. Identify intended AJ peer-to-login and TXDB repositories/interfaces with owner-provided path or canonical spec; no guessed implementation.

### 3. Low-risk implementation

8. Decide whether to retain `ternuxx` wrapper compatibility (F-08); if yes, add a thin alias only after installer/upgrade tests demonstrate no conflict. Keep current installed commands unchanged until separately authorized.
9. Remove misleading “read-only” classification where lock/state creation occurs, or split non-mutating inspection from lock-creating operations; fixture tests only.

### 4. Integration and regression tests

10. After test side effects are fully reviewed, run focused fixture suites with temporary HOME/state and `PYTHONDONTWRITEBYTECODE=1`; then full suite if safe. Include legacy CLI/help alias tests, Cron allowlist/ledger, boot preview manager, PRoot ownership, GTK/Web/API shared-operation parity, schema validation, shell syntax, Python compilation, `git diff --check`, and repo knowledge verification only after confirming whether it writes event files.
11. Reconcile stale historical docs/evidence and capability matrix without rewriting user-authored dirty content; add date-scoped correction records.

### 5. Live qualification requiring separate scope/authorization

12. Interactive login in a disposable, isolated rootfs/state after launcher writes and ownership checks are understood; require genuine TTY and prove guest user/rootfs/exit state.
13. Persistent detach/reattach only if an already-installed multiplexer can be inspected and safely integrated; otherwise keep foreground-only claim.
14. GUI diagnostic window and cleanup only with disposable owned session and verified current display connection, preserving existing GUI/acceleration/audio.
15. Cron/Termux:Boot behavior only in explicit safe-test isolation; no production boot activation/reboot. Listener ownership for protected ports must be read-only and available before making claims.

### 6. Deferred design decisions

16. AJ peer-login trust/ownership/transport contract; TXDB identity, schema, data owner and migration contract.
17. PRoot boot recovery semantics independent of Cron; no automatic PRoot startup in `20-ternuxx-cron`.
18. Kernel process-handle support (`pidfd`/session control) across the actual Android/Termux kernel and safe reduction of stop TOCTOU.

## K. Final integrity report

This report and the short pointer appended to CURRENT_STATE.md are the only repository files changed by the audit. No source, tests, schemas, rootfs, boot files, service state, databases, GUI configuration, or Git history were changed by audit operations. No known external process change was detected, but no start-of-audit file hashes/snapshot exist for every dirty file, so unobserved external edits cannot be ruled out. Final status must be compared after appending this report and a short audit pointer to `CURRENT_STATE.md`; no other status difference was observed.

## Appendix — inventory source and exact lists

Complete exact modified/deleted path list is available by running `git diff --name-status` from the repository at the recorded baseline; complete untracked paths by `git ls-files --others --exclude-standard`. These read-only outputs were captured at audit start in the execution record. The worktree has not been cleaned or normalized. This appendix intentionally does not embed bytecode paths because they are ignored and generated; the audited ignored category was 112 Python `.pyc` files under repository `__pycache__` directories.

### Exact tracked delta at audit start

`git diff --name-status` output (unchanged tracked work; 73 paths):

```text
M	.github/workflows/repo-contract.yml
M	.repo/STATUS.md
M	.repo/project.yaml
M	AI_ASSISTANT.md
M	CURRENT_STATE.md
M	README.md
D	bin/ternuxx
M	docs/ARCHITECTURE.md
M	docs/DEPENDENCY-FALLBACK-MATRIX.md
M	docs/INSTALLATION.md
M	docs/OPERATIONS.md
M	docs/PHASE-STATUS.md
M	docs/PROOT-GPU.md
M	docs/PROOT-SHARED-X11.md
M	docs/ROADMAP.md
M	docs/architecture/MANAGEMENT-API.md
M	docs/architecture/SHARED-MANAGEMENT-PLAN.md
M	docs/architecture/UNIFIED-WORKSTATION.md
M	docs/architecture/decisions/ADR-0004-three-interfaces-shared-management.md
M	docs/evidence/P3-doctor-progress.md
M	lib/boot_profiles.py
M	lib/continuity.py
M	lib/continuity.sh
M	lib/desktop.sh
M	lib/doctor.sh
M	lib/doctor_report.py
M	lib/help.sh
M	lib/management.sh
M	lib/management_authorization.py
M	lib/management_catalog.py
M	lib/management_http_adapter.py
M	lib/management_http_runtime.py
M	lib/management_http_server.py
M	lib/management_service.py
M	lib/management_sessions.py
M	lib/phases.sh
M	lib/proot-xfce-wrapper.sh
M	lib/proot.sh
M	lib/proot_shortcuts.py
M	lib/reboot.sh
M	lib/reboot_recovery.py
M	lib/ssh_diagnostics.py
M	lib/x11_display.py
M	project/phase-state.json
M	schemas/boot-profile-action.schema.json
M	schemas/boot-profile-preview.schema.json
M	schemas/management-catalog.schema.json
M	scripts/cli_entrypoint.py
M	scripts/proot-gui0.sh
M	scripts/proot-x11-app.sh
M	scripts/proot-x11-shortcut-manager.sh
M	scripts/proot-x11-shortcuts.sh
M	scripts/termux-boot/00-ternuxx-services
M	scripts/termux-boot/ternuxx-recovery
M	scripts/termux-services/ternuxx-sshd/run
D	scripts/ternuxx-installed
D	ternuxx
M	tests/test_boot_profiles.py
M	tests/test_cli_entrypoint.py
M	tests/test_cli_help.sh
M	tests/test_desktop_lifecycle_fixture.py
M	tests/test_doctor_report.py
M	tests/test_management_authorization.py
M	tests/test_management_catalog.py
M	tests/test_management_http_adapter.py
M	tests/test_management_http_runtime.py
M	tests/test_management_service.py
M	tests/test_management_sessions.py
M	tests/test_native_service_scripts.py
M	tests/test_proot_shortcuts.py
M	tests/test_ssh_diagnostics.py
M	tests/test_x11_display0.py
M	tools/phase_docs.py
```

### Exact pre-existing untracked paths

The audit report itself is excluded; these are the 104 untracked paths present at audit start:

```text
.repo/events/commit-69e378eb3324-b97a676194dc3607.yaml
.repo/events/sync-69e378eb3324-state-1bcf484d96574d69-1.yaml
.repo/events/sync-69e378eb3324-state-3b2603821080e7d7-1.yaml
.repo/events/sync-69e378eb3324-state-40bb9963d96067b9-1.yaml
.repo/events/sync-69e378eb3324-state-51cebefcecc14926-1.yaml
.repo/events/sync-69e378eb3324-state-84f801dbf75e42f1-1.yaml
.repo/events/sync-69e378eb3324-state-870717662142c41e-1.yaml
.repo/events/test-69e378eb3324-1ef193279deb98ac.yaml
.repo/events/test-69e378eb3324-67f6538868b088ec.yaml
.repo/events/test-69e378eb3324-755093df3c38fc9d.yaml
.repo/events/test-69e378eb3324-80d3a7384d4db3b2.yaml
.repo/events/test-69e378eb3324-98833e3c2233fdfc.yaml
.repo/events/test-69e378eb3324-9ef3b96a659df979.yaml
.repo/events/test-69e378eb3324-a391ab119bb31378.yaml
.repo/events/test-69e378eb3324-c6e7c29e517784a9.yaml
.repo/events/test-69e378eb3324-d17c75ff180ac67d.yaml
.superdesign/init/components.md
.superdesign/init/extractable-components.md
.superdesign/init/layouts.md
.superdesign/init/pages.md
.superdesign/init/routes.md
.superdesign/init/theme.md
apps/management-center/management-center.c
bin/tx
docs/architecture/CAPABILITY-MATRIX.md
docs/architecture/CRON-JOBS.md
docs/architecture/GUI-MONITORING-POLICY.md
docs/architecture/GUI-SESSION-LIFECYCLE.md
docs/architecture/HERMES-PROVIDER.md
docs/architecture/NATIVE-GRAPHICS-AUDIO.md
docs/architecture/PROOT-SESSIONS.md
docs/evidence/2026-10-19-cron-ledger-executor-core.md
docs/evidence/2026-10-19-cron-runtime-proot-probe.md
docs/evidence/2026-10-19-cron-scheduler-lease-proot-gate.md
docs/evidence/2026-10-19-full-repo-audit-followup.md
docs/evidence/2026-10-19-gui-session-recovery.md
docs/evidence/2026-10-19-hermes-readonly-provider.md
docs/evidence/2026-10-19-independent-runtime-clipboard-branding.md
docs/evidence/2026-10-19-launcher-tui-web-followup.md
docs/evidence/2026-10-19-management-center-client-implementation.md
docs/evidence/2026-10-19-management-center-history.md
docs/evidence/2026-10-19-management-center-ssh-parity.md
docs/evidence/2026-10-19-mng-cron-foundation.md
docs/evidence/2026-10-19-native-boot-profile-identity.md
docs/evidence/2026-10-19-native-boot-profile-preview-parity.md
docs/evidence/2026-10-19-native-display-proot-full-gui.md
docs/evidence/2026-10-19-native-monitoring-shizuku-graphics-followup.md
docs/evidence/2026-10-19-native-runit-status-diagnostics.md
docs/evidence/2026-10-19-native-source-cli-entrypoint.md
docs/evidence/2026-10-19-native-ui-management-audit.md
docs/evidence/2026-10-19-native-x11-activity-fallback-tests.md
docs/evidence/2026-10-19-noncontract-cli-shortcut-removal.md
docs/evidence/2026-10-19-p3-doctor-shizuku-identity-recheck.json
docs/evidence/2026-10-19-p3-proot-process-inventory-native.json
docs/evidence/2026-10-19-termux-boot-cron-integration.md
docs/evidence/2026-10-19-timezone-foundation.md
docs/evidence/2026-10-19-tui-guided-proot-launch.md
docs/evidence/2026-10-19-tx-web-tui-cli.md
docs/evidence/2026-10-20-interactive-workstation-followup.md
docs/evidence/2026-10-20-proot-lifecycle.md
lib/cron_daemon.py
lib/cron_execution.py
lib/cron_registry.py
lib/cron_scheduler.py
lib/desktop_session_state.py
lib/gui_monitoring.py
lib/hermes_adapter.py
lib/launch.sh
lib/management_presentation.py
lib/management_web_ui.html
lib/proot_sessions.py
lib/terminal_ui.py
lib/termux_boot_cron.py
lib/timezone_support.py
lib/tui.sh
schemas/cron-execution-v1.schema.json
schemas/cron-job-v1.schema.json
schemas/gui-monitoring-policy.schema.json
schemas/proot-session-registry.schema.json
schemas/termux-boot-cron.schema.json
schemas/timezone-config-v1.schema.json
scripts/install-management-center.sh
scripts/management_desktop_bridge.py
scripts/termux-boot/20-ternuxx-cron
scripts/termux-services/ternuxx-gui-monitor/run
scripts/termux_shell_shortcuts.py
scripts/tx-installed
tests/test_cron_daemon.py
tests/test_cron_execution.py
tests/test_cron_registry.py
tests/test_cron_scheduler.py
tests/test_desktop_session_state.py
tests/test_gui_monitoring.py
tests/test_hermes_adapter.py
tests/test_hermes_management_api.py
tests/test_launch_commands.py
tests/test_management_desktop_bridge.py
tests/test_phase_docs.py
tests/test_proot_gui_routing.py
tests/test_proot_sessions.py
tests/test_terminal_ui.py
tests/test_termux_boot_cron.py
tests/test_timezone_support.py
tx
```
