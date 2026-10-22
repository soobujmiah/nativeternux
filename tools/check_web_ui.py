#!/usr/bin/env python3
"""Opt-in real Firefox checks for the local Web UI; never starts a guest session.

Run from Native Termux. Firefox uses an isolated shared-tmp profile in the
already-installed Debian provider. The current PRoot/Codex session is not used.
Only catalog/session inventory reads are permitted by this checker.
Marionette protocol: https://firefox-source-docs.mozilla.org/remote/marionette/Protocol.html
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
_REPLAY_DISTRO = re.compile(r"^ternuxx-replay-[A-Za-z0-9_-]{1,17}$")


def isolated_replay_distro(value: str) -> str:
    """Refuse the owner's default Debian rootfs for browser qualification."""
    if not isinstance(value, str) or not _REPLAY_DISTRO.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "must name a Ternuxx disposable alias such as ternuxx-replay-p4; the default debian guest is protected"
        )
    return value


sys.path.insert(0, str(ROOT / "lib"))
import management_http_runtime
import management_service
import management_sessions
import proot_diagnostics


class Marionette:
    def __init__(self, port: int):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.stream = self.socket.makefile("rb")
        self.sequence = 0
        hello = self.receive()
        if hello.get("marionetteProtocol") != 3:
            raise RuntimeError("unsupported Firefox automation protocol")

    def receive(self):
        prefix = bytearray()
        while True:
            char = self.stream.read(1)
            if char == b":":
                break
            if not char or not char.isdigit() or len(prefix) > 9:
                raise RuntimeError("invalid Firefox frame")
            prefix.extend(char)
        length = int(prefix)
        if not 0 < length <= 16 * 1024 * 1024:
            raise RuntimeError("oversized Firefox frame")
        chunks = bytearray()
        while len(chunks) < length:
            chunk = self.stream.read(length - len(chunks))
            if not chunk:
                raise RuntimeError("truncated Firefox frame")
            chunks.extend(chunk)
        return json.loads(chunks)

    def call(self, name, parameters=None):
        self.sequence += 1
        body = json.dumps([0, self.sequence, name, parameters or {}]).encode()
        self.socket.sendall(str(len(body)).encode() + b":" + body)
        result = self.receive()
        if len(result) != 4 or result[:2] != [1, self.sequence]:
            raise RuntimeError("unexpected Firefox response")
        if result[2]:
            # Never include script arguments, code, or credentials in errors.
            raise RuntimeError("Firefox command rejected: " + str(result[2].get("error")))
        return result[3]

    def evaluate(self, script, args=None):
        result = self.call("WebDriver:ExecuteScript", {
            "script": script, "args": args or [], "newSandbox": False,
            "sandbox": None, "line": 0, "filename": "ternuxx-ui-check"})
        return result.get("value") if isinstance(result, dict) and "value" in result else result

    def wait(self, script, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.evaluate(script):
                return
            time.sleep(0.1)
        raise AssertionError("browser condition did not become ready")

    def close(self):
        self.stream.close()
        self.socket.close()


def require(value, message):
    if not value:
        raise AssertionError(message)


def select_resource(browser, category_name, resource_name):
    result = browser.evaluate("""
      const category=[...document.querySelectorAll('#categories button')]
        .find(x=>x.textContent.includes(arguments[0]));
      if(!category)return false;
      category.click();
      const card=[...document.querySelectorAll('#resource-list .card')]
        .find(x=>x.querySelector('h3').textContent.includes(arguments[1]));
      if(!card)return false;
      card.click();
      return true;
    """, [category_name, resource_name])
    require(result, "expected category/resource is missing")


def run_checks(browser, secret, screenshots, *, visible=False):
    require(browser.evaluate(
        "return getComputedStyle(document.querySelector('#app')).display==='none'"
        " && !document.querySelector('#login').hidden"
        " && getComputedStyle(document.querySelector('#mobile-action-bar')).display==='none'"),
        "unauthenticated app or actions are visible")
    browser.evaluate("document.querySelector('#secret').value=arguments[0];"
                     "document.querySelector('#connect').click();return true;", [secret])
    browser.wait("return document.querySelector('#login').hidden"
                 " && document.querySelectorAll('#categories button').length>0")
    require(browser.evaluate("return document.querySelector('#secret').value===''"),
            "bootstrap field was not cleared after login")
    require(browser.evaluate("""
      const items=[...document.querySelectorAll('#categories button')];
      return items[0].textContent.includes('System & health')
        && items[0].getAttribute('aria-current')==='page';
    """), "initial category or current indicator is wrong")

    # Search and filters must use the selected category, not global counts.
    select_resource(browser, "Services & background", "8023")
    require(browser.evaluate("""
      const s=document.querySelector('#search');s.value='no-such-ternuxx-resource';
      s.dispatchEvent(new Event('input'));
      return document.querySelectorAll('#resource-list .card').length===0
        && !!document.querySelector('#resource-list .empty');
    """), "empty search state is missing")
    browser.evaluate("const s=document.querySelector('#search');s.value='';"
                     "s.dispatchEvent(new Event('input'));return true;")
    select_resource(browser, "Services & background", "8023")
    login_help = browser.evaluate("""
      const node=[...document.querySelectorAll('.field-note')]
        .find(x=>x.querySelector('summary')?.textContent==='SSH login help');
      return node?.textContent||'';
    """)
    require("public-key login only" in login_help and
            "password login is disabled" in login_help and
            "ssh -p 8023 termux" in login_help,
            "SSH recovery guidance does not match the verified public-key-only policy")
    report = []
    # Firefox browser chrome enforces a desktop minimum width. Remove only that
    # constraint in this disposable profile so 390 really means a 390px viewport.
    browser.call("Marionette:SetContext", {"value": "chrome"})
    browser.evaluate("document.documentElement.style.setProperty('min-width','0px','important');"
                     "document.documentElement.removeAttribute('minwidth');return true;")
    browser.call("Marionette:SetContext", {"value": "content"})
    for width in ((752,) if visible else (390, 752, 1440)):
        browser.call("WebDriver:SetWindowRect", {"width": width, "height": 1000})
        time.sleep(0.15)
        browser.evaluate("window.scrollTo(0,0);return true;")
        metrics = browser.evaluate("""
          const actions=document.querySelector('.action-dock').getBoundingClientRect();
          const nav=document.querySelector('#categories');
          const active=nav.querySelector('[aria-current="page"]');
          const navRect=nav.getBoundingClientRect();
          const activeRect=active?.getBoundingClientRect();
          return {width:innerWidth,height:innerHeight,
            overflow:document.documentElement.scrollWidth>innerWidth+1,
            activeCategoryFits:!!activeRect&&activeRect.left>=navRect.left-1
              &&activeRect.right<=navRect.right+1&&active.scrollWidth<=active.clientWidth+1,
            activeCategoryGeometry:activeRect?{left:activeRect.left,right:activeRect.right,
              width:activeRect.width,scrollWidth:active.scrollWidth,clientWidth:active.clientWidth,
              navLeft:navRect.left,navRight:navRect.right,navScrollLeft:nav.scrollLeft,
              navScrollWidth:nav.scrollWidth,navClientWidth:nav.clientWidth}:null,
            actionTop:actions.top,
            quickBar:getComputedStyle(document.querySelector('#mobile-action-bar')).display};
        """)
        metrics["requested_width"] = width
        if not visible:
            require(abs(metrics["width"] - width) <= 1,
                    "Firefox did not provide the requested viewport width " + str(width))
        else:
            require(300 <= metrics["width"] <= width,
                    "visible Firefox viewport is outside the expected window")
        require(not metrics["overflow"], "page overflows horizontally at width " + str(width))
        if metrics["width"] <= 850:
            require(metrics["activeCategoryFits"],
                    "selected category label is clipped at width " + str(width) + ": "
                    + json.dumps(metrics.get("activeCategoryGeometry"), sort_keys=True))
        require((metrics["quickBar"] != "none") == (metrics["width"] <= 850),
                "quick actions do not match the actual viewport")
        browser.evaluate("""
          document.querySelector('#resource-detail').textContent='Long details. '.repeat(1000);
          document.querySelector('#result-readable').textContent='Status line\\n'.repeat(100);
          return true;
        """)
        after = browser.evaluate(
            "return document.querySelector('.action-dock').getBoundingClientRect().top")
        require(abs(after - metrics["actionTop"]) < 1,
                "resource details moved the action list")
        report.append(metrics)
        if screenshots:
            encoded = browser.call("WebDriver:TakeScreenshot", {})
            if isinstance(encoded, dict):
                encoded = encoded["value"]
            (screenshots / ("web-" + str(width) + ".png")).write_bytes(base64.b64decode(encoded))
        select_resource(browser, "Services & background", "8023")

    # Visually inspect the exact Web PRoot session controls. This uses only the
    # read-only session inventory operation; it never starts, stops, or reconciles.
    select_resource(browser, "Debian PRoot", "Existing Debian PRoot")
    require(browser.evaluate("""
      return [...document.querySelectorAll('#resource-actions button')]
        .some(x=>x.textContent==='Preview and reconcile exited session');
    """), "Web PRoot recovery reconciliation control is missing")
    require(browser.evaluate("""
      const b=[...document.querySelectorAll('#resource-actions button')]
        .find(x=>x.textContent==='Load PRoot sessions');
      if(!b)return false;b.click();return true;
    """), "Web PRoot session inventory control is missing")
    browser.wait("return document.querySelector('#resource-actions').textContent"
                 ".includes('recorded Ternuxx sessions')")
    recovery_control = browser.evaluate("""
      const b=[...document.querySelectorAll('#resource-actions button')]
        .find(x=>x.textContent==='Preview and reconcile exited session');
      b?.scrollIntoView({block:'center',inline:'nearest'});
      const r=b?.getBoundingClientRect();
      const dock=document.querySelector('.action-dock .actions').getBoundingClientRect();
      const quick=document.querySelector('#mobile-action-bar');
      const quickTop=getComputedStyle(quick).display==='none'?innerHeight:quick.getBoundingClientRect().top;
      return {visible:!!r&&r.width>0&&r.height>0&&r.top>=dock.top&&r.bottom<=dock.bottom
          &&r.bottom<=quickTop,
        disabled:!!b?.disabled,label:b?.textContent,buttonTop:r?.top,dockTop:dock.top,
        dockBottom:dock.bottom,quickTop};
    """)
    require(recovery_control["visible"], "Web PRoot recovery control is outside the visible action area")
    if screenshots:
        encoded = browser.call("WebDriver:TakeScreenshot", {})
        if isinstance(encoded, dict):
            encoded = encoded["value"]
        (screenshots / "web-proot-reconcile-control.png").write_bytes(base64.b64decode(encoded))
    report.append({"proot_recovery_control": recovery_control})

    # A delayed response from the previous resource must not label the next one.
    select_resource(browser, "Services & background", "8023")
    browser.evaluate("""
      window.auditOriginalFetch=window.fetch;window.auditOldResponseDone=false;
      window.fetch=(url,options)=>{
        const request=JSON.parse(options.body||'{}');
        if(['ssh.inspect','native.ssh.status'].includes(request.operation)){
          return new Promise(resolve=>setTimeout(()=>{
            window.auditOldResponseDone=true;
            resolve(new Response(JSON.stringify({ok:true,data:{message:'PREVIOUS_RESOURCE_RESULT'}}),
              {status:200,headers:{'Content-Type':'application/json'}}));
          },800));
        }
        return window.auditOriginalFetch(url,options);
      };
      document.querySelector('#resource-actions [data-status-action]').click();
      return true;
    """)
    select_resource(browser, "Networking & remote access", "8022")
    browser.wait("return window.auditOldResponseDone===true")
    require(browser.evaluate("return !document.querySelector('#result-readable').textContent"
                             ".includes('PREVIOUS_RESOURCE_RESULT')"),
            "late response was attributed to a different resource")
    browser.evaluate("window.fetch=window.auditOriginalFetch;return true;")
    select_resource(browser, "Networking & remote access", "8022")
    require(browser.evaluate("""
      return [...document.querySelectorAll('#resource-actions button')]
        .every(x=>!/^stop|^start|^restart/i.test(x.textContent.trim()));
    """), "owner-managed 8022 exposes lifecycle actions")
    select_resource(browser, "Services & background", "Wake Lock")
    require(browser.evaluate(
        "return !!document.querySelector('#resource-actions [data-status-action]')"),
        "Wake Lock resource has no supported status control")
    select_resource(browser, "Debian PRoot", "Optional Debian terminal")
    browser.evaluate("""
      const b=[...document.querySelectorAll('#resource-actions button')]
        .find(x=>x.textContent==='Open Debian terminal');
      if(!b)throw Error('missing terminal control');b.click();return true;
    """)
    browser.wait("return document.querySelector('#terminal-dialog').open")
    browser.wait("return !document.querySelector('#terminal-status').textContent"
                 ".includes('Checking Ternuxx-managed')")
    require(browser.evaluate("""
      const d=document.querySelector('#terminal-dialog').getBoundingClientRect();
      return !!document.querySelector('.xterm') && d.width<=innerWidth
        && d.height<=innerHeight;
    """), "terminal renderer/dialog does not fit the viewport")
    browser.evaluate("document.querySelector('#terminal-close-dialog').click();return true;")
    browser.wait("return !document.querySelector('#terminal-dialog').open")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distro", required=True, type=isolated_replay_distro, help="Ternuxx disposable replay alias; the default Debian workload is refused")
    parser.add_argument("--visible", action="store_true", help="Use the existing Native X11 display")
    parser.add_argument("--screenshots", type=Path, help="Save scoped UI PNGs to this directory")
    args = parser.parse_args()
    if os.environ.get("PREFIX") != management_http_runtime.EXPECTED_PREFIX:
        parser.error("run this checker from Native Termux through SSH 8022")
    tmp_root = Path(os.environ.get("TMPDIR") or os.environ["PREFIX"] + "/tmp")
    if args.screenshots:
        target = args.screenshots.absolute()
        require(not target.is_symlink(), "screenshot directory is a symlink")
        require(target.is_relative_to(tmp_root) or target.is_relative_to(ROOT),
                "screenshot directory must be inside Native tmp or this checkout")
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        args.screenshots = target
    process = browser = server = None
    original_dispatch = management_service.dispatch
    operations = []
    allowed = {"management.catalog", "proot.sessions.list"}
    def dispatch(request, **kwargs):
        operation = request.get("operation")
        require(operation in allowed, "unexpected non-inventory operation")
        operations.append(operation)
        return original_dispatch(request, **kwargs)
    with tempfile.TemporaryDirectory(prefix="ternuxx-ui-check-", dir=tmp_root) as temporary:
        work = Path(temporary)
        profile = work / "profile"
        profile.mkdir(mode=0o700)
        (profile / "user.js").write_text(
            'user_pref("marionette.port", 0);\n'
            'user_pref("remote.log.level", "Info");\n'
            'user_pref("browser.shell.checkDefaultBrowser", false);\n'
            'user_pref("browser.startup.homepage_override.mstone", "ignore");\n'
            'user_pref("browser.aboutwelcome.enabled", false);\n')
        env = dict(os.environ, HOME=str(work), TERNUXX_WEB_MODE="1", TERNUXX_STATE_DIR=str(work / "state"))
        Path(env["TERNUXX_STATE_DIR"]).mkdir(mode=0o700)
        secret = management_sessions.new_bootstrap_secret()
        try:
            management_service.dispatch = dispatch
            server = management_http_runtime.build_server(port=0, bootstrap_secret=secret, env=env)
            server.start()
            guest_user = proot_diagnostics.resolve_proot_guest_user(
                distro=args.distro, prefix=env["PREFIX"])
            command = [shutil.which("proot-distro") or "proot-distro", "login", args.distro,
                       "--shared-tmp", "--user", guest_user]
            if args.visible:
                browser_env = management_http_runtime.browser_x11_environment(os.environ)
                require(bool(browser_env.get("DISPLAY")), "no verified Native display")
                command += ["--env", "DISPLAY=" + browser_env["DISPLAY"]]
            command += ["--", "firefox-esr", "-no-remote", "-profile",
                        "/tmp/" + work.name + "/profile", "--marionette", "--remote-allow-system-access"]
            if not args.visible:
                command.append("--headless")
            browser_env = {key: value for key, value in env.items() if key not in {
                "ANDROID_ART_ROOT", "ANDROID_DATA", "ANDROID_I18N_ROOT", "ANDROID_ROOT",
                "ANDROID_RUNTIME_ROOT", "ANDROID_TZDATA_ROOT", "BOOTCLASSPATH",
                "DEX2OATBOOTCLASSPATH", "EXTERNAL_STORAGE"}}
            with (work / "firefox.log").open("wb") as log:
                process = subprocess.Popen(command, env=browser_env, stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic() + 45
            port = 0
            while time.monotonic() < deadline:
                require(process.poll() is None, "isolated Firefox exited during startup")
                prefs = profile / "prefs.js"
                text = prefs.read_text() if prefs.exists() else ""
                match = re.search(r'user_pref\("marionette\.port",\s*(\d+)\)', text)
                if not match:
                    text = (work / "firefox.log").read_text(errors="replace")
                    match = re.search(r"Marionette.*Listening on port (\d+)", text)
                if match and int(match[1]) > 0:
                    port = int(match[1])
                    break
                time.sleep(0.15)
            require(port > 0, "Firefox automation listener did not become ready")
            browser = Marionette(port)
            session = browser.call("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
            caps = session.get("capabilities", {})
            require(str(caps.get("moz:profile", "")).endswith(work.name + "/profile"),
                    "Firefox profile does not match the isolated checker")
            browser.call("WebDriver:Navigate", {"url": "http://127.0.0.1:" + str(server.port) + "/"})
            metrics = run_checks(browser, secret, args.screenshots, visible=args.visible)
            print(json.dumps({"ok": True, "browser": caps.get("browserVersion"),
                              "mode": "visible" if args.visible else "headless",
                              "viewports": metrics, "operations": operations,
                              "distro": args.distro,
                              "managed_terminal_session_started": False,
                              "browser_guest_login_performed": True,
                              "guest_profile_injection_possible": True,
                              "isolated_browser_profile": True,
                              "checks": ["unauthenticated-hidden-state", "bootstrap-cleared",
                                         "catalog-order", "resource-search", "ssh-password-disabled-recovery-hint", "horizontal-overflow",
                                         "stable-actions", "late-response-resource-binding", "8022-inspection-only",
                                         "wakelock-status-control", "proot-recovery-reconcile-control",
                                         "terminal-renderer-no-guest-start"],
                              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                                for name in ["lib/management_web_ui.html",
                                                             "lib/management_http_runtime.py",
                                                             "lib/management_catalog.py"]}}, indent=2))
        finally:
            if browser:
                try:
                    browser.call("Marionette:Quit", {"flags": ["eForceQuit"]})
                except (OSError, RuntimeError, ValueError):
                    pass
                browser.close()
            if process and process.poll() is None:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=8)
            if server:
                server.close(grace_seconds=5)
            management_service.dispatch = original_dispatch
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
