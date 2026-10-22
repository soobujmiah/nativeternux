#!/usr/bin/env python3
"""Inventory repository documents; read marks are not claim acceptance."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/audit/document-inventory.json"


def documents():
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=ROOT, check=True, stdout=subprocess.PIPE)
    files = set(result.stdout.decode().split("\0")) - {""}
    selected = []
    for name in sorted(files):
        path = ROOT / name
        if name.startswith(".repo/") or path == OUTPUT or not path.is_file() or path.is_symlink():
            continue
        suffix = path.suffix.lower()
        if (suffix in {".md", ".rst", ".txt"}
                or name.startswith(("docs/", "schemas/", "config/", ".github/")) and suffix in {".json", ".yaml", ".yml", ".csv"}
                or name in {"PROJECT_MANIFEST.yaml", "PROJECT_CLASSIFICATION.yaml",
                            "project/phase-state.json"}):
            selected.append((name, path))
    return selected


def broken_links(files):
    errors = []
    for name, path in files:
        if path.suffix.lower() != ".md":
            continue
        text = re.sub(chr(96)*3 + r".*?" + chr(96)*3, "", path.read_text(), flags=re.S)
        for match in re.finditer(r"\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
            target = match[1].strip("<>")
            if target.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            target_path = urllib.parse.unquote(target.split("#", 1)[0])
            resolved = (path.parent / target_path).resolve()
            if resolved == OUTPUT:
                continue
            if not resolved.is_relative_to(ROOT):
                errors.append({"file": name, "target": target, "issue": "outside-repository"})
            elif not resolved.exists():
                errors.append({"file": name, "target": target, "issue": "missing-target"})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mark-read", action="append", default=[],
                        help="Record a file actually read in context; repeatable")
    parser.add_argument("--check", action="store_true", help="Check stored file/hash coverage")
    args = parser.parse_args()
    files = documents()
    old = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {}
    previous = {item["path"]: item for item in old.get("documents", [])}
    marked = set(args.mark_read)
    unknown = marked - {name for name, _path in files}
    if unknown:
        parser.error("not an inventoried document: " + ", ".join(sorted(unknown)))
    entries = []
    for name, path in files:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        was_read = previous.get(name, {}).get("read_sha256") == digest
        read = name in marked or was_read
        entries.append({"path": name, "kind": "narrative" if path.suffix in {".md", ".rst", ".txt"} else "structured",
                        "sha256": digest, "lines": len(data.splitlines()),
                        "read_status": "read" if read else "pending",
                        "read_sha256": digest if read else None})
    if args.check:
        stored = {entry["path"]: entry["sha256"] for entry in old.get("documents", [])}
        current = {entry["path"]: entry["sha256"] for entry in entries}
        if stored != current:
            raise SystemExit("document inventory is stale; regenerate after review")
        print("Document inventory path/hash coverage is current.")
        return
    read_count = sum(entry["read_status"] == "read" for entry in entries)
    report = {"schema_version": 1,
        "scope": "Git tracked/non-ignored narrative docs, docs/schema/config/workflow contracts, root manifests and phase state; .repo generated state excluded",
        "semantics": "Hashing/indexing is not review. Read marks are explicit agent records; claim acceptance remains in the worklist. Changed hashes invalidate previous read marks.",
        "generated_state_scope": ".repo generated status/events use tools.repo_knowledge; exclude their volatile hashes to avoid CI/inventory loops",
        "document_count": len(entries), "read_count": read_count,
        "reading_complete": read_count == len(entries),
        "broken_local_links": broken_links(files), "documents": entries}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(OUTPUT)
    print(f"Documents read: {read_count}/{len(entries)}; broken local links: {len(report['broken_local_links'])}")


if __name__ == "__main__":
    main()
