"""Explicit foreground runtime for the read-only loopback management API."""
from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from collections.abc import Mapping

import management_http_adapter
import management_http_server
import management_service
import management_sessions
import management_authorization


DEFAULT_PORT = 8765
ALLOWED_BOOTSTRAP_CAPABILITIES = frozenset({
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
if ALLOWED_BOOTSTRAP_CAPABILITIES & _MUTATING_CAPABILITIES:
    raise RuntimeError("read-only foreground runtime contains a mutation capability")


def build_server(*, port: int, bootstrap_secret: str,
                 env: Mapping[str, str] | None = None) -> management_http_server.LoopbackManagementServer:
    """Build a loopback-only, read-only server; this call binds but does not serve."""
    process_env = dict(os.environ if env is None else env)
    if process_env.get("PREFIX") != EXPECTED_PREFIX or not process_env.get("TERMUX_VERSION"):
        raise ValueError("management HTTP runtime requires native Termux")
    if not process_env.get("HOME"):
        raise ValueError("management HTTP runtime requires HOME")
    if not isinstance(bootstrap_secret, str) or len(bootstrap_secret) < 40:
        raise ValueError("bootstrap secret is invalid")

    def adapter_factory(bound_port: int) -> management_http_adapter.ManagementHTTPAdapter:
        return management_http_adapter.ManagementHTTPAdapter(
            expected_origin=f"http://127.0.0.1:{bound_port}",
            bootstrap_secret=bootstrap_secret,
            bootstrap_capabilities=ALLOWED_BOOTSTRAP_CAPABILITIES,
            env=process_env,
            dispatcher=management_service.dispatch,
            allow_mutations=False,
        )

    return management_http_server.LoopbackManagementServer(
        host="127.0.0.1", port=port, adapter_factory=adapter_factory)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ternuxx management http serve",
        description="Run the read-only management API on loopback in the foreground.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
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
        print("Ternuxx management API is listening on http://127.0.0.1:" + str(server.port),
              file=sys.stderr)
        print("One-time bootstrap secret (not saved; keep private): " + secret,
              file=sys.stderr)
        print("Read-only API only. Press Ctrl-C to stop.", file=sys.stderr)
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
