#!/usr/bin/env python3
"""Tests for the GEPA-style reflective optimizer engine."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gepa_optimizer as gepa


class TestPareto(unittest.TestCase):
    def test_dominates(self):
        self.assertTrue(gepa.dominates({"quality": 5, "cost": 1}, {"quality": 3, "cost": 2}))
        self.assertFalse(gepa.dominates({"quality": 5, "cost": 9}, {"quality": 1, "cost": 1}))
        self.assertFalse(gepa.dominates({"quality": 3, "cost": 2}, {"quality": 3, "cost": 2}))

    def test_front_keeps_tradeoffs(self):
        cands = [
            {"scores": {"quality": 5, "cost": 9}},
            {"scores": {"quality": 1, "cost": 1}},
            {"scores": {"quality": 3, "cost": 9}},  # dominated
        ]
        front = gepa.pareto_front(cands)
        self.assertEqual(len(front), 2)


class TestOptimize(unittest.TestCase):
    def test_climbs_and_dominates_seed(self):
        # quality up, cost flat -> a better candidate dominates the seed.
        def evaluate(p):
            return {"quality": float(p.count("WIN")), "cost": float(len(p))}

        def reflect_mutate(p, _):
            return p.replace("BAD", "WIN", 1)

        r = gepa.optimize("BAD BAD BAD", evaluate, reflect_mutate, iterations=4)
        self.assertGreaterEqual(r["best"]["scores"]["quality"], 1.0)
        self.assertTrue(r["best_dominates_seed"])

    def test_no_improvement_does_not_falsely_dominate(self):
        # Mutation that never helps quality and only adds cost -> seed not dominated.
        def evaluate(p):
            return {"quality": 1.0, "cost": float(len(p))}

        def reflect_mutate(p, _):
            return p + "x"

        r = gepa.optimize("seed", evaluate, reflect_mutate, iterations=3)
        self.assertFalse(r["best_dominates_seed"])

    def test_default_mutate_is_noop_safe(self):
        r = gepa.optimize("seed", lambda p: {"quality": 1.0, "cost": 1.0}, iterations=2)
        self.assertIn("best", r)


if __name__ == "__main__":
    unittest.main()
