from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import yaml

from tools.repo_knowledge import core
from tools.repo_knowledge.cli import cmd_sync, cmd_verify, migrate_repository


class RepositoryRenameMigrationTests(unittest.TestCase):
    old_repository = "owner/old-project"
    new_repository = "owner/new-project"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._git("init", "-q")
        self._git("config", "user.name", "Test User")
        self._git("config", "user.email", "test@example.invalid")
        (self.root / "tracked.txt").write_text("fixture\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        self._git("commit", "-qm", "fixture source")
        self._git("remote", "add", "origin", f"https://github.com/{self.new_repository}.git")

        repo_dir = self.root / ".repo"
        (repo_dir / "events").mkdir(parents=True)
        self.old_event = core.make_event(
            self.old_repository,
            core.get_head(self.root)["commit"],
            "commit",
            status="completed",
            summary="before rename",
            occurred_at="2026-01-01T00:00:00Z",
        )
        core.dump_yaml(repo_dir / "events" / f"{self.old_event['event_id']}.yaml", self.old_event)
        state = core.build_project_state(
            self.root,
            "stable-project-id",
            self.old_repository,
            generated_by="fixture",
            sync_source="local",
            existing=None,
        )
        core.dump_yaml(repo_dir / "project.yaml", state)
        (repo_dir / "STATUS.md").write_text(core.render_status_markdown(state), encoding="utf-8")
        self.history_bytes = (repo_dir / "events" / f"{self.old_event['event_id']}.yaml").read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str) -> None:
        import subprocess

        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True)

    def test_rename_updates_current_identity_and_preserves_history(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_verify(SimpleNamespace(root=str(self.root))), 1)
        migrate_repository(self.root, self.old_repository, self.new_repository)

        state = core.load_yaml(self.root / ".repo/project.yaml")
        self.assertEqual(state["repository"], self.new_repository)
        self.assertEqual(state["project_id"], "stable-project-id")
        self.assertEqual(state["head"]["commit"], core.get_head(self.root)["commit"])
        self.assertEqual(state["generated_by"], "tools/repo_knowledge migrate-repository")
        self.assertEqual(
            (self.root / ".repo/events" / f"{self.old_event['event_id']}.yaml").read_bytes(),
            self.history_bytes,
        )

        events = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in (self.root / ".repo/events").glob("*.yaml")]
        rename_events = [e for e in events if e.get("summary", "").startswith("Repository renamed from ")]
        self.assertEqual(len(rename_events), 1)
        self.assertEqual(rename_events[0]["repository"], self.new_repository)
        self.assertEqual(rename_events[0]["kind"], "sync")
        self.assertEqual(rename_events[0]["source_paths"], [".repo/project.yaml"])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_verify(SimpleNamespace(root=str(self.root))), 0)

        migrated_at = state["generated_at"]
        sync_args = SimpleNamespace(
            root=str(self.root), project_id=None, repository=None, ci=False,
            build_run_id=None, test_run_id=None,
            build_status=None, test_status=None, test_summary=None, run_attempt="1",
            build_at=None, test_at=None, source_commit=None, build_conclusion=None,
            test_conclusion=None, workflow_name=None, workflow_id=None, event_type=None,
            started_at=None, completed_at=None, actor=None, run_url=None,
        )
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_sync(sync_args), 0)
            self.assertEqual(cmd_verify(SimpleNamespace(root=str(self.root))), 0)
        state_after_sync = core.load_yaml(self.root / ".repo/project.yaml")
        self.assertEqual(state_after_sync["repository"], self.new_repository)
        self.assertEqual(state_after_sync["project_id"], "stable-project-id")
        self.assertEqual(state_after_sync["generated_at"], migrated_at)
        self.assertEqual(
            (self.root / ".repo/events" / f"{self.old_event['event_id']}.yaml").read_bytes(),
            self.history_bytes,
        )

    def test_migration_fails_closed_when_origin_does_not_match_target(self) -> None:
        repo_yaml = (self.root / ".repo/project.yaml").read_bytes()
        events_before = sorted(p.read_bytes() for p in (self.root / ".repo/events").glob("*.yaml"))
        with self.assertRaisesRegex(ValueError, "origin must point"):
            migrate_repository(self.root, self.old_repository, "owner/wrong-target")
        self.assertEqual((self.root / ".repo/project.yaml").read_bytes(), repo_yaml)
        self.assertEqual(sorted(p.read_bytes() for p in (self.root / ".repo/events").glob("*.yaml")), events_before)

    def test_migration_rejects_owner_transfer(self) -> None:
        with self.assertRaisesRegex(ValueError, "same owner"):
            migrate_repository(self.root, self.old_repository, "other/new-project")


if __name__ == "__main__":
    unittest.main()
