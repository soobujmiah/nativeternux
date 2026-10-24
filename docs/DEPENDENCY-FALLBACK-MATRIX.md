# Native dependency and capability fallback matrix

This matrix describes Native Termux behavior. It is a source contract; package availability and live status must be checked again when a preview or operation is requested.

| Component or capability | Readiness evidence | Missing or unknown behavior | Boundary |
|---|---|---|---|
| Native Termux:X11/XFCE | Package preview plus desktop prerequisite checks | CLI stays available; start fails with an actionable prerequisite and does not launch another runtime | Native desktop only |
| Termux:X11 Android app | Android package presence is checked separately from native commands | Unknown remains unknown; Ternuxx does not open settings or infer visible GUI state | Android UI state is separate from server readiness |
| Termux:Boot | App/package, script directory, and script count are reported separately | Unknown app state blocks enable; manual CLI start remains available | Native Termux only |
| Runit / managed Native SSH | Fixed service definition and ownership identity | Missing service manager is unavailable; no alternate daemon or broad process kill | Fixed Native service; port 8022 is separately managed |
| Native graphics | Renderer and bounded workload output | Missing tools or failed API remain unavailable; no silent backend switch | Native Bionic userspace only |
| Native audio | Exact Ternuxx-owned PulseAudio process/config | Unknown or competing ownership blocks lifecycle changes | Native service only |
| Wake Lock / Termux:API | Command availability and owner-scoped lease | Unknown lock state does not trigger an acquire/release | Android app-global state is not GUI readiness |
| NPU runtime | Native runtime visibility and workload evidence | Device files alone do not prove runtime access or execution | NPU remains unverified until a named workload passes |

## Optional dependency contract

- Keep the selected Native workload fixed when a dependency is missing. Report the failed capability; do not route it to another runtime.
- Distinguish package presence, command presence, service readiness, Android app visibility, process ownership, and workload execution.
- Preview exact package transactions and require explicit confirmation before package changes.
- Preserve CPU as the baseline. A graphics/NPU failure does not change privacy, network, cost, permissions, or execution scope.
- PRoot and Debian guest providers are outside Ternuxx's current product boundary. Earlier PRoot observations are historical evidence only.
