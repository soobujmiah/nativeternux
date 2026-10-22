#!/usr/bin/env python3
"""Opt-in full TUI terminal replay on an installed, separately owned replay guest."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_service
import proot_fresh_setup
import proot_sessions
import terminal_broker


class ScreenDriver:
    """Render terminal updates in memory; never publish shell contents."""
    def __init__(self, fd, *, lines=40, columns=120):
        try:
            import pyte
        except ImportError as exc:
            raise RuntimeError("install optional checker dependency pyte==0.8.2") from exc
        self.fd = fd
        self.screen = pyte.Screen(columns, lines)
        self.stream = pyte.ByteStream(self.screen)
        self.revision = 0
        self.required_revision = 0
        self.byte_count = 0

    def send(self, data):
        self.required_revision = self.revision + 1
        os.write(self.fd, data)

    def resize(self, *, lines, columns):
        self.screen.resize(lines=lines, columns=columns)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
        self.required_revision = self.revision + 1

    def expect(self, text, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.revision >= self.required_revision and text in "\n".join(self.screen.display):
                return
            if select.select([self.fd], [], [], .1)[0]:
                try:
                    chunk = os.read(self.fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                self.byte_count += len(chunk)
                if self.byte_count > 2*1024*1024:
                    raise RuntimeError("TUI replay exceeded its private byte bound")
                self.stream.feed(chunk)
                self.revision += 1
        raise RuntimeError("TUI did not reach expected view: " + text)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias", required=True, help="completed ternuxx-replay-NAME target only")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.alias.startswith("ternuxx-replay-"):
        parser.error("the working Debian guest cannot be a test target")
    try:
        proot_fresh_setup._alias(args.alias)
    except ValueError as exc:
        parser.error(str(exc))
    prefix = os.environ.get("PREFIX", "")
    if prefix != "/data/data/com.termux/files/usr" or not os.environ.get("TERMUX_VERSION"):
        parser.error("Native Termux is required")
    try:
        import pyte  # noqa: F401 - opt-in checker dependency, required before process creation
    except ImportError:
        parser.error("install pyte==0.8.2 for the opt-in TUI replay checker")
    state = Path(os.environ.get("TERNUXX_STATE_DIR") or Path.home()/".local/share/ternuxx")
    receipt = proot_fresh_setup._read_private(state/"proot-setup"/f"fresh-provider-{args.alias}.json")
    if receipt.get("guest_user") != "sbj" or receipt.get("requested_packages_verified_installed") is not True:
        parser.error("the fixed terminal user and completed setup receipt are required")
    guest = proot_fresh_setup._verify_owned_target(prefix, args.alias, receipt.get("rootfs_identity"))
    working = Path(prefix)/"var/lib/proot-distro/containers/debian/rootfs"
    working_identity = (working.stat().st_dev, working.stat().st_ino)
    protected = working/"etc/profile.d/termux-profile.sh"
    protected_hash = hashlib.sha256(protected.read_bytes()).digest() if protected.is_file() else None
    private = Path(tempfile.mkdtemp(prefix="ternuxx-tui-replay-", dir=Path.home()/".local/share"))
    env = dict(os.environ, TERNUXX_STATE_DIR=str(private), TERM="xterm-256color")
    log = (private/"broker.stderr").open("w")
    (private/"broker.stderr").chmod(0o600)
    broker = subprocess.Popen([sys.executable, str(ROOT/"lib/terminal_broker_service.py"),
        "serve", "--guest-alias", args.alias], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=log)
    client = terminal_broker.UnixBrokerClient(private, timeout=30)
    clean = False
    tui_pid = master = None
    try:
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            try:
                if client.request("broker.status").get("ok"): break
            except (OSError, terminal_broker.BrokerError): pass
            time.sleep(.1)
        preview = client.request("terminal.start.preview")["plan"]
        if preview.get("alias") != args.alias or Path(preview["rootfs"]) != guest:
            raise RuntimeError("test broker selected a different guest")
        catalog = management_service.dispatch({"api_version":1,"request_id":"tui-replay-catalog",
            "operation":"management.catalog","args":{}}, env=env)["data"]
        resource = next(x for x in catalog["resources"] if x["id"] == "proot.debian.workloads")
        category_index = next(i for i,x in enumerate(catalog["categories"]) if x["id"] == resource["category_id"])
        resources = sorted([x for x in catalog["resources"] if x["category_id"] == resource["category_id"]], key=lambda x:x["name"].casefold())
        resource_index = next(i for i,x in enumerate(resources) if x["id"] == resource["id"])
        tui_pid, master = pty.fork()
        if tui_pid == 0:
            os.chdir(ROOT)
            os.execve(str(ROOT/"tx"), [str(ROOT/"tx"), "tui"], env)
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH",40,120,0,0))
        screen = ScreenDriver(master)
        screen.expect("Ternuxx")
        screen.send(b"l"*category_index+b"j"*resource_index+b"a")
        screen.expect("PRoot workloads")
        screen.send(b"3");screen.expect("Debian sessions")
        screen.send(b"4");screen.expect("Operation details")
        screen.send(b"q");screen.expect("Start the interactive Debian terminal")
        screen.send(b"yes\n")
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            sessions = proot_sessions.list_sessions(private)
            if any(x["state"]=="running" and x["ownership"]=="ternuxx_verified" for x in sessions): break
            time.sleep(.1)
        else: raise RuntimeError("TUI did not create a verified session")
        time.sleep(.2)
        token = os.urandom(8).hex()
        screen.send(("printf 'TUI_%s\\n' '"+token+"'\n").encode())
        screen.expect("TUI_"+token)
        screen.resize(lines=28, columns=95)
        time.sleep(.2)
        screen.send(b"printf 'TUI_SIZE_%s ' 'CHECK'; stty size\n")
        screen.expect("TUI_SIZE_CHECK 28 95")
        screen.send(b"\x1d");screen.expect("Ternuxx")
        screen.send(b"a");screen.expect("PRoot workloads")
        screen.send(b"3");screen.expect("Debian sessions")
        screen.send(b"5");screen.expect("Attach to a managed terminal")
        screen.send(b"1");time.sleep(.3)
        token=os.urandom(8).hex()
        screen.send(("printf 'REATTACH_%s\\n' '"+token+"'\n").encode())
        screen.expect("REATTACH_"+token)
        screen.send(b"\x1d");screen.expect("Ternuxx")
        screen.send(b"a");screen.expect("PRoot workloads")
        screen.send(b"3");screen.expect("Debian sessions")
        screen.send(b"6");screen.expect("Close a managed session")
        screen.send(b"1");screen.expect("Operation details");screen.expect("SIGHUP")
        screen.send(b"q");screen.expect("Close only the managed session")
        screen.send(b"yes\n")
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if all(x["state"]=="stopped" for x in proot_sessions.list_sessions(private)) and client.request("broker.status")["pty_relay"]=="not_connected": break
            time.sleep(.1)
        else: raise RuntimeError("TUI did not close its exact guest session")
        screen.expect("Ternuxx");screen.send(b"q")
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            waited,status=os.waitpid(tui_pid,os.WNOHANG)
            if waited:
                if os.waitstatus_to_exitcode(status)!=0:raise RuntimeError("TUI exited with failure")
                tui_pid=None;break
            time.sleep(.1)
        else: raise RuntimeError("TUI did not exit")
        if working_identity != (working.stat().st_dev, working.stat().st_ino):
            raise RuntimeError("working Debian root identity changed during replay")
        if protected_hash != (hashlib.sha256(protected.read_bytes()).digest() if protected.is_file() else None):
            raise RuntimeError("working Debian generated profile changed during replay")
        report={"schema_version":1,"target_alias":args.alias,"runtime":"Native Termux through SSH 8022",
            "full_tui_navigation":True,"preview_confirmed_start":True,"terminal_io":True,
            "guest_observed_resize":True,"detach_reattach":True,"preview_confirmed_close":True,
            "curses_navigation_restored":True,"tui_clean_exit":True,
            "working_root_identity_and_profile_preserved":True,
            "visual_pixel_or_performance_qualification":False}
        clean=True
        if args.output:args.output.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report))
        return 0
    finally:
        if clean:
            if master is not None:os.close(master)
            broker.terminate();broker.wait(timeout=10);log.close();shutil.rmtree(private)
        else:
            log.close()
            print(json.dumps({"test_state_retained":str(private),"test_broker_pid":broker.pid,"test_tui_pid":tui_pid}),file=sys.stderr)


if __name__=="__main__":
    raise SystemExit(main())
