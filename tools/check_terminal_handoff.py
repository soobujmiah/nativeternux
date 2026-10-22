#!/usr/bin/env python3
"""Live CLI-to-Web-to-TUI terminal handoff against the receipt-verified replay guest.

Creates one private broker and one managed session, starts it through the real
CLI, detaches, attaches through the real TUI, and confirms that the same live
session remains visible to Web/GTK shared-service inventory paths. It then
closes that exact session through a fresh broker preview and confirmation.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import shlex
import sys
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tools"))

import management_http_runtime
import management_service
import management_sessions
import proot_fresh_setup
import proot_sessions
import terminal_broker
from check_tui_terminal import ScreenDriver

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def _wait_child(pid: int, timeout: float = 8) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        waited, status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return os.waitstatus_to_exitcode(status)
        time.sleep(0.05)
    raise RuntimeError("terminal client did not exit after detach")

def _verified_session(state: Path, guest: Path) -> dict[str, object]:
    matches = [item for item in proot_sessions.list_sessions(state)
               if item.get("profile") == "debian-interactive"
               and Path(str(item.get("rootfs", ""))) == guest
               and item.get("state") == "running"
               and item.get("ownership") == "ternuxx_verified"]
    require(len(matches) == 1, "expected exactly one verified session on the replay root")
    return matches[0]

def _close_exact(client: terminal_broker.UnixBrokerClient, session_id: str) -> None:
    lease = client.request("terminal.attach", session_id=session_id)
    require(lease.get("ok") is True, "could not acquire exact test-session attachment")
    generation = lease["generation"]
    attachment = lease["attachment_id"]
    preview = client.request("terminal.close.preview", session_id=session_id,
                             generation=generation, attachment_id=attachment)
    plan = preview.get("plan", {})
    require(preview.get("ok") is True and isinstance(plan.get("plan_id"), str),
            "exact test-session close preview failed")
    result = client.request("terminal.close", session_id=session_id,
        generation=generation, attachment_id=attachment,
        args={"confirmed": True, "plan_id": plan["plan_id"]})
    require(result.get("ok") is True and result.get("result", {}).get("state") == "stopped",
            "exact test session did not reach stopped state")
    try:
        client.request("terminal.detach", session_id=session_id,
                       generation=generation, attachment_id=attachment)
    except terminal_broker.BrokerError:
        pass

def _web_request(server, bearer: str, csrf: str, path: str,
                 payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    host = f"127.0.0.1:{server.port}"
    headers = {"Host": host, "Origin": "http://" + host,
               "Content-Type": "application/json", "Content-Length": str(len(body))}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    if csrf:
        headers["X-Ternuxx-CSRF"] = csrf
    status, _headers, response_body = server.adapter.handle(
        method="POST", path=path, headers=headers, body=body)
    result = json.loads(response_body)
    require(status == 200 and result.get("ok") is True,
            "authenticated Web operation failed: " + str(result.get("error", "unknown")))
    return result

def _web_terminal_handoff(env: dict[str, str], session_id: str) -> None:
    web_env = dict(env, TERNUXX_WEB_MODE="1")
    secret = management_sessions.new_bootstrap_secret()
    server = management_http_runtime.build_server(
        port=0, bootstrap_secret=secret, env=web_env)
    server.start()
    bearer = csrf = ""
    lease = None
    detached = False
    try:
        login = _web_request(server, "", "", "/api/v1/session", {
            "bootstrap_secret": secret,
            "capabilities": sorted(management_http_runtime.WEB_CAPABILITIES)})
        bearer = login["session"]["bearer_token"]
        csrf = login["session"]["csrf_token"]
        inventory = _web_request(server, bearer, csrf, "/api/v1/operations", {
            "api_version": 1, "request_id": "handoff-web-read-0001",
            "operation": "proot.sessions.list", "args": {}})
        require(any(item.get("session_id") == session_id
                    and item.get("state") == "running"
                    and item.get("ownership") == "ternuxx_verified"
                    for item in inventory.get("data", {}).get("sessions", [])),
                "authenticated Web inventory did not see the CLI session")

        base = {"session_id": session_id, "generation": None,
                "attachment_id": None, "channel_ticket": None, "args": {}}
        issue = _web_request(server, bearer, csrf, "/api/v1/terminal", {
            **base, "operation": "terminal.channel.issue",
            "request_id": "handoff-web-ticket-001"})
        ticket = issue["data"]["channel_ticket"]
        attach = _web_request(server, bearer, csrf, "/api/v1/terminal", {
            **base, "operation": "terminal.attach", "channel_ticket": ticket,
            "request_id": "handoff-web-attach-001"})
        lease = attach["data"]
        generation = lease["generation"]
        attachment = lease["attachment_id"]
        current = {"session_id": session_id, "generation": generation,
                   "attachment_id": attachment, "channel_ticket": None}
        resize = _web_request(server, bearer, csrf, "/api/v1/terminal", {
            **current, "operation": "terminal.resize",
            "request_id": "handoff-web-resize-001",
            "args": {"columns": 83, "rows": 25}})
        require(resize["data"].get("columns") == 83 and resize["data"].get("rows") == 25,
                "Web resize response did not confirm the replay session geometry")

        marker = "WEB_HANDOFF_" + os.urandom(8).hex()
        encoded = base64.b64encode(marker.encode()).decode()
        command = "printf " + shlex.quote("%s\n") + ' "$(printf %s ' + encoded + ' | base64 -d)"'
        _web_request(server, bearer, csrf, "/api/v1/terminal", {
            **current, "operation": "terminal.input",
            "request_id": "handoff-web-input-001",
            "args": {"data_base64": base64.b64encode((command + "\n").encode()).decode()}})
        sequence = 0
        output = ""
        deadline = time.monotonic() + 8
        poll = 0
        while time.monotonic() < deadline and marker not in output:
            poll += 1
            response = _web_request(server, bearer, csrf, "/api/v1/terminal", {
                **current, "operation": "terminal.output",
                "request_id": f"handoff-web-output-{poll:03d}",
                "args": {"after_sequence": sequence}})
            data = response["data"]
            for chunk in data.get("chunks", []):
                output += base64.b64decode(chunk["data_base64"], validate=True).decode(
                    "utf-8", errors="replace")
                sequence = max(sequence, int(chunk["sequence"]))
            time.sleep(0.05)
        require(marker in output, "Web terminal did not receive the unique guest output marker")
        _web_request(server, bearer, csrf, "/api/v1/terminal", {
            **current, "operation": "terminal.detach",
            "request_id": "handoff-web-detach-001", "args": {}})
        detached = True
    finally:
        if lease is not None and not detached and bearer and csrf:
            try:
                _web_request(server, bearer, csrf, "/api/v1/terminal", {
                    "session_id": session_id, "generation": lease["generation"],
                    "attachment_id": lease["attachment_id"], "channel_ticket": None,
                    "operation": "terminal.detach",
                    "request_id": "handoff-web-cleanup-01", "args": {}})
            except Exception:
                pass
        server.close(grace_seconds=2)

def _marker_command(marker: str) -> str:
    encoded = base64.b64encode(marker.encode()).decode()
    return "printf " + shlex.quote("%s\n") + ' "$(printf %s ' + encoded + ' | base64 -d)"'

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias", required=True,
                        help="exact receipt-verified ternuxx-replay-NAME target")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"ternuxx-replay-[A-Za-z0-9][A-Za-z0-9_-]{0,47}", args.alias):
        parser.error("alias must be a simple ternuxx-replay-NAME identifier")
    prefix = os.environ.get("PREFIX", "")
    if prefix != "/data/data/com.termux/files/usr" or not os.environ.get("TERMUX_VERSION"):
        parser.error("Native Termux is required")
    state_root = Path.home() / ".local/share/ternuxx"
    receipt = proot_fresh_setup._read_private(
        state_root / "proot-setup" / f"fresh-provider-{args.alias}.json")
    require(receipt.get("guest_user") == "sbj"
            and receipt.get("requested_packages_verified_installed") is True,
            "completed separate-guest setup receipt is required")
    guest = proot_fresh_setup._verify_owned_target(
        prefix, args.alias, receipt.get("rootfs_identity"))
    working_root = Path(prefix) / "var/lib/proot-distro/containers/debian/rootfs"
    working_identity = (working_root.stat().st_dev, working_root.stat().st_ino)
    protected = working_root / "etc/profile.d/termux-profile.sh"
    protected_hash = hashlib.sha256(protected.read_bytes()).hexdigest() if protected.is_file() else None

    private = Path(tempfile.mkdtemp(prefix="ternuxx-handoff-", dir=Path.home() / ".local/share"))
    private.chmod(0o700)
    env = dict(os.environ, TERNUXX_STATE_DIR=str(private), TERM="xterm-256color")
    log_path = private / "broker.stderr"
    log = log_path.open("w", encoding="utf-8")
    log_path.chmod(0o600)
    broker = subprocess.Popen([sys.executable, str(ROOT / "lib/terminal_broker_service.py"),
        "serve", "--guest-alias", args.alias], cwd=ROOT, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log,
        start_new_session=True)
    client = terminal_broker.UnixBrokerClient(private, timeout=30)
    cli_pid = tui_pid = None
    cli_master = tui_master = None
    session_id = None
    passed = False
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                if client.request("broker.status").get("ok"):
                    break
            except (OSError, terminal_broker.BrokerError):
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("private replay broker did not become ready")

        preview = client.request("terminal.start.preview")["plan"]
        require(preview.get("alias") == args.alias and Path(preview.get("rootfs", "")) == guest,
                "broker preview selected a target other than the verified replay guest")

        cli_pid, cli_master = pty.fork()
        if cli_pid == 0:
            os.chdir(ROOT)
            os.execve(str(ROOT / "tx"), [str(ROOT / "tx"), "terminal", "start"], env)
        fcntl.ioctl(cli_master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
        cli = ScreenDriver(cli_master)
        cli.expect("Start this fixed Debian login?")
        cli.send(b"y\n")
        marker = "CLI_HANDOFF_" + os.urandom(8).hex()
        cli.send((_marker_command(marker) + "\n").encode())
        cli.expect(marker)
        cli.resize(lines=27, columns=91)
        cli.send(b"printf 'CLI_HANDOFF_SIZE '; stty size\n")
        cli.expect("CLI_HANDOFF_SIZE 27 91")
        cli.send(b"\x1d")
        require(_wait_child(cli_pid) == 0, "CLI did not detach cleanly")
        cli_pid = None
        os.close(cli_master)
        cli_master = None

        session = _verified_session(private, guest)
        session_id = str(session["session_id"])
        _web_terminal_handoff(env, session_id)
        catalog_result = management_service.dispatch({
            "api_version": 1, "request_id": "handoff-shared-catalog",
            "operation": "management.catalog", "args": {},
        }, env=env)
        require(catalog_result.get("ok") is True, "shared Web/GTK catalog query failed")

        api_sessions = management_service.dispatch({
            "api_version": 1, "request_id": "handoff-web-session-list",
            "operation": "proot.sessions.list", "args": {},
        }, env=env)
        visible = api_sessions.get("data", {}).get("sessions", [])
        require(api_sessions.get("ok") is True and any(
            item.get("session_id") == session_id and item.get("state") == "running"
            and item.get("ownership") == "ternuxx_verified" for item in visible),
            "shared Web session-inventory operation did not expose the same verified session")

        bridge = subprocess.run([sys.executable, str(ROOT / "scripts/management_desktop_bridge.py"),
            "terminal-session-options"], cwd=ROOT, env=env, capture_output=True,
            text=True, timeout=15, check=False)
        require(bridge.returncode == 0 and session_id in bridge.stdout,
                "GTK terminal picker data source did not expose the same session")

        catalog = catalog_result["data"]
        resource = next(item for item in catalog["resources"]
                        if item["id"] == "proot.debian.workloads")
        category_index = next(i for i, item in enumerate(catalog["categories"])
                              if item["id"] == resource["category_id"])
        resources = sorted([item for item in catalog["resources"]
                            if item["category_id"] == resource["category_id"]],
                           key=lambda item: item["name"].casefold())
        resource_index = next(i for i, item in enumerate(resources)
                              if item["id"] == resource["id"])
        tui_pid, tui_master = pty.fork()
        if tui_pid == 0:
            os.chdir(ROOT)
            os.execve(str(ROOT / "tx"), [str(ROOT / "tx"), "tui"], env)
        fcntl.ioctl(tui_master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
        tui = ScreenDriver(tui_master)
        tui.expect("Ternuxx")
        tui.send(b"l" * category_index + b"j" * resource_index + b"a")
        tui.expect("PRoot workloads")
        tui.send(b"3")
        tui.expect("Debian sessions")
        tui.send(b"5")
        tui.expect("Attach to a managed terminal")
        tui.send(b"1")
        marker = "TUI_HANDOFF_" + os.urandom(8).hex()
        tui.send((_marker_command(marker) + "\n").encode())
        tui.expect(marker)
        tui.resize(lines=23, columns=77)
        tui.send(b"printf 'TUI_HANDOFF_SIZE '; stty size\n")
        tui.expect("TUI_HANDOFF_SIZE 23 77")
        tui.send(b"\x1d")
        tui.expect("Ternuxx")
        tui.send(b"q")
        require(_wait_child(tui_pid) == 0, "TUI did not detach and exit cleanly")
        tui_pid = None
        os.close(tui_master)
        tui_master = None

        session_after = _verified_session(private, guest)
        require(session_after.get("session_id") == session_id,
                "TUI handoff changed the managed session identity")
        _close_exact(client, session_id)
        session_records = proot_sessions.list_sessions(private)
        stopped = next((item for item in session_records if item.get("session_id") == session_id), None)
        require(stopped is not None and stopped.get("state") == "stopped"
                and stopped.get("ownership") == "released",
                "test session was not recorded as stopped and released")
        require(client.request("broker.status").get("pty_relay") == "not_connected",
                "private broker retained a PTY after exact close")
        require((working_root.stat().st_dev, working_root.stat().st_ino) == working_identity,
                "protected default Debian root identity changed")
        after_hash = hashlib.sha256(protected.read_bytes()).hexdigest() if protected.is_file() else None
        require(after_hash == protected_hash, "protected default Debian profile hash changed")
        passed = True
        print(json.dumps({"status": "PASS", "alias": args.alias,
            "rootfs_identity_verified": True, "same_session_id": session_id,
            "client_handoff": ["CLI start/I-O/resize/detach",
                "authenticated Web attach/I-O/resize/detach",
                "TUI attach/I-O/resize/detach"],
            "shared_inventory": ["GTK picker bridge"],
            "exact_close": "stopped and released", "default_debian_preserved": True,
            "private_broker_state_removed": True}, sort_keys=True))
        return 0
    finally:
        if cli_master is not None:
            try:
                os.close(cli_master)
            except OSError:
                pass
        if tui_master is not None:
            try:
                os.close(tui_master)
            except OSError:
                pass
        for child_pid in (cli_pid, tui_pid):
            if child_pid is None:
                continue
            try:
                os.kill(child_pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            try:
                _wait_child(child_pid, timeout=3)
            except (ChildProcessError, RuntimeError):
                pass
        if passed:
            broker.terminate()
            try:
                broker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                broker.kill()
                broker.wait(timeout=3)
            log.close()
            shutil.rmtree(private)
        else:
            log.close()
            print(json.dumps({"status": "RETAINED_FOR_RECOVERY",
                "state_dir": str(private), "broker_pid": broker.pid,
                "session_id": session_id}, sort_keys=True), file=sys.stderr)

if __name__ == "__main__":
    raise SystemExit(main())
