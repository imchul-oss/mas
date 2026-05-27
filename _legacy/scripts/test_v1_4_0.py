#!/usr/bin/env python3
"""v1.4.0 A+B+C 통합 단위 테스트."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import skillopt_v1_4_extensions as sv14
import reflexion_full_stack as rfs
import senior_engineer_metrics as sem


# ============================================================
# A. SkillOpt v1.4 Extensions
# ============================================================

class TestSlowUpdate(unittest.TestCase):

    def test_record_and_persistent_rejections(self):
        su = sv14.SlowUpdate(lookback_epochs=3)
        edit_a = {"op_type": "add", "target_section": "x"}
        edit_b = {"op_type": "replace", "target_section": "y"}
        su.record_epoch(1, [edit_a], [edit_b], 0.7)
        su.record_epoch(2, [], [edit_b], 0.72)
        su.record_epoch(3, [edit_a], [edit_b], 0.75)
        persistent = su.detect_persistent_rejections(threshold=2)
        self.assertGreater(len(persistent), 0)
        self.assertEqual(persistent[0]["rejection_count"], 3)

    def test_slow_improvements_detection(self):
        su = sv14.SlowUpdate()
        for e, score in [(1, 0.7), (2, 0.71), (3, 0.73), (4, 0.74)]:
            su.record_epoch(e, [], [], score)
        result = su.detect_slow_improvements()
        self.assertTrue(result["is_slow_improving"])
        self.assertEqual(result["trend"], "improving")

    def test_declining_trend(self):
        su = sv14.SlowUpdate()
        for e, score in [(1, 0.9), (2, 0.85), (3, 0.8)]:
            su.record_epoch(e, [], [], score)
        result = su.detect_slow_improvements()
        self.assertFalse(result["is_slow_improving"])
        self.assertEqual(result["trend"], "declining")


class TestMetaSkill(unittest.TestCase):

    def test_success_rate_tracking(self):
        ms = sv14.MetaSkill()
        edit = {"op_type": "add", "target_section": "section_x"}
        for _ in range(7):
            ms.update(edit, "accepted")
        for _ in range(3):
            ms.update(edit, "rejected", "validation_gate_failed")
        rate = ms.get_pattern_success_rate(edit)
        self.assertEqual(rate["n_samples"], 10)
        self.assertAlmostEqual(rate["success_rate"], 0.7, places=2)

    def test_no_prior_returns_none(self):
        ms = sv14.MetaSkill()
        rate = ms.get_pattern_success_rate({"op_type": "delete", "target_section": "z"})
        self.assertIsNone(rate)

    def test_top_successful_filters_low_samples(self):
        ms = sv14.MetaSkill()
        e1 = {"op_type": "add", "target_section": "a"}
        e2 = {"op_type": "add", "target_section": "b"}
        ms.update(e1, "accepted")
        ms.update(e1, "accepted")
        # e2 는 2 samples (threshold 미만)
        ms.update(e2, "accepted")
        ms.update(e2, "accepted")
        top = ms.top_successful_patterns(top_k=5)
        # 2 samples 는 제외 (≥ 3 만)
        self.assertEqual(len(top), 0)


# ============================================================
# B. Reflexion Full Stack
# ============================================================

class TestReflectionTrace(unittest.TestCase):

    def test_xml_prompt_format(self):
        t = rfs.ReflectionTrace()
        t.add(1, [{"criterion_id": "SC1"}],
              "data 수집 OK", "score 0.6 미달", "edge case", "null 처리 추가")
        xml = t.to_prompt()
        self.assertIn("<reflection_trace>", xml)
        self.assertIn("SC1", xml)
        self.assertIn("null 처리", xml)


class TestReflectionParser(unittest.TestCase):

    def test_parse_valid_response(self):
        text = """
        <reflection>
        <what_worked>A</what_worked>
        <what_failed>B</what_failed>
        <root_cause>C</root_cause>
        <next_strategy>D</next_strategy>
        </reflection>
        """
        parsed = rfs.parse_reflection_response(text)
        self.assertEqual(parsed["what_worked"], "A")
        self.assertEqual(parsed["next_strategy"], "D")

    def test_parse_empty_returns_none(self):
        parsed = rfs.parse_reflection_response("no reflection here")
        self.assertIsNone(parsed)


class TestReflexionEnhancedSelfReflect(unittest.TestCase):

    def test_no_llm_callback_fallback(self):
        r = rfs.ReflexionEnhancedSelfReflect(llm_callback=None)
        result = r.reflect(
            output={"x": 1},
            unmet=[{"criterion_id": "SC1", "feedback": "below threshold"}]
        )
        # Fallback 동작 — v1.2.0 simple unmet 전달
        self.assertIn("unmet_criteria_count", result)
        self.assertEqual(result["unmet_criteria_count"], 1)

    def test_with_llm_callback(self):
        def fake_llm(prompt):
            return """
            <reflection>
            <what_worked>OK 1</what_worked>
            <what_failed>FAIL 1</what_failed>
            <root_cause>CAUSE 1</root_cause>
            <next_strategy>STRAT 1</next_strategy>
            </reflection>
            """
        r = rfs.ReflexionEnhancedSelfReflect(llm_callback=fake_llm)
        result = r.reflect(
            output={"x": 1},
            unmet=[{"criterion_id": "SC1"}],
            success_criteria=[{"criterion_id": "SC1", "description": "test"}],
            all_verifications=[{"criterion_id": "SC1", "passed": False, "score": 0.5}]
        )
        self.assertIn("verbal_reflection", result)
        self.assertEqual(result["verbal_reflection"]["what_worked"], "OK 1")
        self.assertEqual(len(r.trace.entries), 1)


# ============================================================
# C. Senior Engineer Test Metric
# ============================================================

class TestLOCDelta(unittest.TestCase):

    def test_reduction(self):
        before = "a = 1\nb = 2\nc = 3\nd = 4\n"
        after = "a, b = 1, 2\n"
        d = sem.loc_delta(before, after)
        self.assertLess(d["delta"], 0)
        self.assertEqual(d["before_loc"], 4)
        self.assertEqual(d["after_loc"], 1)


class TestCyclomaticComplexity(unittest.TestCase):

    def test_simple_function(self):
        code = "def f():\n    return 1\n"
        result = sem.cyclomatic_complexity(code)
        self.assertEqual(result["functions"][0]["complexity"], 1)
        self.assertEqual(result["functions"][0]["rating"], "A (simple)")

    def test_complex_function(self):
        code = """
def f(a, b, c, d):
    if a > 0:
        if b > 0:
            for i in range(c):
                if i > d:
                    return i
    elif a < 0:
        while b > 0:
            b -= 1
    return 0
"""
        result = sem.cyclomatic_complexity(code)
        self.assertGreater(result["max_complexity"], 5)


class TestUnusedDetection(unittest.TestCase):

    def test_unused_import(self):
        code = "import os\nimport sys\nprint(sys.argv)\n"
        unused = sem.detect_unused_imports(code)
        self.assertIn("os", unused)
        self.assertNotIn("sys", unused)

    def test_unused_function(self):
        code = "def used():\n    return 1\n\ndef unused():\n    return 2\n\nused()\n"
        unused = sem.detect_unused_functions(code)
        names = [u["name"] for u in unused]
        self.assertIn("unused", names)
        self.assertNotIn("used", names)


class TestDeadCode(unittest.TestCase):

    def test_after_return(self):
        code = "def f():\n    return 1\n    print('never')\n"
        dead = sem.detect_dead_code(code)
        self.assertGreater(len(dead), 0)
        self.assertEqual(dead[0]["type"], "after_return")


class TestSeniorEngineerTestScore(unittest.TestCase):

    def test_clean_code_high_score(self):
        clean = """
def add(a, b):
    return a + b

add(1, 2)
"""
        result = sem.senior_engineer_test_score(clean)
        self.assertGreaterEqual(result["score"], 4)

    def test_messy_code_low_score(self):
        messy = """
import os
import sys
import re
import json
import collections
import unused_module

def complex_unused_func(a, b, c, d, e):
    if a > 0 and b > 0 and c > 0:
        if d > 0 or e > 0:
            for i in range(10):
                if i % 2 == 0:
                    if i > 5:
                        return i
    return 0
    print("dead")

# TODO: refactor
# FIXME: bug
"""
        result = sem.senior_engineer_test_score(messy)
        self.assertLess(result["score"], 5)
        self.assertGreater(len(result["concrete_findings"]), 0)

    def test_with_original_for_delta(self):
        before = "def f():\n    if x:\n        if y:\n            return 1\n    return 0\n"
        after = "def f():\n    return 1 if x and y else 0\n"
        result = sem.senior_engineer_test_score(after, original_code=before)
        self.assertIsNotNone(result["metrics"]["loc_delta"])
        self.assertLess(result["metrics"]["loc_delta"]["delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
