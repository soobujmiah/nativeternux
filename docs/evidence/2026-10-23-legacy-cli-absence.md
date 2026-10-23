# Legacy Ternux CLI absence check — 2026-10-23

The owner-authorized migration request includes removing legacy CLI dependencies where present. The project provides exact preview-first retirement operations with private rollback for the fixed Native and Debian legacy command targets.

## Read-only result

- Native retirement preview found the fixed PREFIX command target absent.
- Debian retirement preview found the fixed guest command target absent.
- Native PATH lookup found no command named ternux.
- Bounded checks of the fixed guest command locations found no ternux executable.
- Repository source search found no separate Ternux CLI invocation in bin/, lib/, or scripts/.

The previews returned absent-target errors before creating a plan. No Native CLI files, guest files/configuration, packages, rootfs contents, or running sessions were changed. No removal or rollback operation was needed.

This check covers the fixed retired CLI locations and the command-resolution path; it does not search arbitrary user directories or the separate Ternux source repository.
