#!/usr/bin/env python3
"""
C implementations unit tests.

Run:
    python -m pytest scripts/test_c_implementations.py -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import c_implementations as ci


# ============================================================
# C1: Causal Graph
# ============================================================

class TestCausalGraph(unittest.TestCase):

    def test_simple_dag(self):
        dag = ci.CausalDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        self.assertTrue(dag.is_acyclic())
        self.assertEqual(dag.parents("C"), {"B"})
        self.assertEqual(dag.descendants("A"), {"B", "C"})
        self.assertEqual(dag.ancestors("C"), {"A", "B"})

    def test_cycle_detection(self):
        dag = ci.CausalDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "A")
        self.assertFalse(dag.is_acyclic())

    def test_d_separation_chain(self):
        """A -> B -> C, conditioning on B implies A independent of C given B"""
        dag = ci.CausalDAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        self.assertTrue(dag.d_separation("A", "C", {"B"}))
        self.assertFalse(dag.d_separation("A", "C", set()))

    def test_d_separation_collider(self):
        """A -> C <- B, A independent of B unconditional"""
        dag = ci.CausalDAG()
        dag.add_edge("A", "C")
        dag.add_edge("B", "C")
        self.assertTrue(dag.d_separation("A", "B", set()))
        # Conditioning on collider opens path
        self.assertFalse(dag.d_separation("A", "B", {"C"}))

    def test_backdoor_set(self):
        dag = ci.CausalDAG()
        dag.add_edge("Z", "X")
        dag.add_edge("X", "Y")
        dag.add_edge("Z", "Y")
        bd = dag.backdoor_set("X", "Y")
        self.assertIn("Z", bd)

    def test_risk_register_analysis(self):
        dag = ci.CausalDAG()
        dag.add_edge("R1", "R2")
        dag.add_edge("R2", "TARGET_QUALITY")
        risks = [{"id": "R1"}, {"id": "R2"}, {"id": "R99"}]
        analysis = ci.analyze_risk_with_causal_graph(risks, dag)
        self.assertEqual(len(analysis), 3)
        # R99 not in graph
        self.assertEqual(analysis[2]["status"], "not_in_graph")


# ============================================================
# C2: Multi-modal Watchdog
# ============================================================

class TestMultimodalWatchdog(unittest.TestCase):

    def test_image_url_format_invalid(self):
        result = ci.verify_image_url("not-a-url")
        self.assertEqual(result["verdict"], "FALSE")
        self.assertEqual(result["checks"]["format"], "invalid_url_format")

    def test_image_url_valid_format(self):
        result = ci.verify_image_url("https://upload.wikimedia.org/test.png")
        self.assertEqual(result["checks"]["format"], "valid")
        self.assertTrue(result["checks"]["has_image_extension"])
        self.assertTrue(result["checks"]["trusted_domain"])

    def test_python_code_valid(self):
        result = ci.verify_code_block("def add(a, b):\n    return a + b")
        self.assertEqual(result["verdict"], "TRUE")
        self.assertEqual(result["checks"]["syntax"], "valid")
        self.assertEqual(result["checks"]["dangerous_patterns"], [])

    def test_python_code_syntax_error(self):
        result = ci.verify_code_block("def broken(:\n  pass")
        self.assertEqual(result["verdict"], "FALSE")

    def test_python_code_dangerous_eval(self):
        result = ci.verify_code_block("x = eval('1+1')")
        self.assertEqual(result["verdict"], "REQUIRES_REVIEW")
        self.assertIn("dangerous_call:eval", result["checks"]["dangerous_patterns"])

    def test_javascript_balanced(self):
        result = ci.verify_code_block("function f() { return [1, 2]; }", language="javascript")
        self.assertEqual(result["verdict"], "TRUE")

    def test_mixed_modality(self):
        claim = {
            "components": [
                {"modality": "code", "code": "def ok(): pass", "language": "python"},
                {"modality": "image", "url": "https://upload.wikimedia.org/x.png"}
            ]
        }
        result = ci.multimodal_watchdog_verdict(claim, "mixed")
        self.assertIn("overall_verdict", result)
        self.assertEqual(len(result["components"]), 2)


# ============================================================
# C3: SLA/SLO
# ============================================================

class TestSLA(unittest.TestCase):

    def test_compliance_pass(self):
        telemetry = {
            "phase_metrics": {"prompt_architect": {"duration_ms": 20000}},
            "cumulative": {"total_duration_ms": 600000}
        }
        result = ci.evaluate_sla_compliance({}, telemetry)
        self.assertGreaterEqual(result["compliance_ratio"], 0.9)

    def test_compliance_breach(self):
        # SLA is 30000 but 60000 used
        telemetry = {
            "phase_metrics": {"prompt_architect": {"duration_ms": 60000}},
            "cumulative": {"total_duration_ms": 100000}
        }
        result = ci.evaluate_sla_compliance({}, telemetry)
        self.assertGreater(len(result["violations"]), 0)

    def test_breach_gate_critical(self):
        violations = [{
            "sla_key": "phase_3a_researcher_ms",
            "target_ms": 180000, "actual_ms": 400000,
            "breach_ratio": 2.2, "severity": "critical"
        }]
        gate = ci.trigger_sla_breach_gate(violations)
        self.assertEqual(gate["gate_id"], "sla_breach")


# ============================================================
# C4: MCP Registry
# ============================================================

class TestMCPRegistry(unittest.TestCase):

    def test_no_endpoint_fallback(self):
        client = ci.MCPRegistryClient(endpoint=None)
        result = client.search(["slack"])
        self.assertTrue(result.get("fallback_to_search_plugins"))

    def test_priority_with_fallback_func(self):
        def fake_search(keywords):
            return [{"plugin": "fake-plugin"}]
        client = ci.MCPRegistryClient(endpoint=None)
        result = ci.search_plugins_priority(["test"], client, fake_search)
        self.assertEqual(result["source"], "search_plugins_fallback")
        self.assertEqual(len(result["results"]), 1)

    def test_no_search_available(self):
        result = ci.search_plugins_priority(["test"], None, None)
        self.assertEqual(result["source"], "no_search_available")


# ============================================================
# C5: Calibration
# ============================================================

class TestCalibration(unittest.TestCase):

    def test_swe_bench_interpolation(self):
        result = ci.calibrate_to_benchmark(3.5, "swe_bench_verified")
        self.assertEqual(result["estimated"], 50.0)
        self.assertEqual(result["method"], "linear_interp")

    def test_osworld(self):
        result = ci.calibrate_to_benchmark(4.0, "osworld_verified")
        self.assertEqual(result["estimated"], 42.0)

    def test_extrapolation_high(self):
        result = ci.calibrate_to_benchmark(6.0, "swe_bench_verified")
        self.assertEqual(result["method"], "extrapolation_high")

    def test_unknown_benchmark(self):
        result = ci.calibrate_to_benchmark(3.0, "imaginary_bench")
        self.assertIn("error", result)

    def test_observation_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ci.update_calibration_from_actual(3.5, 48.0, "swe_bench_verified", tmp)
            self.assertEqual(result["observations_count"], 1)
            self.assertFalse(result["ready_for_recalibration"])
            # Ready after 5 accumulations
            for _ in range(4):
                ci.update_calibration_from_actual(3.5, 50.0, "swe_bench_verified", tmp)
            result = ci.update_calibration_from_actual(3.5, 50.0, "swe_bench_verified", tmp)
            self.assertTrue(result["ready_for_recalibration"])


# ============================================================
# C6: Long-horizon Memory
# ============================================================

class TestLongHorizonMemory(unittest.TestCase):

    def test_acon_dedup(self):
        mems = [
            {"id": "1", "content": "same", "metadata": {"last_used": ci.now_iso()}},
            {"id": "2", "content": "same", "metadata": {"last_used": ci.now_iso()}},
            {"id": "3", "content": "different", "metadata": {"last_used": ci.now_iso()}}
        ]
        compressed = ci.compress_memory_acon_style(mems)
        self.assertEqual(len(compressed), 2)

    def test_acon_target_size(self):
        mems = [{"id": str(i), "content": f"mem{i}",
                 "metadata": {"last_used": ci.now_iso()}} for i in range(10)]
        compressed = ci.compress_memory_acon_style(mems, target_size=3)
        self.assertEqual(len(compressed), 3)

    def test_hierarchy_promotion(self):
        # warm_size=2 so the oldest item (m0) overflows warm into cold:
        # after 5 adds -> hot=[m3,m4], warm=[m1,m2], cold=[m0]
        mem = ci.HierarchicalMemory(hot_size=2, warm_size=2)
        for i in range(5):
            mem.add(f"m{i}", f"content{i}")
        # m0 should be in cold (oldest), m3/m4 in hot
        stats = mem.stats()
        self.assertEqual(stats["hot_count"], 2)
        # Get cold item -> promote to hot
        result = mem.get("m0")
        self.assertIsNotNone(result)
        self.assertEqual(result["promoted_from"], "cold")

    def test_search_relevance(self):
        mem = ci.HierarchicalMemory()
        mem.add("a", "Apple is a fruit")
        mem.add("b", "Banana is yellow")
        mem.add("c", "Cherry is red and small")
        results = mem.search(["fruit"], top_k=3)
        self.assertGreater(len(results), 0)
        # 'fruit' keyword matches 'a' at the top
        self.assertEqual(results[0]["memory"]["id"], "a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
