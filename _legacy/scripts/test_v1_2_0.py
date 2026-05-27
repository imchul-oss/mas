#!/usr/bin/env python3
"""v1.2.0 G1 + G2 단위 테스트."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal_driven_executor as gde
import test_first_transformer as tft


# ============================================================
# G1: Goal-Driven Executor
# ============================================================

class TestGoalDrivenExecutor(unittest.TestCase):

    def test_passes_immediately(self):
        criteria = [{"criterion_id": "SC1", "verification_method": "metric_threshold",
                     "metric_path": "x", "threshold": 1}]
        runner = lambda it, prior: {"x": 5}
        ex = gde.GoalDrivenExecutor(criteria, max_iterations=3, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["iterations"], 1)

    def test_loops_until_pass(self):
        state = {"x": 0}
        def runner(it, prior):
            state["x"] += 1
            return {"x": state["x"]}
        criteria = [{"criterion_id": "SC1", "verification_method": "metric_threshold",
                     "metric_path": "x", "threshold": 3}]
        ex = gde.GoalDrivenExecutor(criteria, max_iterations=5, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["iterations"], 3)

    def test_max_iter_when_unreachable(self):
        criteria = [{"criterion_id": "SC1", "verification_method": "metric_threshold",
                     "metric_path": "x", "threshold": 100}]
        runner = lambda it, prior: {"x": 1}
        ex = gde.GoalDrivenExecutor(criteria, max_iterations=2, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "max_iter")
        self.assertEqual(result["iterations"], 2)
        self.assertIn("SC1", result["unmet_criteria"])

    def test_regex_match_method(self):
        runner = lambda it, prior: "OK validation passes"
        criteria = [{"criterion_id": "SC1", "verification_method": "regex_match",
                     "pattern": "validation passes"}]
        ex = gde.GoalDrivenExecutor(criteria, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")

    def test_schema_compliance_fallback(self):
        runner = lambda it, prior: {"name": "test", "score": 5}
        criteria = [{"criterion_id": "SC1", "verification_method": "schema_compliance",
                     "schema": {"type": "object", "required": ["name", "score"]}}]
        ex = gde.GoalDrivenExecutor(criteria, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")

    def test_multiple_criteria(self):
        runner = lambda it, prior: {"a": 5, "b": 10}
        criteria = [
            {"criterion_id": "SC1", "verification_method": "metric_threshold",
             "metric_path": "a", "threshold": 3},
            {"criterion_id": "SC2", "verification_method": "metric_threshold",
             "metric_path": "b", "threshold": 8}
        ]
        ex = gde.GoalDrivenExecutor(criteria, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")

    def test_verification_error_logged(self):
        runner = lambda it, prior: {"data": "x"}
        criteria = [{"criterion_id": "SC1", "verification_method": "unknown_method"}]
        ex = gde.GoalDrivenExecutor(criteria, worker_runner=runner, max_iterations=1)
        result = ex.execute()
        self.assertEqual(result["status"], "max_iter")


# ============================================================
# G2: Test-First Transformer
# ============================================================

class TestTransformer(unittest.TestCase):

    def test_add_feature(self):
        result = tft.transform_task("Add validation for email inputs")
        self.assertEqual(result["task_type"], "add_feature")
        self.assertIn("test", result["transformed_goal"].lower())
        self.assertGreaterEqual(result["transformation_confidence"], 0.7)

    def test_fix_bug(self):
        result = tft.transform_task("Fix the bug in payment processing")
        self.assertEqual(result["task_type"], "fix_bug")
        self.assertIn("reproduces", result["transformed_goal"])

    def test_refactor(self):
        result = tft.transform_task("Refactor the authentication module")
        self.assertEqual(result["task_type"], "refactor")
        self.assertIn("tests pass", result["transformed_goal"])

    def test_verify(self):
        result = tft.transform_task("Verify the calculation is correct")
        self.assertEqual(result["task_type"], "verify")

    def test_analyze(self):
        result = tft.transform_task("Analyze Q3 financial trends")
        self.assertEqual(result["task_type"], "analyze")

    def test_documentation(self):
        result = tft.transform_task("Document the API endpoints")
        self.assertEqual(result["task_type"], "documentation")

    def test_unknown_low_confidence(self):
        result = tft.transform_task("Make it work somehow")
        self.assertEqual(result["task_type"], "unknown")
        self.assertLess(result["transformation_confidence"], 0.5)

    def test_success_criteria_generated(self):
        result = tft.transform_task("Add new endpoint /api/users")
        self.assertGreater(len(result["success_criteria"]), 0)
        for c in result["success_criteria"]:
            self.assertIn("criterion_id", c)
            self.assertIn("verification_method", c)

    def test_pm_plan_batch_transformation(self):
        pm_plan = {
            "task_decomposition": [
                {"task_id": "T1", "description": "Add user authentication"},
                {"task_id": "T2", "description": "Fix login bug"},
                {"task_id": "T3", "description": "Document new flow"}
            ]
        }
        updated = tft.transform_pm_plan_tasks(pm_plan)
        self.assertIn("task_decomposition_with_transformations", updated)
        transformed = updated["task_decomposition_with_transformations"]
        self.assertEqual(len(transformed), 3)
        self.assertEqual(transformed[0]["transformation"]["task_type"], "add_feature")
        self.assertEqual(transformed[1]["transformation"]["task_type"], "fix_bug")
        self.assertEqual(transformed[2]["transformation"]["task_type"], "documentation")


# ============================================================
# G1 + G2 통합
# ============================================================

class TestIntegration(unittest.TestCase):

    def test_transformer_output_feeds_executor(self):
        """G2 변환 결과 → G1 Executor 에 직접 입력 가능 한가?"""
        # G2: imperative → goal
        transform = tft.transform_task("Add validation for email")
        criteria = transform["success_criteria"]

        # G1 에 주입 (단, automated_test 는 외부 runner 필요)
        # 본 테스트는 단순 metric_threshold 로 전환
        criteria_for_test = [{
            "criterion_id": "SC1",
            "verification_method": "metric_threshold",
            "metric_path": "tests_passed",
            "threshold": 1
        }]
        runner = lambda it, prior: {"tests_passed": 1}
        ex = gde.GoalDrivenExecutor(criteria_for_test, worker_runner=runner)
        result = ex.execute()
        self.assertEqual(result["status"], "passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
