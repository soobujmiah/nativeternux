# Canonical identity and P4 broker audit — 2026-10-22

Phase: `P4`

## Scope and source

The audit and implementation ran in Native Termux through SSH port 8022 in `$HOME/ternuxx`. The checkout was fast-forwarded from `origin/main` before implementation; all pre-existing modified and untracked work was retained and reviewed. Product identity is Ternuxx, with Native Termux as the self-sufficient core and PRoot as an optional provider.

A case-insensitive scan of tracked and untracked repository content (excluding Git object/history and generated `.repo` metadata) found no obsolete product-name spellings or filenames. Historical Git objects were not rewritten. Assistant instructions now direct project work through the configured Native Termux SSH alias on port 8022 and specify the canonical state/module paths and migration-preservation rule.

## Runtime identity and preservation

- The obsolete executable and module paths are absent; canonical `$PREFIX/bin/tx` and `$PREFIX/lib/ternuxx` are present.
- Native service and recovery helpers use only the canonical state variable. The installed boot helper matches repository source after the exact preview/apply operation; rollback snapshot `0bdc14db04ec16a973a7d301394e6ad9` is retained.
- The recovery module was atomically updated under `$PREFIX/lib/ternuxx`; its prior version is retained in the private runtime-deployment backup. No service was restarted.
- The separate private historical state directory was moved intact to `~/.local/share/ternuxx/archives/prior-state-20261022`. Its device/inode identity and recursive 129-entry metadata manifest matched before and after. Private contents were not opened or copied; the archive can be moved back.
- Read-only PRoot inventory found Debian installed and an unverified host process candidate. No guest was entered, stopped, or modified. Desktop status reported Native `:1` stale and nested `:2` absent; neither was mutated. No reboot occurred.

## Evidence

The private Unix terminal broker remains an optional, typed transport primitive. This increment hardens its protocol: unsupported non-string operation values return a broker error, output is split into 24 KiB chunks and delivered one sequence at a time, and regression coverage verifies pagination. The production broker service loop and CLI/TUI/Web/GTK terminal clients are still open P4 work; no live guest was used for this implementation.

`bash scripts/repo_test.sh` on Native Termux passed **687/687** in 98.336 seconds. Broker focused tests passed **10/10**. Python compilation, boot shell syntax, and `git diff --check` passed. The full run emitted an existing package-index freshness warning from a test fixture; it did not fail a test.

The repository-wide source/filename scan found no obsolete product-name spellings. P4 remains active. Next: wire a supervised production broker to the fixed interactive PRoot PTY lifecycle, then add and qualify authenticated client transports for CLI/TUI/Web/GTK on a disposable guest while preserving the current rootfs and optional-provider boundary.
