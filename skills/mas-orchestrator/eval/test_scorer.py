#!/usr/bin/env python3
"""Tests for the MAS eval scorer."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scorer


class TestScoreCase(unittest.TestCase):
    def test_pass_flip_is_worth_it(self):
        v = scorer.score_case({
            "single": {"passed": False, "overall_score": 2.5, "tokens": 4000},
            "mas": {"passed": True, "overall_score": 4.2, "tokens": 50000},
        })
        self.assertEqual(v["verdict"], "mas_worth_it")
        self.assertTrue(v["pass_flip"])

    def test_pass_flip_too_expensive(self):
        v = scorer.score_case({
            "single": {"passed": False, "overall_score": 2.5, "tokens": 1000},
            "mas": {"passed": True, "overall_score": 4.2, "tokens": 30000},  # 30x
        })
        self.assertEqual(v["verdict"], "single_sufficient")

    def test_trivial_gain_not_worth_it(self):
        v = scorer.score_case({
            "single": {"passed": True, "overall_score": 4.1, "tokens": 3500},
            "mas": {"passed": True, "overall_score": 4.2, "tokens": 49000},
        })
        self.assertEqual(v["verdict"], "single_sufficient")

    def test_regression_flagged(self):
        v = scorer.score_case({
            "single": {"passed": True, "overall_score": 4.0, "tokens": 3000},
            "mas": {"passed": False, "overall_score": 3.0, "tokens": 60000},
        })
        self.assertEqual(v["verdict"], "single_sufficient")
        self.assertIn("regression", v["reason"])

    def test_real_gain_worth_it(self):
        v = scorer.score_case({
            "single": {"passed": True, "overall_score": 3.4, "tokens": 4000},
            "mas": {"passed": True, "overall_score": 4.3, "tokens": 40000},  # +0.9, 10x
        })
        self.assertEqual(v["verdict"], "mas_worth_it")

    def test_incomplete_pair(self):
        v = scorer.score_case({"mas": {"passed": True, "overall_score": 4.0, "tokens": 5}})
        self.assertEqual(v["verdict"], "incomplete")


class TestAggregate(unittest.TestCase):
    def test_aggregate_counts(self):
        records = [
            {"case_id": "a", "mode": "single", "passed": False, "overall_score": 2.0, "tokens": 3000},
            {"case_id": "a", "mode": "mas", "passed": True, "overall_score": 4.0, "tokens": 30000},
            {"case_id": "b", "mode": "single", "passed": True, "overall_score": 4.0, "tokens": 3000},
            {"case_id": "b", "mode": "mas", "passed": True, "overall_score": 4.05, "tokens": 45000},
        ]
        agg = scorer.aggregate(records)
        self.assertEqual(agg["n_complete"], 2)
        self.assertEqual(agg["mas_worth_it"], 1)
        self.assertEqual(agg["single_sufficient"], 1)


if __name__ == "__main__":
    unittest.main()
