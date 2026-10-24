# Native CPU inference candidate audit — 2026-10-24

Phase: `P6`
**Evidence class:** direct Native Termux package/model inspection and bounded device workload.
**Target:** Android 16/API 36, Redmi `25053RT47C`, aarch64, Termux `0.119.0-beta.3`.

## Evidence

## Candidate and provenance

- The current local Termux package index offered `llama-cpp 0.7.0` (aarch64), 7,136,308 bytes downloaded and 21.2 MB installed. Its direct dependencies were already installed; `apt-get -s install llama-cpp` previewed exactly one new package, zero upgrades, and zero removals. The exact configured source was the `termux-main` mirror `https://termux.danyael.xyz/termux/termux-main`. Termux’s published [mirror inventory](https://github.com/termux/termux-packages/wiki/Mirrors) lists this as Dan Yael’s mirror and says it syncs every six hours; it is a mirror, not the Termux primary host. The local APT index showed the package candidate from this URL.
- The package was installed with `pkg install -y llama-cpp` for this bounded qualification. The transaction installed only `llama-cpp 0.7.0`; no Termux packages were upgraded or removed. Termux `pkg` automatically refreshed its configured package indexes first and reported 27 packages with newer candidates. Those candidates remain unapplied.
- The [Termux package recipe](https://github.com/termux/termux-packages/blob/master/packages/llama-cpp/build.sh) identifies the package as MIT-licensed and builds the CPU/OpenCL/Vulkan backends. The [upstream Android guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md) documents a Native Termux CLI path. This evidence does not mean Ternuxx integrates the package lifecycle.
- Model candidate: [`ggml-org/Qwen3-0.6B-GGUF`](https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF), Q4_0 file, 428,970,080 bytes, Apache-2.0 metadata, SHA-256 `da2572f16c06133561ce56accaa822216f2391ef4d37fba427801cd6736417d4`. The file was downloaded into private `$HOME/.local/share/ternuxx/models/` only after a pinned SHA-256 check. The resulting file mode is `0600`; the directory mode is `0700`.

## Bounded correctness run

`llama-cli` reports version `0.7.0` / build `b0-unknown`. The CLI inherited the Codex launcher `LD_LIBRARY_PATH`, whose bundled `libc++_shared.so` is ABI-incompatible with the Termux package and caused the same missing `_ZNSt6__ndk113__hash_memoryEPKvm` symbol. Supplying `LD_LIBRARY_PATH="$PREFIX/lib"` for this process resolved the loader failure without changing global environment or files.

Command parameters: local model file, `-ngl 0`, four CPU threads, batch threads 4, context 512, maximum 32 output tokens, seed 42, temperature 0, reasoning off, one turn. Prompt: `For this fixed CPU test, reply with exactly: NATIVE_CPU_OK`. The first run exited 0 with the exact marker, in 2.432 seconds and 550,080 KiB peak RSS. A second run was retained as [raw CLI output](data/2026-10-24-native-cpu-inference-smoke.txt), SHA-256 `49e2758f813782192a63580ea6e8af3808509adcc8f519014fe74420fde52573`; it exited 0, emitted the same exact marker in 2.115 seconds, and peaked at 550,424 KiB RSS. Its CLI-reported prompt/generation rates were 59.9 / 39.3 tokens/s. Both outputs warned that no usable GPU was found; `-ngl 0` selected no GPU layers.

## Bounded performance sample

`llama-bench` ran two repetitions with `-ngl 0`, four threads, 32 prompt tokens, 32 generated tokens, and warmup disabled. The emitted JSON records `backends: CPU`, `gpu_info: ""`, and `n_gpu_layers: 0`:

- Prompt processing: mean 52.675 tokens/s, standard deviation 0.473; samples 52.341 and 53.009 tokens/s.
- Generation: mean 36.292 tokens/s, standard deviation 0.341; samples 36.051 and 36.533 tokens/s.

Raw result: [`2026-10-24-native-cpu-baseline-qwen3-0.6b.json`](data/2026-10-24-native-cpu-baseline-qwen3-0.6b.json), SHA-256 `0028752f52c5d6d321f372e8ee3e36403ebbfa2137bc05e390d8ea0167a7e305`.

## Limits and next work

This proves one exact local CPU inference workload on one device and model with explicit CPU selection. It is not a Ternuxx-managed install/load/update workflow, a broad correctness suite, an offline-after-reboot test, or a repeated thermal/stability benchmark. The model's answer quality was not evaluated beyond the deterministic marker. No GPU or NPU inference was attempted. The model and package are device-local test inputs; no model is bundled or required by Ternuxx. Public release still needs the repository license/provenance decision and third-party notice review.
