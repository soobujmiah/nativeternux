"""Foreground loopback API with read-only diagnostics and narrowly scoped Web actions."""
from __future__ import annotations

import argparse
import os
import signal
import shutil
import subprocess
import sys
import threading
from collections.abc import Mapping

import management_http_adapter
import management_http_server
import management_service
import management_sessions
import management_request_store
import management_authorization
import proot_diagnostics


DEFAULT_PORT = 8765
READ_CAPABILITIES = frozenset({
    "diagnostics.read",
    "guest.diagnostics.read",
    "remote_policy.read",
    "continuity.read",
})
EXPECTED_PREFIX = "/data/data/com.termux/files/usr"

_MUTATING_CAPABILITIES = {
    management_authorization.required_capability(operation)
    for operation in management_sessions.MUTATING_OPERATIONS
}
WEB_READ_CAPABILITIES = frozenset({
    "diagnostics.read", "guest.diagnostics.read", "remote_policy.read", "continuity.read",
})
WEB_CAPABILITIES = WEB_READ_CAPABILITIES | frozenset({"desktop.manage", "desktop.monitor.manage", "ssh.managed.lifecycle", "graphics.manage", "applications.launch", "applications.shortcuts.manage", "cron.manage", "proot.session.manage"})
_WEB_MUTATING_OPERATIONS = {
    operation for operation in management_sessions.MUTATING_OPERATIONS
    if management_authorization.required_capability(operation) in WEB_CAPABILITIES
    and operation != "proot.recovery.reconcile"
}
if _WEB_MUTATING_OPERATIONS != {"desktop.start", "desktop.stop", "desktop.restart", "desktop.monitor.configure", "ssh.service.start", "ssh.service.stop", "graphics.provider.select", "proot.app.launch", "proot.shortcuts.apply", "proot.start", "proot.stop", "terminal.start.preview", "terminal.start", "terminal.channel.issue", "terminal.attach", "terminal.input", "terminal.resize", "terminal.output", "terminal.detach", "terminal.close.preview", "terminal.close", "cron.jobs.mutation.preview", "cron.jobs.mutation.apply"}:
    raise RuntimeError("Web UI mutation scope must remain limited to desktop/monitor policy, managed SSH, typed graphics/app actions, previewed PRoot and terminal sessions, shortcuts, and previewed Cron job mutations")
if READ_CAPABILITIES & _MUTATING_CAPABILITIES:
    raise RuntimeError("read-only API runtime contains a mutation capability")
if WEB_READ_CAPABILITIES & _MUTATING_CAPABILITIES:
    raise RuntimeError("Web UI runtime contains a mutation capability")


def build_server(*, port: int, bootstrap_secret: str,
                 env: Mapping[str, str] | None = None) -> management_http_server.LoopbackManagementServer:
    """Build a loopback-only server; Web mode adds durable, narrowly scoped policy writes."""
    process_env = dict(os.environ if env is None else env)
    if process_env.get("PREFIX") != EXPECTED_PREFIX or not process_env.get("TERMUX_VERSION"):
        raise ValueError("management HTTP runtime requires native Termux")
    if not process_env.get("HOME"):
        raise ValueError("management HTTP runtime requires HOME")
    if not isinstance(bootstrap_secret, str) or len(bootstrap_secret) < 40:
        raise ValueError("bootstrap secret is invalid")

    web_mode = process_env.get("TERNUXX_WEB_MODE") == "1"
    if web_mode and not process_env.get("TERNUXX_STATE_DIR"):
        raise ValueError("Web UI requires the managed private state directory")
    request_store = (management_request_store.ManagementRequestStore(
        home=process_env["HOME"], state_dir=process_env["TERNUXX_STATE_DIR"]) if web_mode else None)
    def adapter_factory(bound_port: int) -> management_http_adapter.ManagementHTTPAdapter:
        return management_http_adapter.ManagementHTTPAdapter(
            expected_origin=f"http://127.0.0.1:{bound_port}",
            bootstrap_secret=bootstrap_secret,
            bootstrap_capabilities=WEB_CAPABILITIES if web_mode else READ_CAPABILITIES,
            env=process_env,
            dispatcher=management_service.dispatch,
            allow_mutations=web_mode,
            request_store=request_store,
        )

    return management_http_server.LoopbackManagementServer(
        host="127.0.0.1", port=port, adapter_factory=adapter_factory)


def copy_bootstrap_secret(secret: str, *, executable: str = "termux-clipboard-set") -> bool:
    """Send secret only to Termux clipboard stdin; never log it."""
    command = shutil.which(executable)
    if not command or not isinstance(secret, str) or not secret:
        return False
    try:
        result = subprocess.run([command], input=secret, text=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                check=False, timeout=5, close_fds=True)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0



NATIVE_BROWSER_CANDIDATES = (
    ("firefox", "Firefox"), ("firefox-esr", "Firefox ESR"),
    ("chromium", "Chromium"), ("chromium-browser", "Chromium"),
    ("brave", "Brave"), ("brave-browser", "Brave"),
    ("google-chrome", "Google Chrome"),
)
PROOT_BROWSER = ("firefox-esr", "Firefox ESR")


def detect_native_browser() -> tuple[str, str] | None:
    for executable, label in NATIVE_BROWSER_CANDIDATES:
        path = shutil.which(executable)
        if path:
            return path, label
    return None


def detect_proot_browser(env: Mapping[str, str]) -> tuple[str, str] | None:
    proot_distro = shutil.which("proot-distro")
    if not proot_distro:
        return None
    try:
        guest_user = proot_diagnostics.resolve_proot_guest_user(
            distro="debian", prefix=env.get("PREFIX", EXPECTED_PREFIX))
        result = subprocess.run(
            [proot_distro, "login", "debian", "--user", guest_user,
             "--", "sh", "-c", "command -v firefox-esr"],
            env=dict(env), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, check=False, timeout=15, close_fds=True)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    paths = result.stdout.strip().splitlines()
    if result.returncode != 0 or not paths or not paths[0].startswith("/"):
        return None
    return PROOT_BROWSER


def choose_browser(requested: str, *, native: tuple[str, str] | None,
                   proot: tuple[str, str] | None, stdin: object = sys.stdin,
                   stderr: object = sys.stderr) -> str | None:
    automatic = "native" if native else "proot" if proot else "android"
    if requested == "auto":
        return automatic
    if requested == "native":
        return "native" if native else None
    if requested == "proot":
        return "proot" if proot else None
    if requested == "android":
        return "android"
    choices = [("android", "Android default browser")]
    if native:
        choices.append(("native", "Native Termux · " + native[1]))
    if proot:
        choices.append(("proot", "Debian PRoot · " + proot[1]))
    choices.append(("auto", "Auto-select installed browser (recommended)"))
    print("\nChoose a browser for Ternuxx Web:", file=stderr)
    for index, (_value, label) in enumerate(choices, 1):
        print(f"  {index}. {label}" + (" [default]" if _value == "auto" else ""), file=stderr)
    if not getattr(stdin, "isatty", lambda: False)():
        print("Using auto-select because stdin is not interactive.", file=stderr)
        return automatic
    try:
        answer = input("Browser [auto]: ").strip().lower()
    except (EOFError, OSError):
        return automatic
    if not answer:
        return automatic
    if answer.isdigit() and 1 <= int(answer) <= len(choices):
        return choices[int(answer) - 1][0]
    aliases = {value: value for value, _label in choices}
    aliases.update({"a": "android", "n": "native", "p": "proot"})
    selected = aliases.get(answer)
    return selected if selected in {value for value, _label in choices} else None


def open_browser(browser: str, url: str, *, env: Mapping[str, str],
                 native: tuple[str, str] | None = None) -> bool:
    try:
        if browser == "native" and native:
            command = [native[0], url]
        elif browser == "proot":
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            command = [os.path.join(env.get("PREFIX", EXPECTED_PREFIX), "bin", "bash"),
                       os.path.join(root, "scripts", "proot-x11-app.sh"),
                       "--", "firefox-esr", url]
        elif browser == "android":
            opener = shutil.which("termux-open-url")
            if not opener:
                return False
            command = [opener, url]
        else:
            return False
        subprocess.Popen(command, env=dict(env), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         close_fds=True, start_new_session=True)
    except OSError:
        return False
    return True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tx mng http serve",
        description="Run the loopback management API; Web mode supports scoped management actions and the broker-backed Debian terminal.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--web", action="store_true", help="open the local browser UI")
    parser.add_argument("--browser", choices=("choose", "android", "native", "proot", "auto"),
                        default="choose", help="choose Android, installed Native/PRoot browser, or auto-select")
    parser.add_argument("--show-secret-on-clipboard-failure", action="store_true",
                        help="explicitly display the secret if clipboard copying fails")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not 1024 <= args.port <= 65535:
        print("Management HTTP port must be from 1024 to 65535.", file=sys.stderr)
        return 2
    if not sys.stderr.isatty():
        print("Refusing to start: a TTY is required to display the one-time bootstrap secret safely.",
              file=sys.stderr)
        return 2

    selected_browser = None
    native_browser = None
    if args.web:
        if args.browser in {"choose", "native", "auto"}:
            native_browser = detect_native_browser()
        proot_browser = None
        if args.browser in {"choose", "proot"} or (
                args.browser == "auto" and native_browser is None):
            proot_browser = detect_proot_browser(os.environ)
        selected_browser = choose_browser(args.browser, native=native_browser,
                                          proot=proot_browser)
        if selected_browser is None:
            print("That browser is not installed or could not be detected; choose an available browser.",
                  file=sys.stderr)
            return 2
        os.environ["TERNUXX_WEB_MODE"] = "1"
    secret = management_sessions.new_bootstrap_secret()
    try:
        server = build_server(port=args.port, bootstrap_secret=secret)
    except OSError:
        print("Could not bind the loopback management port; check for a port conflict.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Could not start management HTTP: {exc}", file=sys.stderr)
        return 1

    stopped = threading.Event()
    previous_handlers: dict[int, object] = {}

    def request_stop(_signum: int, _frame: object) -> None:
        stopped.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.signal(signum, request_stop)
    try:
        server.start()
        service_name = "Web UI" if args.web else "management API"
        print("Ternuxx " + service_name + " is listening on http://127.0.0.1:" + str(server.port),
              file=sys.stderr)
        if args.web:
            if not copy_bootstrap_secret(secret):
                if not args.show_secret_on_clipboard_failure:
                    print("Clipboard copy failed; server stopped without revealing the secret. "
                          "Retry with --show-secret-on-clipboard-failure for an explicit terminal fallback.",
                          file=sys.stderr)
                    return 1
                print("Clipboard copy failed. Explicit terminal fallback; keep this output private.", file=sys.stderr)
                print("One-time bootstrap secret: " + secret, file=sys.stderr)
            else:
                print("One-time bootstrap secret copied to the Termux clipboard.", file=sys.stderr)
        else:
            print("One-time bootstrap secret (not saved; keep private): " + secret, file=sys.stderr)
        runtime_label = "Management Web UI" if args.web else "Read-only management API"
        print(runtime_label + ". Press Ctrl-C to stop.", file=sys.stderr)
        if args.web:
            url = "http://127.0.0.1:" + str(server.port) + "/"
            if open_browser(selected_browser, url, env=os.environ,
                            native=native_browser):
                labels = {"android": "Android default browser", "native": "Native Termux browser",
                          "proot": "Debian PRoot Firefox ESR"}
                print("Opened " + labels[selected_browser] + " at " + url, file=sys.stderr)
            else:
                print("Could not launch the selected browser. Open this URL manually: " + url,
                      file=sys.stderr)
        stopped.wait()
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        if not server.close(grace_seconds=5):
            print("Management HTTP stopped accepting clients; an operation is still finishing.",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
