# What I want Ternuxx to become

I want my phone to be a world-class mobile workstation I can carry in my pocket. I want to use its CPU, GPU, and NPU wherever the software actually supports them.

Ternuxx's core must work entirely from native Termux. Boot and recovery, SSH, CLI, management, and native workloads must stay usable when PRoot is stopped, missing, or broken. My existing Ternux Debian PRoot is an optional integration for Linux workloads; it must never become a prerequisite for Ternuxx itself.

Native Termux lets me run compatible tools directly and use Android or Termux features when supported. When I choose to use PRoot, it gives me Debian, XFCE, Linux applications, and the GPU/workload setup I have already built. Ternuxx can offer explicit, scoped handoffs to that optional provider, while its own boot, SSH, CLI, management, and native work continue independently. A PRoot failure must affect only an operation that I explicitly routed there.

I do not want Ternuxx to replace, trim, or break my current Ternux setup. Ternux is already useful to me, and it should stay independent.

CPU is the baseline. I have seen the PRoot GPU setup work on my device, but the docs should say when the live renderer was last checked. A driver file or shader cache alone is not enough proof. NPU support is a goal; first we need to confirm that the right runtime works on my exact device. The existing Ternux repository also contains optional CPU/Vulkan llama.cpp work and an experimental SM8735 HTP path. Ternuxx should discover and integrate proven parts of that existing work rather than rebuild them; source documentation and installed device state must remain separate evidence.

I want four ways to manage the same workstation: CLI, an interactive Terminal/TUI, Web UI, and Graphical UI. Each must call the same management service and operation contract, so validation, authorization, provider selection, state, journal, and recovery behave consistently. The interfaces are different clients, not separate management systems.

I want the documentation and compatibility research done before feature implementation. Then we can build phase by phase and update the docs as the work changes. Keep device checks read-only unless I explicitly authorize a specific change.
