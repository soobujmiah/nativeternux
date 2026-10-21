"""Interactive CLI client for the shared local terminal broker."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import select
import shutil
import signal
import sys
import termios
import time
import tty

import terminal_broker


def _client() -> terminal_broker.UnixBrokerClient:
    state = os.environ.get("TERNUXX_STATE_DIR") or str(Path.home()/".local/share/ternuxx")
    return terminal_broker.UnixBrokerClient(state)


def _ok(response: dict[str, object]) -> dict[str, object]:
    if response.get("ok") is not True:
        error=response.get("error")
        code=error.get("code") if isinstance(error,dict) else "operation_failed"
        raise terminal_broker.BrokerError("terminal broker operation failed: "+str(code))
    return response


def _dimensions() -> tuple[int,int]:
    size=shutil.get_terminal_size((80,24))
    return max(1,min(size.columns,500)),max(1,min(size.lines,300))


def attach(session_id: str, *, client: terminal_broker.UnixBrokerClient | None = None,
           principal: str = "native-termux", lease: dict[str,object] | None = None) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise terminal_broker.BrokerError("interactive attach requires a local terminal")
    client=client or _client()
    if lease is None:
        lease=_ok(client.request("terminal.attach",session_id=session_id))
        generation=lease["generation"]
        attachment_id=lease["attachment_id"]
    else:
        generation=lease["generation"]
        attachment_id=lease["attachment_id"]
        session_id=lease["session_id"]
    columns,rows=_dimensions()
    client.request("terminal.resize",session_id=session_id,generation=generation,
                   attachment_id=attachment_id,args={"columns":columns,"rows":rows})
    old=termios.tcgetattr(sys.stdin.fileno())
    previous_handlers={}
    def interrupted(signum, _frame):
        raise InterruptedError(f"terminal client interrupted by signal {signum}")
    for sig in (signal.SIGHUP,signal.SIGTERM):
        previous_handlers[sig]=signal.signal(sig,interrupted)
    cursor=0
    last_size=(columns,rows)
    detached=False
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            readable,_,_=select.select([sys.stdin.fileno()],[],[],0.04)
            if readable:
                data=os.read(sys.stdin.fileno(),2048)
                if not data: break
                if b"\x1d" in data:
                    before,_,after=data.partition(b"\x1d")
                    if before:
                        client.request("terminal.input",session_id=session_id,generation=generation,
                            attachment_id=attachment_id,args={"data_base64":base64.b64encode(before).decode("ascii")})
                    detached=True
                    break
                client.request("terminal.input",session_id=session_id,generation=generation,
                    attachment_id=attachment_id,args={"data_base64":base64.b64encode(data).decode("ascii")})
            size=_dimensions()
            if size!=last_size:
                columns,rows=size; last_size=size
                client.request("terminal.resize",session_id=session_id,generation=generation,
                    attachment_id=attachment_id,args={"columns":columns,"rows":rows})
            response=_ok(client.request("terminal.output",session_id=session_id,generation=generation,
                    attachment_id=attachment_id,args={"after_sequence":cursor}))
            if response.get("truncated"):
                sys.stdout.write("\r\n[terminal output skipped while disconnected]\r\n")
            chunks=response.get("chunks",[])
            if isinstance(chunks,list):
                for chunk in chunks:
                    if isinstance(chunk,dict) and isinstance(chunk.get("data_base64"),str):
                        payload=base64.b64decode(chunk["data_base64"],validate=True)
                        sys.stdout.buffer.write(payload); sys.stdout.buffer.flush()
                        cursor=int(chunk["sequence"])
            if response.get("next_sequence",cursor)>cursor and not chunks:
                cursor=int(response["next_sequence"])
        return 0
    finally:
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,old)
        for sig,handler in previous_handlers.items(): signal.signal(sig,handler)
        if not detached:
            try:
                client.request("terminal.detach",session_id=session_id,generation=generation,
                               attachment_id=attachment_id)
            except terminal_broker.BrokerError:
                pass


def run(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(prog="tx terminal",description="Attach to the fixed Debian interactive terminal")
    sub=parser.add_subparsers(dest="action",required=True)
    sub.add_parser("status",help="show the optional broker state")
    sub.add_parser("serve",help="run the Native Termux broker in the foreground")
    sub.add_parser("start",help="preview and start a fixed Debian interactive login")
    attach_parser=sub.add_parser("attach",help="attach to one verified Ternuxx session")
    attach_parser.add_argument("session_id")
    close_parser=sub.add_parser("close",help="preview and stop one verified Ternuxx session")
    close_parser.add_argument("session_id")
    args=parser.parse_args(argv)
    try:
        if args.action=="serve":
            import terminal_broker_service
            return terminal_broker_service.serve()
        client=_client()
        if args.action=="status":
            print(json.dumps(_ok(client.request("broker.status")),indent=2)); return 0
        if args.action=="start":
            if not sys.stdin.isatty(): raise terminal_broker.BrokerError("starting an interactive guest requires a local terminal")
            preview=_ok(client.request("terminal.start.preview"))["plan"]
            print(json.dumps(preview,indent=2))
            if input("Start this fixed Debian login? [y/N] ").strip().lower()!="y": return 1
            result=_ok(client.request("terminal.start",args={"confirmed":True,"plan_id":preview["plan_id"]}))
            return attach(result["result"]["session_id"],client=client,lease=result["result"])
        if args.action=="attach":
            return attach(args.session_id,client=client)
        if args.action=="close":
            lease=_ok(client.request("terminal.attach",session_id=args.session_id))
            generation=lease["generation"]; attachment=lease["attachment_id"]
            try:
                preview=_ok(client.request("terminal.close.preview",session_id=args.session_id,
                    generation=generation,attachment_id=attachment))["plan"]
                print(json.dumps(preview,indent=2))
                if input("Stop this exact verified session? [y/N] ").strip().lower()!="y": return 1
                _ok(client.request("terminal.close",session_id=args.session_id,generation=generation,
                    attachment_id=attachment,args={"confirmed":True,"plan_id":preview["plan_id"]}))
                return 0
            finally:
                try: client.request("terminal.detach",session_id=args.session_id,generation=generation,attachment_id=attachment)
                except terminal_broker.BrokerError: pass
        return 2
    except (OSError,ValueError,InterruptedError,terminal_broker.BrokerError) as exc:
        print(f"tx terminal: {exc}",file=sys.stderr); return 1


if __name__=="__main__":
    raise SystemExit(run())
