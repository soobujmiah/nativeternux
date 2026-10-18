# Ternuxx testing and acceleration evidence

**Audit snapshot:** 2026-10-17. Current repository: [`soobujmiah/ternuxx`](https://github.com/soobujmiah/ternuxx). The only CLI entrypoint is `ternuxx`; project metadata, state defaults, and library paths use the same identity.

## Test state at audit snapshot (2026-10-17)

The project has a Bash/Termux desktop lifecycle CLI, native private continuity checkpoints, a read-only SSH diagnostic adapter, an owner-scoped Wake Lock coordinator, and a runit-managed SSH service. It contains no inference engine, model loader, CPU/GPU/NPU backend, or benchmark harness. On 2026-10-17 the Native Termux test suite passed 53 tests after the restart-race and SSH-diagnostics fixes; these unit/mock tests are not physical reboot acceptance tests. Live Native Termux testing validated the candidate SSH service on `127.0.0.1:8023`, same-device authenticated repository access, a separate `xgo` start/stop, and preservation of the native SSH lease while the `proot.desktop` lease was released. The owner opened Termux:Boot once, and pre-reboot readiness is now **READY FOR OWNER-OPERATED REBOOT**; actual receiver execution and reboot recovery remain unverified until the owner performs the reboot. RB03 is the active private checkpoint; RB02 is retained as a same-boot inconclusive observer attempt. See the [reboot recovery guide](REBOOT-RECOVERY-GUIDE.md), [live implementation evidence](../evidence/2026-10-17-reboot-recovery-implementation.json), and [latest native continuation report](../evidence/2026-10-17-native-continuation.json). Android procfs did not expose TCP tables, so listener evidence is the candidate daemon's loopback `ListenAddress`/startup log plus authenticated connection; external reachability was not tested. The declared development dependency is PyYAML for repository metadata tooling. No benchmark measurements exist in this repository.

The repository's recorded native `vulkaninfo --summary` result rejected Adreno 825 with `VK_ERROR_INCOMPATIBLE_DRIVER` for the tested Termux Mesa package/process. That is a verified failure of that probe, not a GPU inference test and not a verdict on the separate Ternux Debian PRoot graphics stack. Ternux's current public `main` separately documents CPU/Vulkan llama.cpp inference and experimental Hexagon HTP/QNN work in its PRoot/Android routes; these are external Ternux reports, not a Ternuxx adapter or Ternuxx release qualification. See the [Phase 0 master audit](../evidence/PHASE-0-MASTER-AUDIT.md) and [external-provider research](../RESEARCH.md#existing-ternux-ai-provider-separate-project-reviewed-2026-10-17).

## Post-snapshot update — 2026-10-18

- The owner-operated reboot happened after the 2026-10-17 audit snapshot. RB03 recorded a changed boot and a Termux:Boot observer event. The CLI verifier returned `verified_reboot_partial`: its observer had not captured sshd/service health, and authenticated connectivity was not tested by that verifier. A later read-only native Doctor/SSH inspection found `ternuxx-sshd` running under Runit with valid `127.0.0.1:8023` effective configuration; a separate password-authenticated native loopback probe to `127.0.0.1:8023` succeeded. Procfs listener enumeration and process-to-listener correlation remain unavailable, and the later probe does not prove automatic startup. The current checkpoint stays `NOT_READY`, with automatic resume disabled. See [sanitized postboot evidence](../evidence/2026-10-18-postboot-native-ssh-verification.json).
- The current Native Termux fixture/unit suite passed 129/129 after the state-aware reboot guidance and loopback SSH banner-probe changes. The banner check targets only the managed config's explicit loopback endpoint; it does not authenticate or establish listener-process ownership. These tests do not qualify boot-time GUI visibility, listener ownership, or authenticated connectivity.

Current platform snapshot in the research record: device `25053RT47C` / `onyx`, Android 16, ABI `aarch64`, Snapdragon SM8735 / Adreno 825, Termux `0.119.0-beta.3`; native Termux Vulkan ICD package recorded as Mesa `26.2.4`. This is dated prior observation, not rechecked in this documentation audit. The platform brief lists Hexagon NPU silicon, and current upstream projects document experimental Qualcomm HTP inference backends, but Ternuxx has no backend integration or workload result. See [research](../RESEARCH.md) and the per-backend pages below.

## Canonical evidence and matrix

- [`FEATURE-MATRIX.yaml`](FEATURE-MATRIX.yaml) is the versioned feature/offer classification source, dated to its 2026-10-17 audit snapshot. The post-snapshot boot and P3 changes below are authoritative for those items until the matrix receives a full refresh. It is not yet rendered by a website.
- [Device compatibility matrix](DEVICE-COMPATIBILITY.md) separates detection, initialization, workload verification, and release qualification.
- [CPU baseline](CPU-BASELINE.md), [GPU acceleration](GPU-ACCELERATION.md), and [NPU acceleration](NPU-ACCELERATION.md) state current evidence and the next owner-operated test needed.
- [Benchmark methodology](BENCHMARK-METHODOLOGY.md) defines comparable CPU/GPU/NPU experiments and report fields before data collection.
- [Known limitations](KNOWN-LIMITATIONS.md) is the concise public-facing source for present blockers.
- [Report template](reports/REPORT-TEMPLATE.md) defines what counts as a reproducible test report.
- [Native management slice report](../evidence/2026-10-17-native-management-slice.json) records the restart regression, checkpoint/lease tests, SSH diagnostic mock and native-runtime observations, and limitations.
- [Reboot recovery implementation evidence](../evidence/2026-10-17-reboot-recovery-implementation.json) records the native install, private checkpoint, live CLI checks, observer dry-run and blockers. It does not qualify an Android reboot.

## Status vocabulary

| Status | Meaning |
|---|---|
| `PASS` | All stated acceptance criteria passed for the named version, device, runtime, model/workload, and context. |
| `FAIL` | A named executed criterion failed; include the exact failure and scope. |
| `PARTIAL` | Some stages passed, but end-to-end workload/correctness/release criteria did not. |
| `BLOCKED` | Testing cannot proceed because a required implementation, SDK/runtime, permission, artifact, or approval is missing. |
| `UNKNOWN` | Evidence is insufficient or the test has not been performed. Do not reinterpret this as success. |

Qualification stages are cumulative labels, not synonyms: `DETECTED` → `INITIALIZED` → `WORKLOAD_VERIFIED` → `RELEASE_QUALIFIED`. A capability is not workload-verified until logs show the backend received the intended operations and the same workload returns correct output. Partial delegation must state how much ran on each backend; a silent CPU fallback is not GPU/NPU success.

## Free-core evidence policy

CPU inference/fallback, any supported GPU/NPU inference, essential backend selection and diagnostics, basic benchmark reproduction, compatibility reports, documentation, examples, and access to evidence are free-core targets. An implementation or test limitation does not change that classification into premium. Advanced orchestration, scheduled fleet/report workflows, and bespoke integrations are candidates only; nothing in this catalog is currently sold.

Until license history and provenance are resolved, the public GitHub repository is visible but there is no approved redistribution license or installable release. Do not publish binaries/models or describe source as open source. The [commercial readiness record](../readiness/README.md) tracks these gates.

## CI versus device evidence

CI may validate parser behavior, backend-independent unit logic, report schemas, deterministic fixtures, documentation links and generated chart consistency. Mark all such results `synthetic_ci`; they cannot satisfy device compatibility or acceleration acceptance. Physical-device acceptance is owner-operated unless the owner explicitly authorizes a bounded test. Owner-authorized work to date includes Termux service setup, SSH validation, Wake Lock coordination, an isolated `xgo` lifecycle, the approved native XFCE package transaction, native desktop lifecycle checks, and a reboot-recovery check. The owner viewed the X11 desktop; no agent-driven Android UI interaction occurred. These authorizations do not cover inference runtime/model installation or modification of the protected Ternux PRoot rootfs.

## Report and release rule

Every future report must identify source commit and release, exact device/runtime/backend/model hashes and licenses, reproducible commands, expected/observed backend selection, correctness verdict, raw data, repeated-run methodology, thermal/memory limitations, and whether a human or CI executed it. Keep failed/incomplete runs. Publish benchmark charts only from the machine-readable raw results for reports with an explicit accepted verdict.
