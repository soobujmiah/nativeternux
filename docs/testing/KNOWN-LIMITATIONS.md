# Current implementation and qualification limits

See [phase state](../../project/phase-state.json), [client coverage](../architecture/CAPABILITY-MATRIX.md), and [the active audit](../audit/REPOSITORY-AUDIT.md). Historical evidence retains its date and scope.

- Product unit/fixture tests exist and run on Native/CI. They do not qualify Android boot, fresh setup, GPU/NPU use, or complete live client parity.
- SSH key generation/enrollment/removal, password/recovery controls, per-SSH boot policy, and selectable service Wake Lock policy remain incomplete.
- Broker and four terminal paths exist; full disposable managed guest lifecycle is not accepted. Protect the owner's Codex guest.
- Fresh Debian setup is fixture-tested and refuses the existing rootfs. Separate live replay and complete recovery remain unqualified; the customized workstation is not yet reproducible from this repository alone.
- Direct `:1`, standalone `:0`, and nested `:2` graphics are separate. Nested draw/presentation remains unqualified.
- Selected experimental Native GL/GLES/Vulkan draws exist. Stock ICD failure, fallback, application compatibility, clean driver installation, sustained/thermal behavior, and inference are separate gates.
- No Ternuxx inference engine, model loader, CPU/GPU/NPU inference backend, or inference benchmark harness exists. External experiments do not qualify this project.
- P1–P3 are accepted within dated scope. RB08 has direct Native boot/authenticated evidence, while its private checkpoint stays NOT_READY with auto-resume disabled. Current recovery modules were deployed afterward.
- Full installed/source parity, all-document review, and reproducibility acceptance remain open in the audit.
- No compatibility combination is a supported public release. License/provenance remain unresolved.

Use UNKNOWN for missing evidence, BLOCKED for a concrete prerequisite, and FAIL only for an executed failed criterion. Record observed viewport/workload values rather than assuming requested settings were achieved.
