"""Bounded, private Ternuxx log reader tests."""
import json, os, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"lib"))
import management_log_reader as reader
class LogReaderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.home=Path(self.tmp.name)/"home"; self.home.mkdir(mode=0o700)
  self.state=self.home/".local/share/ternuxx"; self.state.mkdir(parents=True,mode=0o700)
  os.chmod(self.home/".local",0o700); os.chmod(self.home/".local/share",0o700)
 def tearDown(self): self.tmp.cleanup()
 def test_inventory_does_not_create_missing_sources(self):
  got=reader.list_logs(str(self.state),home=str(self.home))
  self.assertEqual([x["status"] for x in got["sources"]],["missing","missing"])
  self.assertFalse((self.state/"cron").exists())
 def test_reads_only_bounded_tail_and_scrubs_ansi(self):
  root=self.state/"cron"; root.mkdir(mode=0o700)
  path=root/"scheduler.log"; path.write_text("one\ntwo\nthree\x1b[31mred\x1b[0m\n"); os.chmod(path,0o600)
  got=reader.read_log(str(self.state),home=str(self.home),source_id="cron-scheduler",limit=2)
  self.assertEqual(got["lines"],["two","threered"]); self.assertTrue(got["read_only"])
 def test_audit_omits_session_and_request_identifiers(self):
  root=self.state/"management-api"; root.mkdir(mode=0o700)
  path=root/"audit.jsonl"; path.write_text(json.dumps({"operation":"desktop.start","session_ref":"secret-ref","request_id":"secret-request"})+"\n"); os.chmod(path,0o600)
  got=reader.read_log(str(self.state),home=str(self.home),source_id="management-api")
  self.assertIn("operation=desktop.start",got["lines"][0]); self.assertNotIn("secret-ref",got["lines"][0]); self.assertNotIn("secret-request",got["lines"][0])
 def test_rejects_symlink_and_unprivate_file(self):
  root=self.state/"cron"; root.mkdir(mode=0o700); target=self.home/"target"; target.write_text("x"); os.chmod(target,0o600)
  (root/"scheduler.log").symlink_to(target)
  with self.assertRaises(reader.LogReadError): reader.list_logs(str(self.state),home=str(self.home))
  (root/"scheduler.log").unlink(); path=root/"scheduler.log"; path.write_text("x"); os.chmod(path,0o644)
  with self.assertRaises(reader.LogReadError): reader.read_log(str(self.state),home=str(self.home),source_id="cron-scheduler")
if __name__=="__main__": unittest.main()