#!/usr/bin/env python3
"""
MAS State Manager unit tests
============================

Regression prevention + new feature verification.

Run:
    python -m pytest scripts/test_state_manager.py -v
    or
    python scripts/test_state_manager.py
"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

# This test is located in the same directory as the integrated state_manager.py
sys.path.insert(0, str(Path(__file__).parent))
import state_manager as sm


class TestConcurrencySafety(unittest.TestCase):
    """B1.1: file lock + atomic write verification."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_atomic_write_basic(self):
        sm.write_state("test.json", {"version": 1, "data": "hello"})
        loaded = sm.read_state("test.json")
        self.assertEqual(loaded["data"], "hello")

    def test_version_cas_increment(self):
        sm.write_state("test.json", {"version": 1, "x": "a"})
        sm.write_state("test.json", {"version": 1, "x": "b"})  # same version
        loaded = sm.read_state("test.json")
        self.assertEqual(loaded["version"], 2)  # auto increment

    def test_concurrent_writes(self):
        """N threads concurrent write -> no exceptions, final version = N."""
        N = 5
        errors = []

        def writer(i):
            try:
                sm.write_state("test.json", {"version": 1, "writer": i})
            except Exception as e:  # noqa: BLE001 - collect for assertion
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(N)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(errors, [], f"writer threads raised: {errors}")
        loaded = sm.read_state("test.json")
        self.assertEqual(loaded["version"], N)  # serialized CAS: one bump per writer


class TestBayesianConvergence(unittest.TestCase):
    """B1.2: Bayesian threshold."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_cold_start_uses_hardcoded(self):
        threshold, source = sm.get_adaptive_threshold("complex")
        self.assertEqual(threshold, 0.05)
        self.assertEqual(source, "hardcoded_fallback")

    def test_after_min_samples_uses_bayesian(self):
        # Accumulate 10 session learning data points
        for _ in range(10):
            sm.update_convergence_bayes("complex", True)
        threshold, source = sm.get_adaptive_threshold("complex")
        self.assertEqual(source, "bayesian")
        self.assertGreater(threshold, 0)
        self.assertLess(threshold, 1)


class TestSourceReliability(unittest.TestCase):
    """B2: Beta-Binomial dynamic source reliability (promoted from legacy)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_cold_start_returns_none(self):
        sm.update_source_reliability("example.com", "TRUE")
        # Below min samples -> no prior emitted yet.
        self.assertIsNone(sm.get_source_confidence_prior("example.com"))

    def test_unverifiable_not_counted(self):
        for _ in range(5):
            sm.update_source_reliability("u.com", "UNVERIFIABLE")
        src = sm.update_source_reliability("u.com", "TRUE")
        self.assertEqual(src["pass_count"], 1)
        self.assertEqual(src["fail_count"], 0)

    def test_posterior_after_min_samples(self):
        for _ in range(8):
            sm.update_source_reliability("good.com", "TRUE")
        for _ in range(2):
            sm.update_source_reliability("good.com", "FALSE")
        prior = sm.get_source_confidence_prior("good.com")
        # Beta(8+1, 2+1) posterior mean = 9/12 = 0.75
        self.assertAlmostEqual(prior, 0.75, places=6)

    def test_unknown_source_returns_none(self):
        self.assertIsNone(sm.get_source_confidence_prior("never-seen.com"))


class TestTelemetrySpans(unittest.TestCase):
    """OTel-GenAI-shaped telemetry writer."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_record_and_summary(self):
        root = sm.record_span("pm", "invoke_agent", "claude-opus", 1000, 500)
        sm.record_span("researcher", "invoke_agent", "claude-sonnet", 2000, 800, parent_span_id=root)
        summ = sm.telemetry_summary()
        self.assertEqual(summ["total_spans"], 2)
        self.assertEqual(summ["total_input_tokens"], 3000)
        self.assertEqual(summ["total_output_tokens"], 1300)
        self.assertIn("pm", summ["per_agent"])
        self.assertIn("researcher", summ["per_agent"])

    def test_cost_derivation(self):
        sm.record_span("worker", "invoke_agent", "claude-opus", 1_000_000, 1_000_000)
        summ = sm.telemetry_summary()
        # opus = (5 + 25) per MTok = 30.0
        self.assertAlmostEqual(summ["total_cost_usd"], 30.0, places=4)

    def test_unknown_model_cost_none(self):
        sm.record_span("x", "chat", "mystery-model", 100, 100)
        self.assertEqual(sm.telemetry_summary()["total_cost_usd"], 0.0)


class TestHandoffContract(unittest.TestCase):
    """Typed handoff contract validation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_complete_contract(self):
        c = {"objective": "x", "output_format": "json", "boundaries": "y", "allowed_tools": ["a"]}
        self.assertEqual(sm.validate_handoff_contract(c), [])
        r = sm.record_worker_handoff("w1", "w2", "ctx", 0, contract=c)
        self.assertTrue(r["accepted"])
        self.assertEqual(r["contract_incomplete"], [])

    def test_missing_fields_warn_not_block(self):
        r = sm.record_worker_handoff("w1", "w2", "ctx", 0, contract={"objective": "x"})
        self.assertTrue(r["accepted"])  # not blocked
        self.assertIn("output_format", r["contract_incomplete"])

    def test_no_contract_is_all_missing(self):
        r = sm.record_worker_handoff("w1", "w2", "ctx", 0)
        self.assertTrue(r["accepted"])
        self.assertEqual(set(r["contract_incomplete"]), set(sm.HANDOFF_CONTRACT_FIELDS))


class TestTypedMemory(unittest.TestCase):
    """Typed memory entries with timestamp + supersession."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_add_and_list_by_type(self):
        sm.add_memory_entry("fact A", "semantic")
        sm.add_memory_entry("did X", "episodic")
        self.assertEqual(len(sm.get_memory_entries("semantic")), 1)
        self.assertEqual(len(sm.get_memory_entries()), 2)

    def test_supersession_by_key(self):
        sm.add_memory_entry("v1", "procedural", key="route")
        sm.add_memory_entry("v2", "procedural", key="route")
        live = sm.get_memory_entries("procedural")
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0]["content"], "v2")
        self.assertEqual(len(sm.get_memory_entries("procedural", include_superseded=True)), 2)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            sm.add_memory_entry("x", "bogus")


class TestWatchdogPoolAggregation(unittest.TestCase):
    """B1.3: Pool aggregation."""

    def test_unanimous(self):
        result = sm.aggregate_watchdog_verdicts([
            {"instance_id": "W1", "verdict": "TRUE"},
            {"instance_id": "W2", "verdict": "TRUE"},
            {"instance_id": "W3", "verdict": "TRUE"}
        ])
        self.assertEqual(result["consensus"], "TRUE")
        self.assertEqual(result["method"], "unanimous")
        self.assertTrue(result["early_exit"])

    def test_majority(self):
        result = sm.aggregate_watchdog_verdicts([
            {"instance_id": "W1", "verdict": "TRUE"},
            {"instance_id": "W2", "verdict": "TRUE"},
            {"instance_id": "W3", "verdict": "FALSE"}
        ])
        self.assertEqual(result["consensus"], "TRUE")
        self.assertEqual(result["method"], "majority")
        self.assertEqual(len(result["dissent"]), 1)

    def test_dispute(self):
        result = sm.aggregate_watchdog_verdicts([
            {"instance_id": "W1", "verdict": "TRUE"},
            {"instance_id": "W2", "verdict": "FALSE"},
            {"instance_id": "W3", "verdict": "UNVERIFIABLE"}
        ])
        self.assertEqual(result["consensus"], "DISPUTED")


class TestWorkerConflictDetection(unittest.TestCase):
    """B1.4: conflict detection."""

    def test_no_conflict_empty(self):
        conflicts = sm.detect_worker_conflicts([])
        self.assertEqual(len(conflicts), 0)

    def test_conflict_different_summaries(self):
        wo_a = {"worker_id": "W1", "tasks_completed": [
            {"task_id": "T1", "output_summary": "Conclusion A"}
        ]}
        wo_b = {"worker_id": "W2", "tasks_completed": [
            {"task_id": "T1", "output_summary": "Conclusion B"}
        ]}
        conflicts = sm.detect_worker_conflicts([wo_a, wo_b])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["entity"], "task_T1")


class TestAsyncTasks(unittest.TestCase):
    """MCP async Tasks primitive."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)
        sm.write_state("async_tasks.json", {"version": 1, "tasks": {}})

    def test_create_task(self):
        tid = sm.create_async_task("researcher", {"query": "test"})
        self.assertIsNotNone(tid)
        task = sm.get_async_task(tid)
        self.assertEqual(task["state"], "pending")

    def test_state_transition(self):
        tid = sm.create_async_task("researcher", {})
        sm.update_async_task(tid, "working")
        sm.update_async_task(tid, "completed", result={"answer": "42"})
        task = sm.get_async_task(tid)
        self.assertEqual(task["state"], "completed")
        self.assertEqual(task["result"]["answer"], "42")

    def test_invalid_state_raises(self):
        tid = sm.create_async_task("researcher", {})
        with self.assertRaises(ValueError):
            sm.update_async_task(tid, "invalid_state")


class TestCheckpoint(unittest.TestCase):
    """LangGraph-style checkpoint."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_create_and_list(self):
        sm.write_state("test.json", {"version": 1, "x": "a"})
        cp_id = sm.create_checkpoint()
        self.assertIsNotNone(cp_id)
        cps = sm.list_checkpoints()
        self.assertIn(cp_id, cps)

    def test_restore(self):
        sm.write_state("test.json", {"version": 1, "x": "before"})
        cp_id = sm.create_checkpoint("before_restore")
        sm.write_state("test.json", {"version": 2, "x": "after"})
        sm.restore_checkpoint(cp_id)
        loaded = sm.read_state("test.json")
        self.assertEqual(loaded["x"], "before")

    def test_retention(self):
        for i in range(10):  # 10 checkpoints
            sm.create_checkpoint(f"cp_{i}")
        cps = sm.list_checkpoints()
        # CHECKPOINT_RETENTION = 5 -> retain 5
        self.assertLessEqual(len(cps), sm.CHECKPOINT_RETENTION + 1)  # +1 for "summary" if exists


class TestWorkerHandoff(unittest.TestCase):
    """OpenAI SDK-style handoff."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.write_state("worker_handoffs.json", {"version": 1, "handoffs": []})

    def test_handoff_within_hop_limit(self):
        result = sm.record_worker_handoff("W1", "W2", {"context": "..."}, hop_count=0)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["hop_count"], 1)

    def test_handoff_exceeds_hop_limit(self):
        result = sm.record_worker_handoff("W1", "W2", {}, hop_count=sm.MAX_HANDOFF_HOPS)
        self.assertFalse(result["accepted"])
        self.assertIn("hop_limit_exceeded", result["reason"])


class TestStructuredOutputValidation(unittest.TestCase):
    """Schema validation."""

    def test_valid_output(self):
        schema = {"type": "object", "required": ["title", "score"]}
        output = {"title": "test", "score": 5}
        result = sm.validate_worker_output_schema(output, schema)
        self.assertTrue(result["valid"])

    def test_missing_required(self):
        schema = {"type": "object", "required": ["title", "score"]}
        output = {"title": "test"}  # score missing
        result = sm.validate_worker_output_schema(output, schema)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)


class TestMemoryAPIAdapter(unittest.TestCase):
    """Anthropic Memory API adapter."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_export_empty_state(self):
        data = sm.memory_export()
        self.assertEqual(data["format"], "anthropic_memory_api_v1")
        self.assertEqual(len(data["memories"]), 0)

    def test_export_with_pattern(self):
        sm.write_state("process_policy.json", {
            "version": 1,
            "patterns": {"data_analysis": {"steps": ["sample", "validate", "analyze"]}}
        })
        data = sm.memory_export()
        self.assertEqual(len(data["memories"]), 1)
        self.assertEqual(data["memories"][0]["type"], "procedural")

    def test_round_trip_export_import(self):
        sm.write_state("process_policy.json", {
            "version": 1,
            "patterns": {"task_a": {"steps": ["x"]}}
        })
        exported = sm.memory_export()
        # Intentionally reset process_policy
        sm.write_state("process_policy.json", {"version": 1, "patterns": {}})
        count = sm.memory_import(exported)
        self.assertEqual(count, 1)
        loaded = sm.read_state("process_policy.json")
        self.assertIn("task_a", loaded["patterns"])


class TestRegression_v0_4_0(unittest.TestCase):
    """Regression prevention for existing features."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        sm.set_state_dir(self.tmpdir)
        sm.set_persistent_dir(self.tmpdir)

    def test_init_session(self):
        sm.init_session("test task")
        session = sm.read_state("session_state.json")
        self.assertEqual(session["status"], "initialized")
        self.assertEqual(session["current_phase"], 0)

    def test_should_continue_loop_no_history(self):
        sm.init_session("test")
        result = sm.should_continue_loop()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
