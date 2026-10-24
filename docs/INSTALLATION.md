# Native Termux installation and upgrade guide

Ternuxx installs Native Termux workstation packages through a saved, preview-first transaction. It does not create or manage Linux guest environments.

## Install

Enable the Termux X11 package repository, install Git, clone Ternuxx, and inspect the Native package transaction:

```sh
pkg update && pkg install x11-repo git && pkg update
git clone https://github.com/soobujmiah/ternuxx.git "$HOME/ternuxx"
cd "$HOME/ternuxx"
./tx install preview
```

Review the exact package and dependency plan, then apply only its saved plan ID:

```sh
./tx install apply PLAN_ID
```


## Optional Native CPU inference

`tx ai status` inspects the Termux-owned `llama-cpp` runtime and Ternuxx's pinned local model. If the runtime is absent, first review `apt-get -s install llama-cpp`; package installation remains a separate Termux package-manager action and is never performed by Ternuxx. After the runtime is available, `tx ai setup` offers the exact pinned 429 MB model preview and requires you to type `DOWNLOAD` before fetching it. The model file is checked against its fixed size and SHA-256 before it is installed under private Ternuxx state.

Use `tx ai model preview` to review the model URL, destination, license, required storage, and hash without network access. `tx ai run` reads one line from the terminal or stdin and runs locally on CPU only, with a bounded context, token count, and timeout. Model downloads need network access; inference uses the local model file. Network-isolated inference has not yet been verified on-device. See the [CPU baseline](testing/CPU-BASELINE.md) for current limits and evidence.

The transaction refuses removals and upgrades. To preview upgrades of installed Ternuxx core packages:

```sh
./tx install update preview
./tx install update apply PLAN_ID
```

Update refuses removals, downgrades, and packages outside official Termux repositories. The matching Termux:X11 Android app must be installed separately for a desktop.

## First checks and desktop

```sh
./tx help
./tx guides
./tx doctor
./tx info
```

Open the Termux:X11 Android app, then start the Native desktop:

```sh
./tx start
```

For interactive management, use `./tx tui`, `./tx web`, or `./tx mng center`. Each client uses the shared service; supported actions can vary by client. See the [capability matrix](architecture/CAPABILITY-MATRIX.md).

## Native SSH and recovery

`./tx ssh inspect` reports Native SSH state. Managed SSH lifecycle actions use preview and confirmation. The product service is loopback-only on port 8023; port 8022 is a separately owner-managed repository-work channel.

`./tx backup`, `./tx recovery`, and `./tx checkpoint` show private Native state backup and recovery guidance. Read the exact target and plan before applying a change. Ternuxx does not scan shared storage or manage arbitrary files.

## Optional Native apps

The separate curated catalog currently offers htop, tmux, and tree. Use `tx app list`, then preview the exact install plan before applying it. After installing tree, `tx app run directory-tree HOME_PATH` provides a bounded, read-only HOME path listing. It does not access shared storage or read file contents. See the [software catalog](SOFTWARE-CATALOG.md) for source and safety details.

## Current limits

The current device is already configured; this is not a clean-device reproduction claim. Package candidates can change over time, and the saved preview is not an offline artifact mirror. GPU/NPU acceleration, rollback, supported-device coverage, and public release each require separate evidence. No PRoot guest setup is supported by Ternuxx.

## Optional Native apps

The separate curated catalog currently offers htop, tmux, and tree. Use tx app list, then preview the exact install plan before applying it. After installing tree, tx app run directory-tree HOME_PATH provides a bounded, read-only HOME path listing. It does not access shared storage or read file contents. See the software catalog for source and safety details.
