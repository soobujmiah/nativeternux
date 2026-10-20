# Native Hermes provider boundary

Status: implemented for read-only scheduler status inspection only.

## Verified local installation

On 2026-10-19, Native Termux resolved `hermes` and `hermes-agent` under the active Termux prefix. The installed package reports Hermes Agent `v0.22.0+canary.20261014T070054Z (2026.9.24)`. The private `$HOME/.hermes` directory is mode 0700 and contains a `cron` directory; the installed Hermes CLI documents `cron status` and `cron list` as inspection commands. This integration invokes only `hermes --version` and `hermes cron status`, with bounded timeouts.

Read-only live results reported: default profile; no scheduled jobs; no scheduler serving that profile. No jobs, task history, configuration values, credentials, or Hermes history were read by Ternuxx. No Hermes task was run, and no gateway, schedule, or provider configuration was changed.

## Ternuxx contract

`agent.hermes.status` is a typed API-v1 operation requiring only `diagnostics.read`. `tx mng hermes status` is its CLI entrypoint. The operation returns normalized availability, version, scheduler state/health/profile, checked time, and a stable error code; it never returns raw Hermes output. Scheduler state is `running` only when the installed status output explicitly reports the successful ticker state, `not_running` when Hermes explicitly reports no scheduler for the profile, and `unknown` for every other output or timeout.

The catalog lists Hermes as an optional external provider. Its scheduler remains independent (`management_mode=disconnected`); Ternuxx does not adopt its registry or scheduler. Listing task details, validating or previewing a task, execution, cancellation, history/log reading, configuration changes, and schedule bridging remain unsupported/planned. Do not infer that Hermes status being readable means Cron is operational.

## Ternuxx Cron status

The Ternuxx typed registry and deterministic schedule preview now exist; see [Cron Jobs](CRON-JOBS.md). Its scheduler, execution ledger, boot/recovery event delivery, and watchdog remain unavailable. Hermes remains disconnected; no task was created, enabled, or run, and its configuration was not changed.

## Safety boundary

The adapter resolves the Native Termux executable under `$PREFIX`, passes an argument vector (no shell), supplies a minimal environment, bounds version/status probes, and discards command output except for strict status markers and the version token. It does not read or return task/configuration content, invoke `cron list`, or expose Hermes commands as arbitrary shell execution. If the CLI output changes, status becomes `unknown` until the adapter is reviewed.
