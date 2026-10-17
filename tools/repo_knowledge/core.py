"""Deterministic collection/merge logic for the .repo/ state protocol.

Every function here is pure Git/filesystem derivation. Nothing in this module calls an LLM or
makes a judgment call about priority, status, or maturity -- those stay human-authored per
governance/DETERMINISTIC_STATE_SYNC_POLICY.md. A function that cannot derive a fact returns an
explicit "unknown"/None rather than guessing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only when PyYAML is missing
    raise SystemExit("tools/repo_knowledge requires PyYAML (see tools/requirements.txt)") from exc

SCHEMA_VERSION = 1
STATUS_VALUES = ("passed", "failed", "cancelled", "skipped", "timed_out", "unknown")
CONCLUSION_VALUES = (
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "neutral",
    "stale",
    "startup_failure",
    "unknown",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_git(args: list[str], root: Path) -> str | None:
    """Run a git command in ``root``; return stripped stdout, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_head(root: Path) -> dict[str, str | None]:
    commit = run_git(["rev-parse", "HEAD"], root)
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    committed_at_raw = run_git(["show", "-s", "--format=%cI", "HEAD"], root)
    committed_at = _to_utc_z(committed_at_raw) if committed_at_raw else None
    return {"commit": commit, "branch": branch, "committed_at": committed_at}


def _to_utc_z(iso_with_offset: str) -> str:
    """Normalize a git %cI timestamp (has a numeric offset) to a Z-suffixed UTC string."""
    dt = datetime.fromisoformat(iso_with_offset)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_version(root: Path) -> str | None:
    """Return `git describe --tags --always`, or None if not in a git repository at all."""
    return run_git(["describe", "--tags", "--always"], root)


def get_commit_summary(root: Path, commit: str | None = None) -> str | None:
    return run_git(["show", "-s", "--format=%s", commit or "HEAD"], root)


def load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)


def _is_phase_completed(root: Path, phase: dict[str, Any], tags: set[str]) -> bool:
    """Determine whether a declared phase in .repo/phases.yaml is completed.

    Supports:
      1. Tag-gated completion (`complete_tag` present in repository git tags).
      2. Evidence-gated completion (`status: completed` with optional `evidence_path`
         and/or `commit` verified against the repository).
    """
    tag = phase.get("complete_tag")
    if tag and tag in tags:
        return True
    raw_status = str(phase.get("status") or "").strip().lower()
    if raw_status in ("completed", "complete", "done", "passed"):
        ev_path = phase.get("evidence_path")
        if ev_path and not (root / ev_path).exists():
            return False
        commit = phase.get("commit")
        return not commit or bool(re.fullmatch(r"[0-9a-f]{7,40}", str(commit)))
    return False


def compute_phases(root: Path) -> dict[str, Any]:
    """Read the optional, human-authored .repo/phases.yaml and mark completion from tags or verified gates.

    A phase is "completed" when its declared `complete_tag` exists in the repository's
    tag list OR when its declared `status` is `completed` and any declared `evidence_path` /
    `commit` is verified in the repository. Nothing here infers an active/next phase from
    anything but that same declared order -- the first not-completed phase (if any) is
    "active" and the one after it is "next". Never invents a phase name.
    """
    phases_path = root / ".repo" / "phases.yaml"
    declared = load_yaml(phases_path)
    if not declared or "phases" not in declared:
        return {"source": "not_configured", "completed": [], "active": None, "next": None}

    tags_raw = run_git(["tag", "--list"], root)
    tags = set(tags_raw.splitlines()) if tags_raw else set()

    ordered = declared["phases"]
    completed: list[str] = []
    blocked: list[str] = []
    active: str | None = None
    next_phase: str | None = None
    for i, phase in enumerate(ordered):
        name = str(phase.get("name") or phase.get("id") or "")
        if not name:
            continue
        if _is_phase_completed(root, phase, tags):
            completed.append(name)
            continue
        raw_status = str(phase.get("status") or "").strip().lower()
        if raw_status == "blocked":
            blocked.append(name)
        if active is None:
            active = name
            # Find the next non-completed phase after active
            for j in range(i + 1, len(ordered)):
                if not _is_phase_completed(root, ordered[j], tags):
                    next_phase = str(ordered[j].get("name") or ordered[j].get("id") or "") or None
                    break
    result: dict[str, Any] = {
        "source": ".repo/phases.yaml",
        "completed": completed,
        "active": active,
        "next": next_phase,
    }
    if blocked:
        result["blocked"] = blocked
    return result


def _run_block(
    status,
    run_id,
    existing,
    *,
    head,
    run_attempt="1",
    observed_at=None,
    conclusion=None,
    workflow_name=None,
    workflow_id=None,
    event_type=None,
    started_at=None,
    completed_at=None,
    actor=None,
    run_url=None,
):
    if status is None:
        # Historical blocks remain historical: never attach today's commit to an
        # earlier result whose original provenance was not recorded.
        return copy.deepcopy(existing) if existing else {"status": "unknown", "run_id": None, "at": None}
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status {status!r}; expected one of {STATUS_VALUES}")
    if conclusion is not None and conclusion not in CONCLUSION_VALUES:
        raise ValueError(f"invalid conclusion {conclusion!r}; expected one of {CONCLUSION_VALUES}")
    identity = {"status": status, "run_id": run_id, "commit": head["commit"],
                "run_attempt": str(run_attempt)}
    extra: dict[str, Any] = {}
    for k, v in (
        ("conclusion", conclusion),
        ("workflow_name", workflow_name),
        ("workflow_id", workflow_id),
        ("event_type", event_type),
        ("started_at", started_at),
        ("completed_at", completed_at),
        ("actor", actor),
        ("run_url", run_url),
    ):
        if v not in (None, ""):
            extra[k] = v
    if existing and all(existing.get(k) == v for k, v in {**identity, **extra}.items()):
        if observed_at is not None and existing.get("at") != observed_at:
            raise ValueError("same result identity has conflicting evidence timestamp")
        return copy.deepcopy(existing)
    # A CI invocation may supply the actual source run timestamp. Otherwise this
    # is explicitly an observation time, not falsely a CI-completion timestamp.
    at = observed_at or (now_iso() if run_id else head["committed_at"])
    block = {
        **identity,
        "at": at,
        "timestamp_source": "ci" if observed_at else "observed" if run_id else "commit",
    }
    block.update(extra)
    return block


def build_project_state(
    root: Path,
    project_id: str,
    repository: str,
    generated_by: str,
    sync_source: str,
    existing: dict[str, Any] | None,
    build_status: str | None = None,
    build_run_id: str | None = None,
    test_status: str | None = None,
    test_run_id: str | None = None,
    test_summary: str | None = None,
    run_attempt: str = "1",
    build_at: str | None = None,
    test_at: str | None = None,
    source_commit: str | None = None,
    build_conclusion: str | None = None,
    test_conclusion: str | None = None,
    workflow_name: str | None = None,
    workflow_id: str | None = None,
    event_type: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    actor: str | None = None,
    run_url: str | None = None,
) -> dict[str, Any]:
    """Compute the next .repo/project.yaml content.

    Applies policy rules 5-7: a successful run promotes last_successful_build; a failed run
    updates last_failed_build and never clears last_successful_build; a run that reports
    nothing for build/test leaves the previous block untouched.
    """
    head = get_head(root)
    existing = existing or {}

    if not head.get("commit") or not head.get("committed_at"):
        raise ValueError("repository must have an initial commit before state collection")
    # Ignore only a state-publication commit directly above the recorded source.
    # Human .repo/phases.yaml changes and any source changes must remain visible.
    old_head = existing.get("head") or {}
    changed = run_git(["diff", "--name-only", old_head.get("commit") or "HEAD", "HEAD"], root)
    generated_paths = lambda p: p in {".repo/project.yaml", ".repo/STATUS.md",
        "public/verification.json", "app/verification-summary.json"} or p.startswith(".repo/events/")
    if (old_head.get("commit") and changed and
            all(generated_paths(p) for p in changed.splitlines()) and
            (get_commit_summary(root) or "").startswith("chore(repo-knowledge):")):
        head = copy.deepcopy(old_head)
    if source_commit:
        if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise ValueError("source commit must be a full Git SHA")
        if run_git(["merge-base", "HEAD", source_commit], root) != source_commit:
            raise ValueError("CI source is not an ancestor of the checked-out branch")
        delta = run_git(["diff", "--name-only", source_commit, "HEAD"], root)
        if delta and not all(generated_paths(p) for p in delta.splitlines()):
            raise ValueError("new source changes exist after this CI run; refusing stale publication")
        at = run_git(["show", "-s", "--format=%cI", source_commit], root)
        head = {"commit": source_commit, "branch": head["branch"], "committed_at": _to_utc_z(at)}
    build = _run_block(
        build_status,
        build_run_id,
        existing.get("build"),
        head=head,
        run_attempt=run_attempt,
        observed_at=build_at,
        conclusion=build_conclusion,
        workflow_name=workflow_name,
        workflow_id=workflow_id,
        event_type=event_type,
        started_at=started_at,
        completed_at=completed_at,
        actor=actor,
        run_url=run_url,
    )
    test_existing = existing.get("test")
    test = _run_block(
        test_status,
        test_run_id,
        test_existing,
        head=head,
        run_attempt=run_attempt,
        observed_at=test_at,
        conclusion=test_conclusion,
        workflow_name=workflow_name,
        workflow_id=workflow_id,
        event_type=event_type,
        started_at=started_at,
        completed_at=completed_at,
        actor=actor,
        run_url=run_url,
    )
    if test_status is not None and test_summary is not None:
        test["summary"] = test_summary
    elif test_existing and "summary" in test_existing and test_status is None:
        test["summary"] = test_existing["summary"]
    else:
        test.setdefault("summary", None)

    last_successful_build = existing.get("last_successful_build")
    last_failed_build = existing.get("last_failed_build")
    if build_status == "passed":
        last_successful_build = {"commit": head["commit"], "at": build["at"], "run_id": build_run_id}
    elif build_status in ("failed", "timed_out"):
        last_failed_build = {"commit": head["commit"], "at": build["at"], "run_id": build_run_id}

    generated_at = max(filter(None, [head.get("committed_at"), build.get("at"), test.get("at")]))
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "repository": repository,
        "generated_at": generated_at,
        "generated_by": generated_by,
        "version": run_git(["describe", "--tags", "--always", head["commit"]], root),
        "head": head,
        "phases": compute_phases(root),
        "build": build,
        "test": test,
        "last_successful_build": last_successful_build,
        "last_failed_build": last_failed_build,
        "sync": {
            "status": "ok",
            "last_synced_at": generated_at,
            "source": sync_source,
        },
    }


def make_event(
    repository: str,
    commit: str,
    kind: str,
    status: str | None = None,
    summary: str | None = None,
    run_id: str | None = None,
    evidence_level: str | None = None,
    occurred_at: str | None = None,
    run_attempt: str = "1",
    conclusion: str | None = None,
    branch: str | None = None,
    workflow_name: str | None = None,
    workflow_id: str | None = None,
    event_type: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    actor: str | None = None,
    run_url: str | None = None,
    state_version: int | str | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    occurred_at = occurred_at or now_iso()
    short_commit = commit[:12] if commit else "unknown"
    # Local observation identity is content-derived. CI identities include attempt.
    local = json.dumps([repository, commit, kind, status, summary, evidence_level], sort_keys=True)
    suffix = f"{run_id}-{run_attempt}" if run_id else hashlib.sha256(local.encode()).hexdigest()[:16]
    event_id = f"{kind}-{short_commit}-{suffix}"
    event: dict[str, Any] = {
        "event_id": event_id,
        "repository": repository,
        "commit": commit,
        "kind": kind,
        "occurred_at": occurred_at,
    }
    if run_id:
        event["run_id"] = run_id
        event["run_attempt"] = str(run_attempt)
    if status is not None:
        event["status"] = status
    if summary is not None:
        event["summary"] = summary
    if evidence_level is not None:
        event["evidence_level"] = evidence_level
    for k, v in (
        ("conclusion", conclusion),
        ("branch", branch),
        ("workflow_name", workflow_name),
        ("workflow_id", workflow_id),
        ("event_type", event_type),
        ("started_at", started_at),
        ("completed_at", completed_at),
        ("actor", actor),
        ("run_url", run_url),
        ("state_version", state_version),
        ("jobs", jobs),
    ):
        if v not in (None, "", []):
            event[k] = v
    return event


def write_event(root: Path, event: dict[str, Any]) -> Path:
    """Append-only write: an existing event file with the same event_id is never overwritten
    with different content silently -- same id + same content is a no-op; a real conflict
    (same id, different content) raises, because that would mean the id scheme collided.
    """
    path = root / ".repo" / "events" / f"{event['event_id']}.yaml"
    if path.exists():
        existing = load_yaml(path)
        if existing == event:
            return path
        raise RuntimeError(f"event id collision with differing content: {path}")
    dump_yaml(path, event)
    return path


def render_status_markdown(state: dict[str, Any]) -> str:
    lines = [
        "<!-- GENERATED by tools/repo_knowledge -- do not hand-edit. -->",
        f"# {state['project_id']} -- deterministic status",
        "",
        f"- Repository: `{state['repository']}`",
        f"- Generated at: {state['generated_at']} (by `{state['generated_by']}`)",
        f"- Version: `{state['version'] or 'unknown'}`",
        f"- Head: `{state['head']['commit']}` on `{state['head']['branch']}` ({state['head']['committed_at']})",
        "",
        "## Build / test",
        "",
        f"- Build: **{state['build']['status']}**" + (f" (run `{state['build']['run_id']}`)" if state['build'].get('run_id') else ""),
        f"- Test: **{state['test']['status']}**" + (f" -- {state['test']['summary']}" if state['test'].get('summary') else ""),
    ]
    if state.get("last_successful_build"):
        lsb = state["last_successful_build"]
        lines.append(f"- Last successful build: `{lsb['commit']}` at {lsb['at']}")
    if state.get("last_failed_build"):
        lfb = state["last_failed_build"]
        lines.append(f"- Last failed build: `{lfb['commit']}` at {lfb['at']}")
    phases = state.get("phases", {})
    lines += ["", "## Phases"]
    if phases.get("source") == "not_configured":
        lines.append("- Not configured (no `.repo/phases.yaml`).")
    else:
        lines.append(f"- Completed: {', '.join(phases['completed']) or 'none'}")
        lines.append(f"- Active: {phases['active'] or 'none'}")
        lines.append(f"- Next: {phases['next'] or 'none'}")
        if phases.get("blocked"):
            lines.append(f"- Blocked: {', '.join(phases['blocked'])}")
    sync = state.get("sync", {})
    lines += ["", "## Sync", "", f"- Status: {sync.get('status')}", f"- Source: {sync.get('source')}", f"- Last synced at: {sync.get('last_synced_at')}"]
    return "\n".join(lines) + "\n"
