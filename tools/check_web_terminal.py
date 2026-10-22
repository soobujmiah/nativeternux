#!/usr/bin/env python3
"""Opt-in real Web terminal lifecycle on the separately owned replay guest."""
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
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tools"))
from check_web_ui import Marionette, require, select_resource
import management_http_runtime
import management_sessions
import proot_fresh_setup
import proot_sessions
import terminal_broker

def wait_for(browser, script, *, timeout=20):
    browser.wait(script, timeout=timeout)

def terminal_contains(browser, token):
    return browser.evaluate("return window.replayOutput?.includes(arguments[0])===true",[token])

def send_terminal_keys(browser, value):
    actions=[]
    for char in value:
        key="\ue007" if char=="\n" else char
        actions.extend(({"type":"keyDown","value":key},{"type":"keyUp","value":key}))
    browser.call("WebDriver:PerformActions",{"actions":[{"type":"key","id":"replay-keyboard",
        "actions":actions}]})

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--screenshot", type=Path,
                        help="Optional private PNG inside Native Termux tmp")
    args=parser.parse_args(argv)
    if not args.alias.startswith("ternuxx-replay-"):
        parser.error("the working Debian guest cannot be a Web replay target")
    try:
        proot_fresh_setup._alias(args.alias)
    except ValueError as exc:
        parser.error(str(exc))
    prefix=os.environ.get("PREFIX","")
    if prefix!=management_http_runtime.EXPECTED_PREFIX or not os.environ.get("TERMUX_VERSION"):
        parser.error("Native Termux is required")
    if args.screenshot:
        target=args.screenshot.absolute()
        if target.is_symlink() or not target.is_relative_to(Path(prefix)/"tmp"):
            parser.error("screenshot target must be a regular path inside Native tmp")
        args.screenshot=target
    state=Path(os.environ.get("TERNUXX_STATE_DIR") or Path.home()/".local/share/ternuxx")
    receipt=proot_fresh_setup._read_private(state/"proot-setup"/f"fresh-provider-{args.alias}.json")
    if receipt.get("guest_user")!="sbj" or receipt.get("requested_packages_verified_installed") is not True:
        parser.error("completed separate-guest setup receipt is required")
    guest=proot_fresh_setup._verify_owned_target(prefix,args.alias,receipt.get("rootfs_identity"))
    browser_binary=guest/"usr/bin/firefox-esr"
    if not browser_binary.exists():
        parser.error("Firefox ESR is not installed in replay guest")
    working=Path(prefix)/"var/lib/proot-distro/containers/debian/rootfs"
    working_identity=(working.stat().st_dev,working.stat().st_ino)
    protected=working/"etc/profile.d/termux-profile.sh"
    protected_hash=hashlib.sha256(protected.read_bytes()).digest() if protected.is_file() else None
    private=Path(tempfile.mkdtemp(prefix="ternuxx-web-terminal-",dir=Path.home()/".local/share"))
    scratch=Path(tempfile.mkdtemp(prefix="ternuxx-web-terminal-",dir=Path(prefix)/"tmp"))
    profile=scratch/"profile"
    profile.mkdir(mode=0o700)
    (profile/"user.js").write_text(
        'user_pref("marionette.port", 0);\n'
        'user_pref("remote.log.level", "Info");\n'
        'user_pref("browser.shell.checkDefaultBrowser", false);\n'
        'user_pref("browser.startup.homepage_override.mstone", "ignore");\n'
        'user_pref("browser.aboutwelcome.enabled", false);\n')
    env=dict(os.environ,TERNUXX_STATE_DIR=str(private),TERNUXX_WEB_MODE="1",TERM="xterm-256color")
    broker_log=(private/"broker.stderr").open("w")
    (private/"broker.stderr").chmod(0o600)
    browser_log=(scratch/"firefox.log").open("wb")
    (scratch/"firefox.log").chmod(0o600)
    broker=subprocess.Popen([sys.executable,str(ROOT/"lib/terminal_broker_service.py"),"serve",
                             "--guest-alias",args.alias],cwd=ROOT,env=env,
                            stdout=subprocess.DEVNULL,stderr=broker_log)
    client=terminal_broker.UnixBrokerClient(private,timeout=30)
    server=process=browser=None
    clean=False
    try:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:
                if client.request("broker.status").get("ok"): break
            except (OSError,terminal_broker.BrokerError): pass
            time.sleep(.1)
        preview=client.request("terminal.start.preview")["plan"]
        if preview.get("alias")!=args.alias or Path(preview["rootfs"])!=guest:
            raise RuntimeError("Web replay broker selected a different guest")
        secret=management_sessions.new_bootstrap_secret()
        server=management_http_runtime.build_server(port=0,bootstrap_secret=secret,env=env)
        server.start()
        terminal_trace=[]
        original_terminal_dispatch=server.adapter._terminal_dispatch
        def traced_terminal_dispatch(headers,payload,session_ref):
            response=original_terminal_dispatch(headers,payload,session_ref)
            try:code=json.loads(response[2]).get("error")
            except (ValueError,TypeError):code=None
            dimensions=(payload.get("args") if payload.get("operation")=="terminal.resize" else None)
            terminal_trace.append((payload.get("operation"),response[0],code,dimensions))
            return response
        server.adapter._terminal_dispatch=traced_terminal_dispatch
        command=[shutil.which("proot-distro") or "proot-distro","login",args.alias,
                 "--shared-tmp","--user","sbj","--","firefox-esr","-no-remote",
                 "-profile","/tmp/"+scratch.name+"/profile","--marionette",
                 "--remote-allow-system-access","--headless"]
        browser_env={k:v for k,v in env.items() if k not in {
            "ANDROID_ART_ROOT","ANDROID_DATA","ANDROID_I18N_ROOT","ANDROID_ROOT",
            "ANDROID_RUNTIME_ROOT","ANDROID_TZDATA_ROOT","BOOTCLASSPATH",
            "DEX2OATBOOTCLASSPATH","EXTERNAL_STORAGE"}}
        process=subprocess.Popen(command,env=browser_env,stdin=subprocess.DEVNULL,
                                 stdout=browser_log,stderr=browser_log,start_new_session=True)
        deadline=time.monotonic()+60
        port=0
        while time.monotonic()<deadline:
            require(process.poll() is None,"separate-guest Firefox exited during startup")
            prefs=profile/"prefs.js"
            output=prefs.read_text() if prefs.exists() else ""
            match=re.search(r'user_pref\("marionette\.port",\s*(\d+)\)',output)
            if not match:
                output=(scratch/"firefox.log").read_text(errors="replace")
                match=re.search(r"Marionette.*Listening on port (\d+)",output)
            if match and int(match[1])>0:
                port=int(match[1]);break
            time.sleep(.15)
        require(port>0,"separate-guest Firefox automation listener unavailable")
        browser=Marionette(port)
        session=browser.call("WebDriver:NewSession",{"capabilities":{"alwaysMatch":{}}})
        caps=session.get("capabilities",{})
        require(str(caps.get("moz:profile","")).endswith(scratch.name+"/profile"),
                "Firefox profile does not match replay scratch")
        browser.call("WebDriver:Navigate",{"url":f"http://127.0.0.1:{server.port}/"})
        browser.evaluate("document.querySelector('#secret').value=arguments[0];"
                         "document.querySelector('#connect').click();return true;",[secret])
        wait_for(browser,"return document.querySelector('#login').hidden && "
                 "document.querySelectorAll('#categories button').length>0")
        select_resource(browser,"Debian PRoot","Optional Debian terminal")
        browser.evaluate("""
          const b=[...document.querySelectorAll('#resource-actions button')]
             .find(x=>x.textContent==='Open Debian terminal');
          if(!b)throw Error('terminal control missing');b.click();return true;
        """)
        wait_for(browser,"return document.querySelector('#terminal-dialog').open")
        wait_for(browser,"return !document.querySelector('#terminal-status').textContent"
                 ".includes('Checking Ternuxx-managed')")
        browser.evaluate("""
          window.replayPrompts=[];
          window.confirm=(message)=>{window.replayPrompts.push(message);return true};
          window.replayOutput="";
          window.replayFetch=window.fetch;
          window.fetch=async (...request)=>{
            const response=await window.replayFetch(...request);
            if(String(request[0]).endsWith('/api/v1/terminal')){
              let operation="";
              try{operation=JSON.parse(request[1]?.body||'{}').operation}catch{}
              if(operation==='terminal.output'){
                try{
                  const result=await response.clone().json();
                  for(const chunk of result.data?.chunks||[]){
                    const bytes=Uint8Array.from(atob(chunk.data_base64),c=>c.charCodeAt(0));
                    window.replayOutput=(window.replayOutput+new TextDecoder().decode(bytes)).slice(-100000);
                  }
                }catch{}
              }
            }
            return response;
          };
          return true;
        """)
        browser.evaluate("document.querySelector('#terminal-start-session').click();return true;")
        try:
            wait_for(browser,"return document.querySelector('#terminal-status').textContent"
                     ".includes('Connected to managed Debian terminal')",timeout=7)
        except AssertionError as exc:
            status=browser.evaluate("return document.querySelector('#terminal-status').textContent")
            raise RuntimeError("Web terminal start/attach status: "+str(status)[:100]
                +"; adapter="+json.dumps({"tickets":len(server.adapter._terminal_tickets),
                    "attachments":len(server.adapter._terminal_attachments)},sort_keys=True)
                +"; operations="+json.dumps(terminal_trace)) from exc
        prompts=browser.evaluate("return window.replayPrompts")
        require(len(prompts)==1 and args.alias in prompts[0],
                "Web start confirmation does not identify the exact replay target")
        sessions=proot_sessions.list_sessions(private)
        require(len(sessions)==1 and sessions[0]["ownership"]=="ternuxx_verified"
                and sessions[0]["state"]=="running"
                and sessions[0]["rootfs"]==str(guest),"Web start did not own exact guest")
        token=os.urandom(8).hex()
        command=f"printf 'WEB_%s\\n' '{token}'\n"
        send_terminal_keys(browser,command)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline and not terminal_contains(browser,"WEB_"+token):
            time.sleep(.1)
        require(terminal_contains(browser,"WEB_"+token),"Web terminal returned no guest marker")
        first_resize=next((item[3] for item in reversed(terminal_trace)
                           if item[0]=="terminal.resize" and item[1]==200),None)
        require(first_resize,"Web attach sent no accepted terminal resize")
        browser.call("WebDriver:SetWindowRect",{"width":940,"height":640})
        deadline=time.monotonic()+10
        changed=None
        while time.monotonic()<deadline:
            changed=next((item[3] for item in reversed(terminal_trace)
                          if item[0]=="terminal.resize" and item[1]==200
                          and item[3]!=first_resize),None)
            if changed:break
            time.sleep(.1)
        require(changed,"Web viewport change sent no new terminal size")
        send_terminal_keys(browser,"printf 'WEB_SIZE_%s ' 'CHECK'; stty size\n")
        size_script=r"""
          const match=(window.replayOutput||"").match(/WEB_SIZE_CHECK\s+(\d+)\s+(\d+)/);
          return match?[Number(match[1]),Number(match[2])]:null;
        """
        deadline=time.monotonic()+15
        observed_size=None
        while time.monotonic()<deadline:
            observed_size=browser.evaluate(size_script)
            if observed_size:break
            time.sleep(.1)
        require(observed_size,"guest size marker did not reach Web terminal")
        latest_resize=next((item[3] for item in reversed(terminal_trace)
                            if item[0]=="terminal.resize" and item[1]==200),None)
        if observed_size!=[latest_resize["rows"],latest_resize["columns"]]:
            raise RuntimeError("guest size differs from Web resize: "+str(observed_size)
                +" vs "+str([latest_resize["rows"],latest_resize["columns"]]))
        if args.screenshot:
            encoded=browser.call("WebDriver:TakeScreenshot",{})
            if isinstance(encoded,dict):encoded=encoded.get("value")
            args.screenshot.write_bytes(base64.b64decode(encoded))
        browser.evaluate("document.querySelector('#terminal-close-dialog').click();return true;")
        wait_for(browser,"return !document.querySelector('#terminal-dialog').open")
        require(proot_sessions.list_sessions(private)[0]["state"]=="running",
                "Web detach closed guest")
        browser.evaluate("""
          const b=[...document.querySelectorAll('#resource-actions button')]
             .find(x=>x.textContent==='Open Debian terminal');b.click();return true;
        """)
        wait_for(browser,"return document.querySelector('#terminal-dialog').open")
        wait_for(browser,"return document.querySelector('#terminal-session').options.length>1")
        browser.evaluate("const s=document.querySelector('#terminal-session');s.selectedIndex=1;"
                         "document.querySelector('#terminal-attach-session').click();return true;")
        wait_for(browser,"return document.querySelector('#terminal-status').textContent"
                 ".includes('Connected to managed Debian terminal')")
        token=os.urandom(8).hex()
        send_terminal_keys(browser,f"printf 'WEB_REATTACH_%s\\n' '{token}'\n")
        deadline=time.monotonic()+15
        while time.monotonic()<deadline and not terminal_contains(browser,"WEB_REATTACH_"+token):
            time.sleep(.1)
        require(terminal_contains(browser,"WEB_REATTACH_"+token),"Web reattach returned no guest marker")
        browser.evaluate("document.querySelector('#terminal-stop-session').click();return true;")
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if proot_sessions.list_sessions(private)[0]["state"]=="stopped":break
            time.sleep(.1)
        else:raise RuntimeError("Web close did not stop exact guest session")
        prompts=browser.evaluate("return window.replayPrompts")
        require(len(prompts)==2 and "SIGHUP" in prompts[1],
                "Web close confirmation omits the exact graceful signal")
        require(client.request("broker.status")["pty_relay"]=="not_connected",
                "Web broker retained terminal after close")
        if working_identity!=(working.stat().st_dev,working.stat().st_ino):
            raise RuntimeError("working Debian root identity changed")
        if protected_hash!=(hashlib.sha256(protected.read_bytes()).digest() if protected.is_file() else None):
            raise RuntimeError("working Debian generated profile changed")
        report={"schema_version":1,"runtime":"Native Termux through SSH 8022",
                "browser_guest_alias":args.alias,"managed_guest_alias":args.alias,
                "web_preview_confirmed_start":True,"terminal_io":True,
                "guest_observed_resize":True,"detach_reattach":True,"preview_confirmed_close":True,
                "exact_owned_session_stopped":True,"working_root_identity_and_profile_preserved":True,
                "visual_pixel_or_performance_qualification":False}
        if args.output:args.output.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report))
        clean=True
        return 0
    finally:
        if browser:
            try:browser.call("Marionette:Quit",{"flags":["eForceQuit"]})
            except (OSError,RuntimeError,ValueError):pass
            browser.close()
        if process and process.poll() is None:
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if clean and os.getpgid(process.pid)==process.pid:
                    os.killpg(process.pid,signal.SIGTERM)
                    process.wait(timeout=8)
        if server:server.close(grace_seconds=5)
        browser_log.close();broker_log.close()
        if clean:
            broker.terminate();broker.wait(timeout=10)
            shutil.rmtree(private);shutil.rmtree(scratch)
        else:
            print(json.dumps({"test_state_retained":str(private),
                              "test_scratch_retained":str(scratch),
                              "test_broker_pid":broker.pid,
                              "test_browser_pid":process.pid if process else None}),file=sys.stderr)

if __name__=="__main__":
    raise SystemExit(main())
