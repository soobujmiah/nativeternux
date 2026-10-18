# What I want Ternuxx to become

I want my phone to be a world-class mobile workstation I can carry in my pocket. I want to use its CPU, GPU, and NPU wherever the software actually supports them.

I need both native Termux and my existing Ternux Debian PRoot setup. They do different jobs, and I want them to work together.

Native Termux lets me run compatible tools directly and use Android or Termux features when they are supported. My PRoot setup gives me Debian, XFCE, Linux applications, and the GPU/workload setup I have already built. I want the whole workflow to connect: choose native, PRoot, or hybrid at boot; open compatible apps from either layer; pass selected files and commands between them; see where work ran; and manage its display, audio, performance, and recovery from one place. Phone-facing tasks can stay in Termux while Linux or proven GPU-heavy work runs in PRoot, with a clear handoff and without weakening either setup.

I do not want Ternuxx to replace, trim, or break my current Ternux setup. Ternux is already useful to me, and it should stay independent.

CPU is the baseline. I have seen the PRoot GPU setup work on my device, but the docs should say when the live renderer was last checked. A driver file or shader cache alone is not enough proof. NPU support is a goal; first we need to confirm that the right runtime works on my exact device.

I want the documentation and compatibility research done before feature implementation. Then we can build phase by phase and update the docs as the work changes. Keep device checks read-only unless I explicitly authorize a specific change.
