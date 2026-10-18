# CPU inference baseline

**Status:** `BLOCKED` for product implementation; end-to-end validation `UNKNOWN`. **Commercial class:** `FREE_CORE` target.

## Current evidence

No inference engine, model, tokenizer, CPU inference API, example, correctness test, or benchmark is present in the audited repository. The project uses Bash for its CLI and PyYAML for repository state tooling. Device CPU cores existing is not Ternuxx inference support. No model/runtime was installed or downloaded during this audit.

Upstream llama.cpp documents a portable Android CLI build and a Termux build path, making it a research candidate for an offline CPU baseline. This is not a Ternuxx integration or a benchmark result: [upstream Android/Termux guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md). Runtime selection requires source/license/notice review, memory behavior, model-format support, update cadence, build reproducibility, and exact Termux dependencies.

## Free-core acceptance

CPU remains the dependable fallback and must not require premium entitlement or network access. Before calling it supported, an authorized implementation must prove:

1. An approved runtime/model pair installs from an auditable source and its applicable licenses are recorded.
2. A named model loads, tokenizes, executes and returns output under a bounded memory/context configuration.
3. A deterministic correctness fixture passes (tokenization, known prompt behavior or runtime reference test as appropriate); quality impressions are not the correctness test.
4. Model/runtime errors, insufficient memory, cancellation, and unsupported formats fail clearly without leaving stale processes/files.
5. CPU execution is explicitly selected/observed; no hidden GPU/NPU delegation contaminates the baseline.
6. The same model/hash and inputs are measured with the protocol in [benchmark methodology](BENCHMARK-METHODOLOGY.md).
7. Offline use works after artifacts are available locally; no telemetry or mandatory account is required.

Until those pass, public status remains `NOT_IMPLEMENTED` / validation `BLOCKED`; do not publish CPU tokens/s or promise a model size.
