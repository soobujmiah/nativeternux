# Ternuxx documentation index

Use this page to find the current product, operating, architecture, testing, audit, and release-readiness documentation. The live phase status is generated from `project/phase-state.json`; dated evidence records what was observed at the time named in each file.

## Start here

- [Product vision](PRODUCT-VISION.md)
- [English quick start](../README.md)
- [বাংলা পরিচিতি](../bn/README.md) · [বাংলা ইনস্টল নির্দেশিকা](../bn/INSTALLATION.md)
- [Installation and upgrade](INSTALLATION.md)
- [Operations and command reference](OPERATIONS.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap and phase gates](ROADMAP.md)
- [Current phase status](PHASE-STATUS.md)

## Native workloads

- [Native graphics and audio](architecture/NATIVE-GRAPHICS-AUDIO.md)
- [Software catalog](SOFTWARE-CATALOG.md)
- [Optimization guide](OPTIMIZATION.md)
- [Wine/Hangover research (not implemented)](WINE-NATIVE.md)

## Architecture and interfaces

- [Shared capability matrix](architecture/CAPABILITY-MATRIX.md)
- [Management API](architecture/MANAGEMENT-API.md)
- [SSH lifecycle](architecture/SSH-LIFECYCLE.md)
- [Architecture decisions](architecture/decisions/)

## Historical PRoot documentation

The pre-Native-only [roadmap](history/ROADMAP-pre-native-only-2026-10-24.md), [management API contract](history/MANAGEMENT-API-pre-native-only-2026-10-24.md), [feature matrix](history/FEATURE-MATRIX-pre-native-only-2026-10-17.yaml), and [software catalog](history/SOFTWARE-CATALOG-pre-native-only-2026-10-24.md) are archived alongside the older dated reports below. These materials are retained as historical records and do not describe supported product behavior.

The following dated/legacy materials are retained as historical records and do not describe supported product behavior: [hybrid integration](HYBRID-INTEGRATION.md), [PRoot session lifecycle](architecture/PROOT-SESSIONS.md), [PRoot graphics](PROOT-GPU.md), [PRoot GUI display experiment](PROOT-GUI-DISPLAY0.md), [shared-X11 PRoot applications](PROOT-SHARED-X11.md), [interactive guest terminals](architecture/INTERACTIVE-PROOT-TERMINALS.md), and the [pre-migration reboot guide](history/REBOOT-RECOVERY-GUIDE-pre-native-only-2026-10-24.md).

## Testing and evidence

- [Testing and qualification](testing/README.md)
- [Native reboot and recovery](testing/REBOOT-RECOVERY-GUIDE.md)
- [Known limitations](testing/KNOWN-LIMITATIONS.md)
- [CPU baseline](testing/CPU-BASELINE.md)
- [GPU qualification](testing/GPU-ACCELERATION.md)
- [NPU qualification](testing/NPU-ACCELERATION.md)
- [Device compatibility](testing/DEVICE-COMPATIBILITY.md) · [Current capability matrix](testing/FEATURE-MATRIX.yaml)
- [Dated evidence](evidence/) · [Device test reports](testing/reports/)

## Project maintenance

- [Repository audit worklist](audit/REPOSITORY-AUDIT.md)
- [Phase revalidation](audit/PHASE-REVALIDATION.md)
- [Knowledge synchronization](KNOWLEDGE-SYNC.md)
- [Security policy](../SECURITY.md)
- [License and release readiness](readiness/README.md)
- [Third-party artifact notices](readiness/THIRD-PARTY-NOTICES.md)
