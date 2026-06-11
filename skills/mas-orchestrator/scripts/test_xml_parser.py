#!/usr/bin/env python3
"""xml_parser.py unit tests."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xml_parser as xp


class TestExtractXMLSections(unittest.TestCase):

    def test_simple_extraction(self):
        text = "<a>x</a><b>y</b>"
        sections = xp.extract_xml_sections(text)
        self.assertEqual(sections["a"], ["x"])
        self.assertEqual(sections["b"], ["y"])

    def test_multiline_content(self):
        text = "<thinking>\nstep1\nstep2\n</thinking>"
        sections = xp.extract_xml_sections(text)
        self.assertIn("thinking", sections)
        self.assertIn("step1", sections["thinking"][0])

    def test_nested_not_supported_but_outer_extracted(self):
        # Nested same-tag: outer only (greedy avoidance ignores inner or outer only)
        text = "<x>outer<x>inner</x></x>"
        sections = xp.extract_xml_sections(text)
        # Non-greedy matching: up to the first closing tag -> "outer<x>inner"
        # This implementation assumes simple flat tags
        self.assertIn("x", sections)

    def test_repeated_tag_accumulates(self):
        text = "<note>1</note><note>2</note>"
        sections = xp.extract_xml_sections(text)
        self.assertEqual(len(sections["note"]), 2)


class TestOrphanDetection(unittest.TestCase):

    def test_balanced(self):
        text = "<a>x</a>"
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(orphans, [])

    def test_missing_close(self):
        text = "<a>x"
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["tag"], "a")
        self.assertEqual(orphans[0]["open_count"], 1)
        self.assertEqual(orphans[0]["close_count"], 0)

    def test_extra_close(self):
        text = "</a>"
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(len(orphans), 1)

    def test_backtick_quoted_tag_not_orphan(self):
        # Prose mention like "Mandatory `<thinking>`" must not count as orphan
        text = "**`<thinking>` mandatory**: agents must externalize reasoning."
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(orphans, [])

    def test_fenced_code_block_tag_not_orphan(self):
        text = "```\n[Phase 1] -- mandatory <thinking>\n```\n<a>x</a>"
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(orphans, [])

    def test_real_orphan_still_detected_outside_code(self):
        text = "`<thinking>` is described here.\n<answer>unclosed"
        orphans = xp.find_orphan_tags(text)
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["tag"], "answer")


class TestParseAgentDefinition(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write(self, name, content):
        p = Path(self.tmpdir) / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_complete_agent(self):
        full_agent = """
<agent_identity>Role: X</agent_identity>
<knowledge_base>...</knowledge_base>
<execution_protocol>...</execution_protocol>
<output_format>...</output_format>
<token_efficiency_rules>...</token_efficiency_rules>
<failure_modes>...</failure_modes>
<feedback_integration>...</feedback_integration>
"""
        p = self._write("agent_x.md", full_agent)
        result = xp.parse_agent_definition(p)
        self.assertEqual(result["compliance_score"], 1.0)
        self.assertTrue(result["machine_parseable"])
        self.assertEqual(result["missing_required"], [])

    def test_partial_agent(self):
        partial = """
<agent_identity>Role: X</agent_identity>
<execution_protocol>...</execution_protocol>
"""
        p = self._write("agent_partial.md", partial)
        result = xp.parse_agent_definition(p)
        self.assertLess(result["compliance_score"], 1.0)
        self.assertGreater(len(result["missing_required"]), 0)


class TestWorkerOutput(unittest.TestCase):

    def test_proper_thinking_answer(self):
        out = """
<thinking>
Step1
</thinking>

<answer>
Final
</answer>
"""
        result = xp.parse_worker_output(out)
        self.assertEqual(result["compliance_score"], 1.0)

    def test_missing_thinking(self):
        out = "<answer>only answer</answer>"
        result = xp.parse_worker_output(out)
        self.assertIn("thinking", result["missing_required"])


class TestVerifierDimensionScore(unittest.TestCase):

    def test_high_compliance(self):
        reports = [{"compliance_score": 0.95, "missing_required": [],
                    "orphan_tags": [], "file": "a"},
                   {"compliance_score": 0.96, "missing_required": [],
                    "orphan_tags": [], "file": "b"}]
        dim = xp.compute_verifier_dimension_score(reports)
        self.assertEqual(dim["score"], 5)

    def test_low_compliance(self):
        reports = [{"compliance_score": 0.4, "missing_required": ["x", "y"],
                    "orphan_tags": [], "file": "a"}]
        dim = xp.compute_verifier_dimension_score(reports)
        self.assertEqual(dim["score"], 1)

    def test_aggregates_failing_files(self):
        reports = [{"compliance_score": 0.5, "missing_required": ["x"],
                    "orphan_tags": [], "file": "bad.md"},
                   {"compliance_score": 0.95, "missing_required": [],
                    "orphan_tags": [], "file": "good.md"}]
        dim = xp.compute_verifier_dimension_score(reports)
        self.assertIn("bad.md", dim["failing_files"])
        self.assertNotIn("good.md", dim["failing_files"])


class TestLintDirectory(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        agents = self.tmpdir / "agents"
        agents.mkdir()
        (agents / "test_agent.md").write_text(
            "<agent_identity>X</agent_identity>", encoding="utf-8"
        )
        (self.tmpdir / "SKILL.md").write_text(
            "<system_overview>X</system_overview>", encoding="utf-8"
        )

    def test_lint_returns_reports(self):
        reports = xp.lint_directory(self.tmpdir)
        self.assertGreaterEqual(len(reports), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
