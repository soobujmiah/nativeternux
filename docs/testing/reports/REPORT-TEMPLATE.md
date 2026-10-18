# Test report: <short title>

- Report ID:
- Generated UTC:
- Source commit:
- Release/version: `unreleased` if applicable
- Report owner/operator:
- Test type: `synthetic_ci` | `owner_operated_device`
- Verdict: `PASS` | `FAIL` | `PARTIAL` | `BLOCKED` | `UNKNOWN`
- Reproduced: yes/no; number of independent runs:

## Device and runtime

- Device model / chipset / ABI:
- Android build/API:
- Termux version and app source/signing context:
- Execution context: native Termux | Android app | Debian PRoot | other (explain)
- Display/audio state if workload requires it:
- Runtime version/commit/build flags:
- Driver/delegate/SDK versions:

## Workload and artifacts

- Workload/model ID and source:
- Model/workload SHA-256:
- License and redistribution terms:
- Quantization/precision:
- Input dataset/prompt identity (hash; avoid publishing private content):
- Requested input/output sizes and context/batch/thread settings:
- Backend requested:
- Backend observed and evidence (logs/counters):
- Fallback/partial delegation details:

## Procedure

List safe, repeatable commands and prerequisites. Clearly separate automated checks from owner-operated device steps. Record cache/warmup procedure, sample count, test duration, thermal starting state, charging/power mode, and any deviations from the benchmark methodology.

## Acceptance criteria and results

| Criterion | Expected | Observed | Status | Evidence link/hash |
|---|---|---|---|---|
| Build/runtime initialization | | | UNKNOWN | |
| Backend actually selected | | | UNKNOWN | |
| Workload completed | | | UNKNOWN | |
| Correctness | | | UNKNOWN | |
| Fallback/error handling | | | UNKNOWN | |
| Stability/resource behavior | | | UNKNOWN | |
| Release qualification | | | UNKNOWN | |

## Raw measurements

Attach the machine-readable JSON/CSV path and SHA-256. Include every run and failure; do not paste only the best result.

## Limitations and privacy review

State missing metrics, measurement uncertainty, unsupported operations, thermal/battery limits, device-context limits, privacy redactions and sources of variation. Do not infer other devices from this one.

## Review

- Reviewed by:
- Review date:
- Compatibility matrix updated:
- Feature matrix updated:
- Website/report index updated (if applicable):
