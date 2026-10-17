#!/usr/bin/env python3
"""repo-knowledge -- deterministic, non-LLM repository state sync CLI.

See governance/DETERMINISTIC_STATE_SYNC_POLICY.md and governance/REPO_STATE_PROTOCOL.md in the
SKB repository. Every subcommand here is pure Git/filesystem derivation; none of them call an
LLM, and none of them write status/priority/maturity/next_gate -- those remain human-authored.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from . import core, validate

REPO_DIR_NAME = ".repo"


def _repo_dir(root: Path) -> Path:
    return root / REPO_DIR_NAME


def _project_yaml(root: Path) -> Path:
    return _repo_dir(root) / "project.yaml"


def _infer_repository(root: Path) -> str | None:
    url = core.run_git(["remote", "get-url", "origin"], root)
    if not url:
        return None
    match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return match.group(1) if match else None


def _resolve_identity(root: Path, args: argparse.Namespace) -> tuple[str, str]:
    existing = core.load_yaml(_project_yaml(root)) or {}
    inferred = _infer_repository(root)
    repository = args.repository or existing.get("repository") or inferred
    if not repository:
        raise SystemExit("could not infer repository; pass --repository owner/repo")
    if existing.get("repository") and repository != existing["repository"]:
        raise ValueError("repository identity change requires explicit migration")
    if inferred and inferred != repository:
        raise ValueError("origin remote does not match repository identity")
    project_id = args.project_id or existing.get("project_id") or repository.split("/", 1)[1]
    if existing.get("project_id") and project_id != existing["project_id"]:
        raise ValueError("project identity change requires explicit migration")
    return project_id, repository


@contextlib.contextmanager
def _locked(root):
    git_dir = core.run_git(["rev-parse", "--absolute-git-dir"], root)
    if not git_dir:
        raise ValueError("state collection requires a Git repository")
    with (Path(git_dir) / "repo-knowledge.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _publish(staged, destination):
    """Atomic directory exchange on Linux; fail closed when unsupported.

    All files have been derived and validated before this call. An interrupted
    reader sees a complete old or complete new directory, never a partial batch.
    """
    if not destination.exists():
        os.replace(staged, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    exchange = getattr(libc, "renameat2", None)
    if exchange is None:
        raise RuntimeError("atomic directory exchange unavailable; state was not changed")
    exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    exchange.restype = ctypes.c_int
    if exchange(-100, os.fsencode(staged), -100, os.fsencode(destination), 2) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _validate_candidate(root, state, events):
    schema_dir = root / "schemas"
    if not schema_dir.exists():
        # The CLI's own canonical schemas support disposable library fixtures.
        schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    findings = validate.validate(state, validate.load_schema(schema_dir / "project-registry.schema.json"))
    event_schema = validate.load_schema(schema_dir / "project-event.schema.json")
    for event in events:
        findings += validate.validate(event, event_schema)
    if findings:
        raise ValueError("candidate state rejected: " + "; ".join(findings))


def _transaction(root, state, events, *, status=True):
    _validate_candidate(root, state, events)
    # Detect conflicting event identities before preparing ANY published writes.
    for event in events:
        prior = core.load_yaml(root / ".repo" / "events" / (event["event_id"] + ".yaml"))
        if prior is not None and prior != event:
            raise RuntimeError("event id collision with differing content: " + event["event_id"])
    with tempfile.TemporaryDirectory(prefix=".repo-stage-", dir=root) as tmp:
        work = Path(tmp)
        dest = work / ".repo"
        if (root / ".repo").exists():
            shutil.copytree(root / ".repo", dest)
        else:
            (dest / "events").mkdir(parents=True)
        core.dump_yaml(dest / "project.yaml", state)
        for event in events:
            core.write_event(work, event)
        if status:
            (dest / "STATUS.md").write_text(core.render_status_markdown(state), encoding="utf-8")
        def snapshot(path):
            return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
        if (root / ".repo").exists() and snapshot(dest) == snapshot(root / ".repo"):
            print("state unchanged")
            return
        _publish(dest, root / ".repo")


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    with _locked(root):
        project_id, repository = _resolve_identity(root, args)
        if _project_yaml(root).exists():
            print(f"already initialized: {_project_yaml(root)}")
            return 0
        state = core.build_project_state(root, project_id, repository,
            generated_by="tools/repo_knowledge init", sync_source="local", existing=None)
        state["sync"]["status"] = "pending"
        _transaction(root, state, [], status=True)
    return 0


def _collect(args, *, sync):
    root = Path(args.root).resolve()
    with _locked(root):
        project_id, repository = _resolve_identity(root, args)
        existing = core.load_yaml(_project_yaml(root))
        build_id = args.build_run_id or (os.environ.get("GITHUB_RUN_ID") if args.ci else None)
        test_id = args.test_run_id or build_id
        state = core.build_project_state(
            root,
            project_id,
            repository,
            generated_by="tools/repo_knowledge collect",
            sync_source="ci" if args.ci else "local",
            existing=existing,
            build_status=args.build_status,
            build_run_id=build_id,
            test_status=args.test_status,
            test_run_id=test_id,
            test_summary=args.test_summary,
            run_attempt=args.run_attempt,
            build_at=args.build_at,
            test_at=args.test_at,
            source_commit=args.source_commit,
            build_conclusion=args.build_conclusion,
            test_conclusion=args.test_conclusion,
            workflow_name=args.workflow_name,
            workflow_id=args.workflow_id,
            event_type=args.event_type,
            started_at=args.started_at,
            completed_at=args.completed_at,
            actor=args.actor,
            run_url=args.run_url,
        )
        head = state["head"]
        events = []
        if head["commit"] != (existing or {}).get("head", {}).get("commit"):
            events.append(core.make_event(repository, head["commit"], "commit", status="completed",
                summary=core.get_commit_summary(root, head["commit"]), occurred_at=head["committed_at"]))
        for kind in ("build", "test"):
            if getattr(args, kind + "_status") is not None:
                block = state[kind]
                events.append(core.make_event(
                    repository,
                    head["commit"],
                    kind,
                    status=block["status"],
                    summary=block.get("summary"),
                    run_id=block.get("run_id"),
                    occurred_at=block["at"],
                    run_attempt=block.get("run_attempt", "1"),
                    conclusion=block.get("conclusion"),
                    workflow_name=block.get("workflow_name"),
                    workflow_id=block.get("workflow_id"),
                    event_type=block.get("event_type"),
                    started_at=block.get("started_at"),
                    completed_at=block.get("completed_at"),
                    actor=block.get("actor"),
                    run_url=block.get("run_url"),
                ))
        if sync:
            # A sync records a state transition, not every invocation/poll.
            import hashlib
            identity = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()[:16]
            events.append(core.make_event(repository, head["commit"], "sync", status="completed",
                run_id="state-" + identity, occurred_at=state["generated_at"]))
        _transaction(root, state, events)
    print(f"collected validated state for {repository}")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    return _collect(args, sync=False)


def cmd_sync(args: argparse.Namespace) -> int:
    return _collect(args, sync=True)


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    schemas_dir = root / "schemas"
    findings: list[str] = []

    project_yaml = _project_yaml(root)
    state = core.load_yaml(project_yaml)
    if state is None:
        print(f"VERIFY: {project_yaml} does not exist (run `repo-knowledge init` first)")
        return 1
    status_path = _repo_dir(root) / "STATUS.md"
    if not status_path.exists():
        findings.append("STATUS.md is missing")
    elif status_path.read_text(encoding="utf-8") != core.render_status_markdown(state):
        findings.append("STATUS.md differs from the canonical state rendering")
    registry_schema = validate.load_schema(schemas_dir / "project-registry.schema.json")
    findings += [f"project.yaml {e}" for e in validate.validate(state, registry_schema)]

    event_schema = validate.load_schema(schemas_dir / "project-event.schema.json")
    events_dir = _repo_dir(root) / "events"
    for event_path in sorted(events_dir.glob("*.yaml")) if events_dir.exists() else []:
        event = core.load_yaml(event_path)
        findings += [f"{event_path.name} {e}" for e in validate.validate(event, event_schema)]

    if findings:
        print(f"VERIFY: {len(findings)} finding(s)")
        for f in findings:
            print(f"- {f}")
        return 1
    print("VERIFY: 0 findings")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    state = core.load_yaml(_project_yaml(root))
    if state is None:
        print("no .repo/project.yaml -- run `repo-knowledge init` first")
        return 1
    print(core.render_status_markdown(state))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-knowledge", description=__doc__)
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--repository", default=None, help="owner/repo, inferred from origin if omitted")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the .repo/ skeleton").set_defaults(func=cmd_init)

    for name, func in (("collect", cmd_collect), ("sync", cmd_sync)):
        p = sub.add_parser(name)
        p.add_argument("--ci", action="store_true", help="mark this run's sync.source as ci")
        p.add_argument("--build-status", choices=core.STATUS_VALUES, default=None)
        p.add_argument("--build-run-id", default=None)
        p.add_argument("--test-status", choices=core.STATUS_VALUES, default=None)
        p.add_argument("--test-run-id", default=None)
        p.add_argument("--test-summary", default=None)
        p.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
        p.add_argument("--build-at", default=None, help="actual CI evidence timestamp; otherwise first observation is labelled")
        p.add_argument("--test-at", default=None)
        p.add_argument("--source-commit", default=None, help="checked CI source SHA; only generated-only later commits are permitted")
        p.add_argument("--build-conclusion", choices=core.CONCLUSION_VALUES, default=None)
        p.add_argument("--test-conclusion", choices=core.CONCLUSION_VALUES, default=None)
        p.add_argument("--workflow-name", default=None)
        p.add_argument("--workflow-id", default=None)
        p.add_argument("--event-type", default=None)
        p.add_argument("--started-at", default=None)
        p.add_argument("--completed-at", default=None)
        p.add_argument("--actor", default=None)
        p.add_argument("--run-url", default=None)
        p.set_defaults(func=func)

    sub.add_parser("verify", help="validate .repo/ against the schemas; report-only").set_defaults(func=cmd_verify)
    sub.add_parser("status", help="print a human summary of .repo/project.yaml").set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
