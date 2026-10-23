# Native Ternuxx shell alias migration — 2026-10-23

## Scope and preview

The owner-authorized full-repository task includes task-required Native and existing Debian integration configuration changes. A read-only preview found two Native shell aliases that logged into Debian directly and bypassed Ternuxx's validated provider/display/audio handoff. The exact target was the mode-0600 Native shell startup file; its owner, type, mode, and SHA-256 were checked before apply.

## Applied change

- The regular-user shortcut now delegates to Ternuxx's regular-user tx db path.
- The root shortcut now delegates to tx db --root.
- The existing X11 app aliases and unrelated cache-cleanup function were left as they were.
- The original file is retained in Native Ternuxx private rollback storage with mode 0600; no shell contents or backup hash are published here.

## Verification and limits

- The complete startup file passed bash -n before and after the atomic replacement.
- Both supported tx db user/root help paths passed.
- The applied file hash matched the previewed target hash; the private backup matched the recorded pre-change identity and mode.
- A disposable rollback fixture restored the exact original hash and mode.
- No PRoot login, guest package/config change, session stop, SSH change, rootfs change, or launcher edit occurred.
- Already-open shells keep their previously loaded aliases until they reload the startup file or restart.

This changes future shell invocations only. It does not alter the separate Ternux repository, its launcher, or existing guest state.
