#!/usr/bin/env python3
"""SkillOpt Adapter unit tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import skillopt_adapter as soa


class TestSkillEdit(unittest.TestCase):

    def test_add_edit(self):
        edit = soa.SkillEdit("add", "(end)", content_after="new content")
        self.assertEqual(edit.op_type, "add")
        self.assertEqual(edit.cost(), 1)

    def test_delete_edit(self):
        edit = soa.SkillEdit("delete", "## Old Section")
        self.assertEqual(edit.cost(), 1)

    def test_replace_edit(self):
        edit = soa.SkillEdit("replace", "section",
                              content_before="old", content_after="new")
        self.assertEqual(edit.cost(), 2)  # replace = highest

    def test_invalid_op_type(self):
        with self.assertRaises(ValueError):
            soa.SkillEdit("invalid_op", "x")

    def test_apply_add(self):
        edit = soa.SkillEdit("add", "(end)", content_after="ADDED")
        result = edit.apply_to("original\n")
        self.assertIn("ADDED", result)
        self.assertIn("original", result)

    def test_apply_replace(self):
        edit = soa.SkillEdit("replace", "section",
                              content_before="old text",
                              content_after="new text")
        result = edit.apply_to("here is old text in doc")
        self.assertIn("new text", result)
        self.assertNotIn("old text", result)

    def test_apply_delete(self):
        edit = soa.SkillEdit("delete", "section to remove")
        result = edit.apply_to("keep this section to remove drop")
        self.assertNotIn("section to remove", result)


class TestBoundedEdits(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        skill_file = self.tmpdir / "skill.md"
        skill_file.write_text("# Test", encoding="utf-8")
        self.adapter = soa.SkillOptAdapter(skill_file, edit_budget=3, max_epochs=1)

    def test_within_budget(self):
        edits = [
            soa.SkillEdit("add", "(end)", content_after="A"),
            soa.SkillEdit("add", "(end)", content_after="B"),
            soa.SkillEdit("delete", "X"),
        ]
        accepted, deferred = self.adapter._bound_edits(edits)
        self.assertEqual(len(accepted), 3)  # 1+1+1 = 3 = budget
        self.assertEqual(len(deferred), 0)

    def test_over_budget_defers(self):
        edits = [
            soa.SkillEdit("replace", "x", content_before="a", content_after="b"),  # cost 2
            soa.SkillEdit("replace", "y", content_before="c", content_after="d"),  # cost 2
        ]
        accepted, deferred = self.adapter._bound_edits(edits)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(deferred), 1)


class TestSkillOptLoop(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.skill_file = self.tmpdir / "skill.md"
        self.skill_file.write_text("# Initial\n\nRule 1.\n", encoding="utf-8")

    def test_train_runs_epochs(self):
        adapter = soa.SkillOptAdapter(self.skill_file, max_epochs=2)
        result = adapter.train(
            train_batch=[{"task_id": f"t{i}"} for i in range(3)],
            val_batch=[{"task_id": f"v{i}"} for i in range(2)]
        )
        self.assertEqual(len(result["history"]), 2)
        self.assertIn("best_skill_path", result)

    def test_export_best_skill_file(self):
        adapter = soa.SkillOptAdapter(self.skill_file, max_epochs=1)
        result = adapter.train([{"task_id": "t1"}], [{"task_id": "v1"}])
        best_path = Path(result["best_skill_path"])
        self.assertTrue(best_path.exists())
        self.assertIn("best_skill", best_path.name)

    def test_rejected_buffer_accumulates(self):
        # validator always returns 0 -> all edits rejected
        def always_reject(skill, val_batch):
            return {"score": 0, "details": "reject"}

        # reflector always returns an edit
        def always_propose(skill, succ, fail):
            return [soa.SkillEdit("add", "(end)", content_after="X")]

        adapter = soa.SkillOptAdapter(self.skill_file,
                                       reflector_fn=always_propose,
                                       validator_fn=always_reject,
                                       max_epochs=3)
        result = adapter.train([{"task_id": "t"}], [{"task_id": "v"}])
        self.assertGreater(result["rejected_count"], 0)

    def test_state_persistence(self):
        persistent = self.tmpdir / "state"
        adapter = soa.SkillOptAdapter(self.skill_file,
                                       max_epochs=1, persistent_dir=persistent)
        adapter.train([{"task_id": "t"}], [{"task_id": "v"}])
        state_file = persistent / "skillopt_state.json"
        self.assertTrue(state_file.exists())
        data = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertIn("history", data)
        self.assertIn("rejected_buffer", data)


class TestMASIntegration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def test_verifier_integration(self):
        report = {"overall_score": 4.5, "verdict": "PASS",
                  "quality_rubric": {"accuracy": {"score": 5}}}
        report_path = self.tmpdir / "verifier_report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        result = soa.integrate_with_mas_verifier(report_path)
        self.assertEqual(result["score"], 4.5)
        self.assertEqual(result["details"]["verdict"], "PASS")

    def test_verifier_integration_missing(self):
        result = soa.integrate_with_mas_verifier(self.tmpdir / "missing.json")
        self.assertEqual(result["score"], 0)

    def test_adversarial_critic_integration(self):
        report = {"claim_analyses": [{
            "claim_id": "AC001",
            "coverage_gaps": ["edge case for null input", "timezone handling"]
        }]}
        report_path = self.tmpdir / "adversarial.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        edits = soa.integrate_with_adversarial_critic(report_path)
        self.assertEqual(len(edits), 2)
        for e in edits:
            self.assertEqual(e.op_type, "add")


if __name__ == "__main__":
    unittest.main(verbosity=2)
