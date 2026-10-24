# Native-only migration and PRoot removal audit

## Evidence

Phase: `P4`

This evidence records owner-directed closure of former P4 guest-provider work by retiring the PRoot runtime and redirecting the repository to Native Termux-only support.

## Scope and decision

The owner requested full alignment with the canonical SKB context for Native Termux, asked for a complete repository audit before implementation, then explicitly authorized removing all PRoot, including the live Debian guest, and confirmed that a backup exists. The target is therefore a Native Termux-only Ternuxx product. This supersedes the provider choices in ADR-0001, ADR-0010, ADR-0015, the current product vision, and the P4–P9 roadmap as current direction. Their old evidence remains historical unless a later change removes it after a retention review.

Keep the existing guided CLI/TUI/Web/GTK experience for Native functions. Remove PRoot launch, setup, guest-management, graphics handoff, PRoot-only package, and related client controls. Do not close Termux or stop the Native desktop, SSH, GUI, or other Native services as part of this work.

## Repository audit

- Verified checkout: `/data/data/com.termux/files/home/ternuxx`, branch `main`, remote `https://github.com/soobujmiah/ternuxx.git`, HEAD `33a465c6f32c15d1ab11cb4e070505dfb95798d0`.
- The worktree already contained an in-progress Web same-runtime reload/reconnect change and evidence. Its files are outside the PRoot scope and must be preserved.
- Read project instructions, current handoff, README, product vision, roadmap, architecture, security policy, package/setup guidance, management API, client capability matrix, dependency fallback matrix, PRoot graphics contract, relevant ADRs, SKB policy-resolution contract, and the active repository audit. `python3 tools/audit_documents.py --check` reports path/hash coverage current; the repository's document inventory still records many files not individually read, so that mechanical inventory is not represented as a completed content review.
- Audited the CLI/help routing, Native package transaction, PRoot shell adapter, Debian manifest, management service/authorization/catalog/presentation/HTTP/Web/terminal client references, shared desktop/graphics/diagnostics dependencies, scripts, schemas, docs, and test references. PRoot is cross-cutting: it is not safe to remove only the direct CLI files. Main seams include `lib/proot*.py`, `lib/proot.sh`, `lib/management_service.py`, `lib/management_catalog.py`, `lib/management_authorization.py`, `lib/management_http_runtime.py`, `lib/management_web_ui.html`, `lib/terminal_ui.py`, `scripts/management_desktop_bridge.py`, `lib/help.sh`, phase tooling, package/profile data, schemas, docs, and associated tests.
- `./tx help` still presented `tx db`, `tx pgui`, PRoot management, app, audio, VirGL, and terminal flows as primary shortcuts. Native start/stop/status, SSH, monitoring, recovery, management clients, and install/update paths are separately implemented and must remain usable.
- Baseline verification: `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh` passed all 939 tests in 122.813 seconds. The inherited Codex `LD_LIBRARY_PATH` prevents the installed Termux Node binary from linking; clearing that variable allows Node 24.22.1 to run. This affects verification environment only.
- `python3 tools/audit_documents.py --check` passed. The complete suite and source-reference inventory provide broad baseline coverage; historical evidence remains dated and is not a claim about current runtime state.

## Live Native Termux audit

- Runtime is Native Termux on Android 16/aarch64; `$PREFIX=/data/data/com.termux/files/usr`; `$HOME=/data/data/com.termux/files/home`. The current checkout and installed `tx` command are Native-side.
- Read-only `tx proot setup status --json` identified the adopted default Debian rootfs at `/data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/rootfs`, device/inode `65086/3240111`, Debian profile `ternuxx-debian-trixie-workstation`, recorded user `sbj`, and package baseline `matches`.
- Read-only PRoot inventory found six aliases: `debian`, `ternuxx-replay-audit-20261023`, `ternuxx-replay-p4`, `ternuxx-replay-p4-coldboot`, `ternuxx-replay-p4-retry`, and `ternuxx-replay-repro`. Recorded Ternuxx sessions were stopped/released and the host PRoot process inventory was empty, with `ownership=unverified` for the installation. The package database reports `proot-distro 5.9.0` and `proot 5.1.107.96` installed.
- Apparent tree sizes from `du` were 20 GB for default Debian, 3.2 GB each for four replay guests, and 175 MB for the remaining replay guest. Device free space was about 61 GB. These are filesystem-usage observations, not a backup check.
- A recursive size scan encountered Android shared-storage/system mount-point permission boundaries inside the guest tree. No file content in those locations was read. Do not traverse shared/external storage. The installed `proot-distro` 5.9.0 removal implementation uses its descriptor-relative `rmtree_at` cleanup and documents that symlinks are unlinked without following targets; verify exact alias and outcome before/after each live removal.
- `tx proot status` showed no active host PRoot process and all recorded Ternuxx sessions as stopped. Native X11/desktop and managed services remain outside this operation; no app closure or service stop is authorized.

## Implementation and verification requirements

1. Preserve the pre-existing dirty Web-session work and history.
2. Remove PRoot from current product scope, source routes, package manifests, guided help, docs, active schemas/catalogs, and tests without breaking Native management clients or leaving dead controls. Keep interactive Native guidance intact.
3. Retire all six live distro aliases through the installed PRoot-Distro's exact named remove operation. Confirm inventory first and after each removal. Then remove the now-unused `proot-distro` and `proot` Termux packages using Termux's package manager; verify the Native base package plan no longer depends on them.
4. Do not traverse, inspect, or remove shared/external-storage targets. Keep Termux app and Native desktop/services open.
5. Run the complete suite, CLI/help checks, document/link checks, package plan checks, and live Native smoke checks after code changes. Record the exact outcomes and remaining limits.

## Authorization and limits

Live distro and package removal are consequential actions. The owner explicitly requested “sob remove koro proot” and confirmed having a backup; this is the applicable human authorization under SKB's policy-resolution contract. The backup is owner-reported and was not accessed or independently verified. Shared/external storage remains outside scope. Preserve audit evidence and the pre-existing Web-session changes.

## Removal result and post-change verification

- Retired the six exact aliases in sequence with `proot-distro remove`: `debian`, `ternuxx-replay-audit-20261023`, `ternuxx-replay-p4`, `ternuxx-replay-p4-coldboot`, `ternuxx-replay-p4-retry`, and `ternuxx-replay-repro`. `proot-distro list` showed no installed containers after the last removal.
- Removed only `proot-distro` and `proot` using `pkg uninstall -y proot-distro proot`; the simulated package plan confirmed those were the only package removals. Both commands are absent afterward and package records are absent.
- Post-change `tx status --json` still reports Native display `:1`, supervisor/X11/XFCE live and Native audio ownership. `tx help` now lists Native management routes, and `tx proot status --json` / `tx pgui status --json` return `feature_removed`.
- Base package-plan tests passed (16 tests); authenticated Web runtime tests passed (22 tests, including JavaScript syntax under Native Node after clearing the injected loader path).
- The complete test suite was run after the first migration edits: 938 tests, 36 failures and 9 errors. The failing set includes legacy PRoot/terminal contracts and some mixed CLI/catalog/service expectations that still require migration or removal. Therefore the repository-wide suite is not yet passing and full implementation retirement is not complete.
- Document inventory/hash check passes after indexing the new evidence. It reports 114 of 458 documents marked read and six broken local links; this is not a claim that every historical document has been reviewed. The six link findings still need triage.
- Shared/external storage was not traversed. Backup remains owner-reported and unverified. No Termux app closure or Native service stop was performed.

## Updated verification

The updated full suite ran 900 tests and had one failure in `test_boot_entry_uses_canonical_state_default_without_override`; rerunning its containing `test_native_service_scripts.py` module passed all six tests. The focused package-plan suite (16), authenticated Web runtime suite (22), HTTP adapter suite (12), authorization suite (6), catalog suite (6), management service suite (33), management sessions suite (12), desktop bridge suite (46), terminal UI suite (51), CLI help suite, and PRoot shortcut unit suite (20) passed. `git diff --check` passed. The full suite has not yet had a clean all-pass rerun.

The repository still contains inactive PRoot-specific implementation modules and many historical/legacy documents. User-facing routes, authorization scopes, session scopes, catalog entries, Native package dependencies, top-level help, and the Web PRoot/terminal controls have been retired; source-module deletion and full historical-document reconciliation remain follow-up work. Current phase state therefore remains in progress.


## Final Native-only retirement verification

- Removed former PRoot guest setup/session/shortcut/diagnostic and VirGL source modules, schemas, install/management routes, terminal broker path, GTK guest controls and VTE dependency, dedicated service scripts, and feature-specific tests/tools. Historical evidence remains dated; links to deleted implementation files have been converted to plain historical references.
- Current phase status records P4 as completed by retirement, advances to Native Termux profile compatibility, and revises later workload planning to Native scope.
- Full repository harness `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: 654 tests passed in 91.811 seconds. CLI help contract passed; focused Native remote-access, boot/service, SSH client, GTK UI, and authenticated Web tests passed. GTK4 C syntax check and `git diff --check` passed. The current document inventory reports 116/454 files marked read, with 0 broken local links; this is not a claim of complete historical-document reading.
- `tx status --json` reports display `:1`, live supervisor/X11/XFCE, and `ternuxx-native` audio ownership. `tx proot status --json` and `tx pgui status --json` return `feature_removed`; `proot` and `proot-distro` are absent from PATH.
- No shared/external storage was traversed and no Termux app or Native service was stopped. The owner-reported backup was not inspected.


Gate: PASS

## Acceptance criteria

- All six installed guest containers and both Termux PRoot packages are absent; retired PRoot CLI routes fail closed.
- PRoot guest lifecycle, app menu, terminal broker, VirGL handoff, client controls, schemas, dedicated tools, and feature-specific tests are removed from active source. Native management controls remain and the GTK client compiles.
- The complete repository test harness passes all 654 tests; CLI help, document link audit, package-plan tests within the suite, and live Native desktop/audio status checks pass.
- Ternuxx remains Native Termux-only in current product and phase documentation; dated reports remain explicitly historical.


## Post-migration regression and live recheck — 2026-10-24

- `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh` passed all 657 tests in 92.077 seconds. The phase workflow tests (9) and graphics verification tests (16) passed independently; CLI help contract passed.
- `python3 tools/audit_documents.py --check` reports current path/hash coverage and zero broken local links (459 documents indexed). The read-mark count is not a claim that every historical document was reviewed. `git diff --check` passed.
- `command -v proot` and `command -v proot-distro` return no executable; `dpkg-query` has no installed package records for either package; the PRoot-Distro containers directory is absent. Retired `tx proot` and `tx pgui` routes return `feature_removed`.
- `tx status --json` reports display `:1`, live supervisor/X11/XFCE, and `ternuxx-native` audio ownership. No Termux app or Native service was stopped.
- Historical records still mention PRoot because they preserve dated evidence; those files are indexed as historical and are not current instructions. The backup remains owner-reported, not inspected. Shared/external storage remains untouched.

## Residual Native-side PRoot state sweep — 2026-10-24

A follow-up live scan found retired PRoot state outside the repository and the removed guest roots. The package manager records and executable were already absent, but the following unused PRoot-only state remained:

- Ternuxx state trees `proot/`, `proot-display0/`, and `proot-setup/`; the first contained nine session records, all marked `stopped` with no corresponding live process. The setup artifact `c014cf66bdbff96417ee30d34f006cf51df64ae04893d599711b0b6b73b52ccf.tar.gz` was a 11,648,933-byte regular file with SHA-256 `c014cf66bdbff96417ee30d34f006cf51df64ae04893d599711b0b6b73b52ccf`; its provenance is linked to the former Debian Trixie graphics setup record above. The archive was listed, not extracted.
- `$PREFIX/var/lib/proot-distro/` retained only empty container storage plus stale lock and session metadata. All 12 recorded session PIDs were absent from `/proc`; the tree contained no symlink or foreign-owned entry. The package-private state tree was removed.
- Thirty-six exact `ternuxx-proot-app-*.desktop` launchers and `ternuxx-proot-apps.directory` remained in the Ternuxx XFCE profile. Those retired guest launchers and their menu category were removed; no panel, X11 server, XFCE session, or Termux process was restarted.
- The user shell profile contained a `clean-mesa` function that invoked `proot-distro login debian` and an informational `killx` alias with stale PRoot wording. The PRoot-only function was removed and the alias wording was updated; `bash -n ~/.bashrc` passed. The owner reported an independent backup; it was not inspected.
- A final scoped name scan of `$PREFIX/bin`, `$PREFIX/var/lib`, `$PREFIX/var/cache/apt/archives`, `$PREFIX/etc`, and `$TERNUXX_STATE_DIR` found no path containing `proot`. `proot` and `proot-distro` remain absent from PATH and package status. `tx proot status --json` and `tx pgui status --json` return `feature_removed`.
- `tx status --json` still reports display `:1`, supervisor, X11, XFCE, and Native audio live. Shared/external storage was not accessed.

This sweep removes PRoot-specific runtime state and stale entry points. Dated repository evidence and historical documentation intentionally retain PRoot references and remain labeled historical.

## Git object-store references into the retired guest — 2026-10-24

During final commit review, 113 dangling symlinks were found under this checkout's `.git/objects/??/` paths. Each pointed to a `.l2s/.l2s.tmp_obj_*` path inside the removed Debian guest rootfs. The target files were absent; no target contents were read. Their link names and target strings were recorded in a private Termux cache manifest, then the dangling symlink entries were removed from the active Git object directories. A `git fetch --refetch --no-tags origin main` restored reachable GitHub objects; the previously missing blob became readable. Final `git fsck --full --no-reflogs` reported only pre-existing dangling objects, with no missing/corrupt-object or garbage warnings; object symlink count is zero. Two incomplete temporary fetch packs were moved out of `.git/objects/pack` to the private cache. No branch ref changed and no commit was made during repair.

This was local repository metadata fallout from object links into the removed guest, not PRoot product code. The private recovery manifest and incomplete pack artifacts are outside the repository and are not part of project evidence.
