# Native Termux operations

Ternuxx manages the Android workstation from the Native Termux app. Run `tx help` for the current command list and `tx guides` for interactive setup and recovery guidance. Historical PRoot commands return a migration message and do not launch a guest.

## Core workflow

```sh
tx doctor
tx info
tx start
tx status
tx tui
tx web
tx mng center
```

`tx start`, `stop`, `restart`, and `status` operate on the recorded Native desktop. The supervisor verifies process identity before sending signals and refuses ambiguous ownership. The Android Termux:X11 app's visible state is separate from server readiness.

## Management clients

The CLI, TUI, authenticated Web UI, and GTK center call the same typed management service. Implemented operations share validation, authorization, and state; each client exposes only actions supported in its context. Read the catalog and each command's `--help` output before applying a change. Mutations that affect services, packages, keys, boot state, or recovery require the exact preview and confirmation described by the command.

## SSH and services

`tx ssh inspect` is read-only. Managed SSH configuration and lifecycle changes are scoped to the fixed Native Runit service and use preview/rollback flows. The service listens on loopback port 8023; port 8022 is not managed by Ternuxx. Do not infer exposure from a config file alone.

Native audio, desktop monitoring, boot profiles, and Wake Lock controls have independent owners and state. A stop operation releases only resources whose identity matches a Ternuxx record.

## Packages and updates

`tx install preview` and `tx install update preview` show the exact Native Termux package transaction. Apply only the reviewed plan ID. If a package operation fails partway, inspect APT output/history and create a fresh preview; Ternuxx does not claim an automatic package rollback.

## Optional Native apps and HOME file handoff

Use tx app list to inspect the curated htop, tmux, and tree catalog. Preview install, update, or removal before applying the saved plan. The TUI, authenticated Web UI, and GTK center use the same service.

When tree is installed, tx app run directory-tree HOME_PATH passes one selected HOME-relative file or directory to the fixed tree executable. It lists names only, is limited to two levels and 32 entries per directory, and rejects paths outside Native HOME, symlinks, special files, and traversal. It does not read file contents or Android shared storage. The TUI, Web, and GTK clients expose the same bounded action.

## Local CPU inference

Run `tx ai status` to inspect the Termux-owned runtime and pinned model. `tx ai setup` guides first use; it does not install Termux packages. Preview model download or removal before confirming it. TUI, Web, and GTK expose the same shared CPU inference service with separate run and model-management scopes. Prompts are handled on-device and are not written to Ternuxx logs; the Web interface is authenticated and loopback-only.

Each run uses CPU only (`-ngl 0`), four threads, a 512-token context, at most 128 output tokens, one prompt line, and a 120-second timeout. Ctrl-C terminates only the inference process group. Ternuxx verifies the pinned model SHA-256 before each run and removes only that fixed model after confirmation. The runtime package remains owned by Termux. See the [CPU baseline](testing/CPU-BASELINE.md) and [workflow evidence](evidence/2026-10-24-native-cpu-inference-workflow.md).

## Recovery and backups

`tx backup`, `tx restore`, `tx recovery`, and `tx checkpoint` operate on the private Ternuxx Native state paths. They do not inspect Android shared storage. Recovery refuses symlinks, stale plans, ambiguous process identity, and changed targets. Keep private keys, passwords, bootstrap codes, and unredacted logs out of evidence and Git.

## Retired PRoot routes

Ternuxx no longer supports `tx db`, `tx pgui`, `tx proot`, Debian app launch, guest terminal, guest setup, or guest graphics handoff. The owner authorized removal of the installed guest containers and PRoot packages; the live retirement and verification are recorded in the [migration evidence](evidence/2026-10-24-native-only-proot-removal-audit.md). Historical dated reports do not describe the current supported product.
